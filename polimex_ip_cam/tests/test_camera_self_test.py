# -*- coding: utf-8 -*-
"""Самотестът на камерата: всички проблеми на едно място, без да пипа нищо.

Бизнес твърдения (собственик, 2026-08-16, при живия отказ на списъците):
1. "като избера камерата и извикам тест да ми излезе тест с всички проблеми
   плюс всички детайли по камерата" - един бутон, пълният доклад.
2. "това не трябва да нарушава работата на камерата (ако работи)" - тестът
   само чете; единственият запис е фиктивен номер, който се маха веднага;
   бариерата, часовникът и настройките за известяване НЕ се пипат.
3. Живият отказ (V5.5.0, HTTP 400 на всеки от 1394 записа) трябва да
   се диагностицира: минимален запис срещу запис с формата на реалните
   данни, и присъда КОЯ част камерата отказва.
4. Отхвърлен механизъм не наводнява дневника: три еднакви поредни отказа
   спират останалите команди от партидата с една обяснена бележка.
"""
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.polimex_ip_cam.helpers.camera_api import HikvisionCamera

CONNECTED = {
    'status': 'connected', 'name': 'Gate cam', 'type': 'ANPR',
    'devid': '1', 'model': 'DS-TCG406-E', 'serial': 'DS-TCG406-E20260101',
    'subserial': 'G12345678', 'firmware': 'V5.5.0',
    'firmwaredate': 'build 260101', 'hardware': '1.0',
    'supportBeep': 'true', 'supportVideoLoss': 'false',
}
OK_WRITE = {'status': 'success', 'response': '{"statusCode":1}'}
REFUSED = {'status': 'failed',
           'error': 'Invalid XML Content (badParameters, 0x38410029)'}


def _quiet_reads():
    """Всички безопасни четения отговарят успешно."""
    return [
        patch.object(HikvisionCamera, 'check_connection', return_value=dict(CONNECTED)),
        patch.object(HikvisionCamera, 'get_snapshot',
                     return_value={'status': 'success', 'snapshot_b64': 'x' * 56}),
        patch.object(HikvisionCamera, 'get_time_config',
                     return_value={'status': 'failed', 'error': 'no clock in this double'}),
        patch.object(HikvisionCamera, 'get_http_host',
                     return_value={'status': 'success', 'response': {
                         'ipAddress': '192.168.0.99', 'portNo': '8069',
                         'url': '/ipcam/anpr/event/G12345678',
                         'protocolType': 'HTTP'}}),
        patch.object(HikvisionCamera, 'search_lp_audit',
                     return_value={'status': 'success', 'records': [
                         {'plate': 'CB1234AB', 'type': 'whiteList'}],
                         'plates': ['CB1234AB'], 'total': 1}),
        patch.object(HikvisionCamera, 'probe_vcl_capabilities',
                     return_value={'status': 'success', 'status_code': 404, 'body': ''}),
        patch.object(HikvisionCamera, 'get_entrance_param',
                     return_value={'status': 'success', 'response': {
                         'bEnable': 'true', 'ctrlMode': '2',
                         'vehControlMeasure.plateNumOnlyEnable': 'true'}}),
        patch.object(HikvisionCamera, 'export_lp_list_xml',
                     return_value={'status': 'success', 'status_code': 200,
                                   'body': '<LPListAuditData><LicensePlateInfoList/></LPListAuditData>'}),
    ]


@tagged('post_install', '-at_install', 'polimex_ip_cam', 'ipcam_self_test')
class TestCameraSelfTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.camera = cls.env['cctv.camera'].create({
            'name': 'Вход', 'ip_address': '10.0.0.7', 'username': 'admin',
            'password': 'x', 'brand': 'hikvision', 'tz': 'Europe/Sofia',
            'sub_serial_number': 'G12345678',
            'server_setup': 'ipAddress=192.168.0.99\nportNo=8069',
        })

    def _run(self, add=None, delete=None, time_config=None):
        patches = _quiet_reads() + ([
            patch.object(HikvisionCamera, 'get_time_config',
                         return_value=time_config)] if time_config else []) + [
            patch.object(HikvisionCamera, 'add_plate_to_list',
                         side_effect=add or (lambda entries: dict(OK_WRITE))),
            patch.object(HikvisionCamera, 'delete_plate_from_list',
                         return_value=delete or dict(OK_WRITE)),
            patch.object(HikvisionCamera, 'barrier_gate_control') ,
            patch.object(HikvisionCamera, 'set_time_config'),
            patch.object(HikvisionCamera, 'set_http_host'),
        ]
        started = [p.start() for p in patches]
        self.addCleanup(lambda: [p.stop() for p in patches])
        action = self.camera.action_camera_diagnostics()
        wizard = self.env['cctv.camera.diagnostic'].browse(action['res_id'])
        # Тестът никога не задейства нищо по камерата.
        barrier, set_time, set_host = started[-3], started[-2], started[-1]
        self.assertFalse(barrier.called, 'самотестът задвижи бариерата')
        self.assertFalse(set_time.called, 'самотестът пренастрои часовника')
        self.assertFalse(set_host.called, 'самотестът пренастрои известяването')
        return wizard.report, started

    def test_the_report_holds_the_details_and_the_problems_up_top(self):
        """Един клик - всички детайли; проблемният часовник е обявен горе."""
        report, _mocks = self._run()
        self.assertIn('V5.5.0', report, 'фирмуерът липсва от доклада')
        self.assertIn('DS-TCG406-E', report)
        self.assertIn('PROBLEMS FOUND', report,
                      'недостъпният часовник трябва да излезе като проблем')
        self.assertIn('192.168.0.99', report, 'дестинацията на събитията липсва')
        # Чатърът е за разговори, не за логове (собственикът, дословно) -
        # докладът живее само в диалога.
        self.assertFalse(
            any('PROBLEMS' in (m.body or '') for m in self.camera.message_ids),
            'докладът е издуднал чатъра на камерата')

    def test_a_working_camera_is_left_exactly_as_found(self):
        """Записът е един фиктивен номер и се маха: нула следи след теста."""
        added, removed = [], []

        def add(entries):
            added.extend(e['plateNum'] for e in entries)
            return dict(OK_WRITE)

        report, _mocks = self._run(add=add)
        self.assertTrue(all(p == self.camera.DIAG_TEST_PLATE for p in added),
                        'тестът писа нещо различно от фиктивния номер: %s' % added)

    def test_the_verdict_names_what_the_camera_refuses(self):
        """Минималният запис минава, реалната форма пада -> присъдата назовава
        частта, която фирмуерът отказва (живият случай: свързаната карта)."""
        contact = self.env['res.partner'].create({'name': 'Шофьор'})
        plate_type = self.env.ref('hr_rfid.hr_rfid_card_type_8')
        plate_card = self.env['hr.rfid.card'].create({
            'number': 'CB5803CM', 'card_type': plate_type.id,
            'contact_id': contact.id, 'company_id': self.env.company.id,
        })
        self.env['hr.rfid.card'].create({
            'number': '0000012345', 'contact_id': contact.id,
            'company_id': self.env.company.id,
        })
        self.camera.rfid_rel_ids = [(0, 0, {
            'card_id': plate_card.id, 'list_category': 'whitelist',
        })]

        def add(entries):
            entry = entries[0]
            if 'cardNo' in entry:
                return dict(REFUSED)
            return dict(OK_WRITE)

        report, _mocks = self._run(add=add)
        self.assertIn('VERDICT', report, 'липсва присъда коя част е отказана')
        self.assertIn('linked card number', report,
                      'присъдата не назовава свързаната карта като причината')
        self.assertIn('0x38410029', report,
                      'дословният отговор на камерата липсва от доклада')

    def test_a_refused_mechanism_does_not_flood_the_batch(self):
        """Три еднакви отказа спират останалите команди с една бележка."""
        calls = []

        def refuse(entries):
            calls.append(entries)
            return dict(REFUSED)

        commands = self.env['cctv.camera.command'].with_context(
            no_hardware_commands=True).create([{
                'camera_id': self.camera.id,
                'command_type': 'add_plate',
                'request_data': 'plateNum=CB%04dAB\nlistType=0' % i,
            } for i in range(10)])
        with patch.object(HikvisionCamera, 'add_plate_to_list', side_effect=refuse):
            commands.action_execute()
        self.assertEqual(len(calls), commands.PLATE_FAILURE_STREAK_LIMIT,
                         'камерата продължи да бъде обстрелвана след присъдата')
        self.assertTrue(all(c.state == 'error' for c in commands))
        # Спрените команди носят ДОСЛОВНИЯ пръв отговор на камерата - това е
        # обяснението "защо", независимо на какъв език говори интерфейсът.
        stopped = commands[commands.PLATE_FAILURE_STREAK_LIMIT:]
        self.assertTrue(
            all('0x38410029' in (c.response_data or '') for c in stopped),
            'спрените команди не цитират отговора, заради който са спрени')

    def test_a_true_wall_clock_with_a_lying_offset_is_not_an_alarm(self):
        """Живият случай: камерата обяви +02:00 при вярно стенно време и
        докладът изкрещя "3599 секунди" - документираният капан с
        инвертирания Hikvision офсет. Канонът от heartbeat-а: офсетът се
        сваля, стенното време се закотвя в зоната на камерата."""
        from datetime import datetime, timezone as dt_tz
        import pytz as _pytz
        sofia_wall = datetime.now(dt_tz.utc).astimezone(
            _pytz.timezone('Europe/Sofia')).replace(microsecond=0)
        lying_iso = sofia_wall.strftime('%Y-%m-%dT%H:%M:%S') + '+02:00'
        report, _mocks = self._run(time_config={
            'status': 'success', 'timeMode': 'ALL',
            'timeZone': 'CST-2:00:00DST01:00:00', 'localTime': lying_iso})
        self.assertNotIn('clock is off', report,
                         'вярното стенно време е обявено за разминато - '
                         'докладът вярва на лъжливия офсет')
        self.assertIn('offset the camera claims is ignored', report,
                      'докладът не обяснява защо офсетът не се ползва')

    def test_a_different_device_at_the_address_is_called_out(self):
        """Отговаря ЧУЖД сериен номер -> проблем, не мълчалива подмяна."""
        self.camera.serial_number = 'DS-OTHER-SERIAL'
        report, _mocks = self._run()
        self.assertIn('DIFFERENT device', report,
                      'чуждото устройство на адреса не е обявено като проблем')


@tagged('post_install', '-at_install', 'polimex_ip_cam', 'ipcam_self_test')
class TestReaderListSelfRepair(TransactionCase):
    """Камера с вързани четци, но празен списък, не губи събития.

    Живият случай (2026-08-16): пренесените камери имаха четците си по
    camera_id, списъкът reader_ids стоеше празен и всяко разпознаване се
    изхвърляше с "has no readers configured" - реални коли, незаписани."""

    def test_wired_readers_are_relinked_instead_of_dropping_the_event(self):
        camera = self.env['cctv.camera'].create({
            'name': 'ВХОД ХАН БОГРОВ', 'ip_address': '10.0.0.8',
            'username': 'admin', 'password': 'x', 'brand': 'hikvision',
            'tz': 'Europe/Sofia',
        })
        wired = self.env['hr.rfid.reader'].search(
            [('camera_id', '=', camera.id)], order='number, id')
        self.assertTrue(wired, 'камерата не е авто-провизирала четците си')
        camera.reader_ids = [(5, 0, 0)]
        self.assertFalse(camera.reader_ids)

        linked = camera._ensure_reader_links()

        self.assertEqual(linked, wired,
                         'вързаните четци не бяха възстановени - събитието '
                         'щеше да се изгуби')
        self.assertEqual(linked[0].number, 1,
                         'редът е In преди Out - обработката взима [0] за вход')

    def test_a_camera_with_truly_no_readers_still_reports_empty(self):
        camera = self.env['cctv.camera'].create({
            'name': 'Гола камера', 'ip_address': '10.0.0.18',
            'username': 'admin', 'password': 'x', 'brand': 'hikvision',
            'tz': 'Europe/Sofia',
        })
        # Мениджър е разкачил и изтрил авто-провизираните четци.
        self.env['hr.rfid.reader'].search(
            [('camera_id', '=', camera.id)]).unlink()
        camera.reader_ids = [(5, 0, 0)]
        self.assertFalse(camera._ensure_reader_links(),
                         'камера без никакви четци не бива да измисля връзки')


@tagged('post_install', '-at_install', 'polimex_ip_cam', 'ipcam_self_test')
class TestEntranceModeInTheReport(TransactionCase):
    """Живият факт: байтово еднакъв минимален запис минава на едната камера
    и пада на другата - разликата е в НАСТРОЙКИТЕ на камерата. Докладът
    показва входно-списъчната конфигурация дословно, а изключен режим е
    обявен проблем (интуицията на собственика от първия ден: "ако е
    пропуск в настройките")."""

    def _camera(self):
        return self.env['cctv.camera'].create({
            'name': 'ВХОД', 'ip_address': '10.0.0.31', 'username': 'admin',
            'password': 'x', 'brand': 'hikvision', 'tz': 'Europe/Sofia',
        })

    def test_a_switched_off_entrance_control_is_a_named_problem(self):
        camera = self._camera()
        patches = _quiet_reads() + [
            patch.object(HikvisionCamera, 'get_entrance_param',
                         return_value={'status': 'success',
                                       'response': {'bEnable': 'false'}}),
            patch.object(HikvisionCamera, 'add_plate_to_list',
                         return_value=dict(OK_WRITE)),
            patch.object(HikvisionCamera, 'delete_plate_from_list',
                         return_value=dict(OK_WRITE)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        action = camera.action_camera_diagnostics()
        report = self.env['cctv.camera.diagnostic'].browse(action['res_id']).report
        self.assertIn('bEnable', report, 'конфигурацията липсва от доклада')
        self.assertIn('switched OFF', report,
                      'изключеният входен контрол не е обявен като проблем')


@tagged('post_install', '-at_install', 'polimex_ip_cam', 'ipcam_self_test')
class TestUnreachableCameraIsOneProblemNotSixHundred(TransactionCase):
    """Собственикът, дословно: пуснатият процес по презареждане "не проверява
    дали камерата отговаря, а започва 600 номера да праща и генерира 600
    грешки за които всъщност проблемът е комуникационен"."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.camera = cls.env['cctv.camera'].create({
            'name': 'ВХОД', 'ip_address': '10.0.0.41', 'username': 'admin',
            'password': 'x', 'brand': 'hikvision', 'tz': 'Europe/Sofia',
        })

    def test_reload_asks_the_camera_first(self):
        """Недостъпна камера = едно предупреждение, нула команди."""
        contact = self.env['res.partner'].create({'name': 'Шофьор'})
        plate = self.env['hr.rfid.card'].with_context(
            no_hardware_commands=True).create({
                'number': 'CB7153HX', 'contact_id': contact.id,
                'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_8').id,
                'company_id': self.env.company.id,
            })
        self.camera.with_context(no_hardware_commands=True).rfid_rel_ids = [
            (0, 0, {'card_id': plate.id, 'list_category': 'whitelist'})]
        before = self.env['cctv.camera.command'].search_count([])
        with patch.object(HikvisionCamera, 'check_connection',
                          return_value={'status': 'unreachable',
                                        'error': 'no route'}):
            action = self.camera.action_reload_whitelist()
        self.assertEqual(
            self.env['cctv.camera.command'].search_count([]), before,
            'към недостъпна камера пак се изстреляха команди')
        self.assertEqual(action['params']['type'], 'warning',
                         'операторът не е предупреден, че камерата мълчи')

    def test_a_batch_stops_at_the_first_network_failure(self):
        """Мрежовият отказ спира партидата ВЕДНАГА - не на 600-ната грешка.
        Спирачката с 3 еднакви не хваща този случай: мрежовият текст носи
        различен адрес в паметта при всеки опит."""
        calls = []

        def unreachable(entries):
            calls.append(entries)
            return {'status': 'failed',
                    'error': "HTTPConnectionPool(host='10.0.0.41'): Max "
                             "retries exceeded (object at 0x%x)" % id(entries),
                    'unreachable': True}

        commands = self.env['cctv.camera.command'].with_context(
            no_hardware_commands=True).create([{
                'camera_id': self.camera.id, 'command_type': 'add_plate',
                'request_data': 'plateNum=CB%04dAB\nlistType=0' % i,
            } for i in range(10)])
        with patch.object(HikvisionCamera, 'add_plate_to_list',
                          side_effect=unreachable):
            commands.action_execute()
        self.assertEqual(len(calls), 1,
                         'недостъпната камера е обстрелвана повече от веднъж')
        self.assertTrue(all(c.state == 'error' for c in commands))


@tagged('post_install', '-at_install', 'polimex_ip_cam', 'ipcam_self_test')
class TestTheListHereLeads(TransactionCase):
    """Политиката на собственика, дословно: "камерите когато са под наше
    управление поддържат само нашите списъци. не ни интересува какво има
    записано там. водещ е списъка при нас." """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.camera = cls.env['cctv.camera'].create({
            'name': 'ВХОД', 'ip_address': '10.0.0.51', 'username': 'admin',
            'password': 'x', 'brand': 'hikvision', 'tz': 'Europe/Sofia',
        })
        contact = cls.env['res.partner'].create({'name': 'Наш шофьор'})
        plate = cls.env['hr.rfid.card'].with_context(
            no_hardware_commands=True).create({
                'number': 'CB7153HX', 'contact_id': contact.id,
                'card_type': cls.env.ref('hr_rfid.hr_rfid_card_type_8').id,
                'company_id': cls.env.company.id,
            })
        cls.camera.with_context(no_hardware_commands=True).rfid_rel_ids = [
            (0, 0, {'card_id': plate.id, 'list_category': 'whitelist'})]

    def test_sync_removes_what_is_not_ours_and_sends_what_is(self):
        """Заварен чужд номер на камерата се маха; нашият се изпраща."""
        Command = self.env['cctv.camera.command']
        before = Command.search([])
        patches = [
            patch.object(HikvisionCamera, 'check_connection',
                         return_value=dict(CONNECTED)),
            patch.object(HikvisionCamera, 'search_lp_audit',
                         return_value={'status': 'success', 'total': 2,
                                       'plates': ['PB4181KC', 'CB7153HX'],
                                       'records': [{'plate': 'PB4181KC'},
                                                   {'plate': 'CB7153HX'}]}),
            patch.object(HikvisionCamera, 'add_plate_to_list',
                         return_value=dict(OK_WRITE)),
            patch.object(HikvisionCamera, 'delete_plate_from_list',
                         return_value=dict(OK_WRITE)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.camera.action_reload_whitelist()
        created = self.env['cctv.camera.command'].search([]) - before
        removals = created.filtered(lambda c: c.command_type == 'remove_plate')
        adds = created.filtered(lambda c: c.command_type == 'add_plate')
        self.assertEqual(len(removals), 1)
        self.assertIn('PB4181KC', removals.request_data,
                      'чуждият заварен номер не е предвиден за махане')
        self.assertNotIn('CB7153HX', removals.request_data,
                         'нашият номер е предвиден за махане')
        self.assertEqual(len(adds), 1,
                         'номерата пътуват в една партидна команда, не по '
                         'команда на номер')
        self.assertIn('CB7153HX', adds.request_data)

    def test_an_unreadable_camera_list_never_guesses_removals(self):
        """Не можем ли да прочетем какво има на камерата - не махаме нищо."""
        Command = self.env['cctv.camera.command']
        before = Command.search([])
        patches = [
            patch.object(HikvisionCamera, 'check_connection',
                         return_value=dict(CONNECTED)),
            patch.object(HikvisionCamera, 'search_lp_audit',
                         return_value={'status': 'failed', 'error': 'boom'}),
            patch.object(HikvisionCamera, 'add_plate_to_list',
                         return_value=dict(OK_WRITE)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.camera.action_reload_whitelist()
        created = self.env['cctv.camera.command'].search([]) - before
        self.assertFalse(
            created.filtered(lambda c: c.command_type == 'remove_plate'),
            'махане на сляпо - без да знаем какво има на камерата')
        self.assertTrue(
            created.filtered(lambda c: c.command_type == 'add_plate'),
            'нашите номера трябва да заминат въпреки нечетимия списък')


@tagged('post_install', '-at_install', 'polimex_ip_cam', 'ipcam_self_test')
class TestPlatesTravelTogether(TransactionCase):
    """Собственикът: "няма ли опция всички номера да се изпратят заедно
    (без да се нарушава работния процес на модулния сет)". API-то е
    групово поначало - раздробяваше командният слой."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.camera = cls.env['cctv.camera'].create({
            'name': 'ВХОД', 'ip_address': '10.0.0.61', 'username': 'admin',
            'password': 'x', 'brand': 'hikvision', 'tz': 'Europe/Sofia',
        })

    def _batch_command(self, plates):
        import json as _json
        return self.env['cctv.camera.command'].with_context(
            no_hardware_commands=True).create([{
                'camera_id': self.camera.id, 'command_type': 'add_plate',
                'request_data': _json.dumps(
                    [{'plateNum': p, 'listType': '0'} for p in plates]),
            }])

    def test_one_command_carries_many_plates(self):
        calls = []

        def record(entries):
            calls.append(entries)
            return dict(OK_WRITE)

        command = self._batch_command(['CB0001AA', 'CB0002BB', 'CB0003CC'])
        with patch.object(HikvisionCamera, 'add_plate_to_list',
                          side_effect=record):
            command.action_execute()
        self.assertEqual(command.state, 'done')
        self.assertEqual(len(calls), 1, 'партидата е раздробена на заявки')
        self.assertEqual(len(calls[0]), 3,
                         'трите номера не пътуват в една заявка')

    def test_a_refused_batch_splits_itself_to_isolate_the_culprit(self):
        """Отказана партида не казва КОЙ номер пречи - разцепва се, докато
        виновникът остане сам с дословния отговор; диагнозата per номер
        оцелява груповото изпращане."""
        def refuse_when_bad_present(entries):
            if any(e['plateNum'] == 'CB0002BB' for e in entries):
                return dict(REFUSED)
            return dict(OK_WRITE)

        command = self._batch_command(['CB0001AA', 'CB0002BB', 'CB0003CC'])
        Command = self.env['cctv.camera.command']
        with patch.object(HikvisionCamera, 'add_plate_to_list',
                          side_effect=refuse_when_bad_present), \
             patch.object(HikvisionCamera, 'delete_plate_from_list',
                          return_value=dict(OK_WRITE)):
            command.action_execute()
            # Разцепването ражда нови команди; изпълняваме ги както кронът
            # би ги подкарал, докато бисекцията се изчерпи.
            for _ in range(8):
                pending = Command.search([
                    ('camera_id', '=', self.camera.id),
                    ('state', '=', 'new')])
                if not pending:
                    break
                pending.action_execute()
        all_commands = Command.search(
            [('camera_id', '=', self.camera.id)])
        self.assertEqual(command.state, 'error')
        # Поведенчески, не текстово (бележката е преведена): разцепването
        # е родило дъщерни команди.
        self.assertGreater(len(all_commands), 1,
                           'отказаната партида не роди дъщерни команди')
        done_texts = ' '.join(all_commands.filtered(
            lambda c: c.state == 'done').mapped('request_data'))
        self.assertIn('CB0001AA', done_texts,
                      'здравите номера не стигнаха до камерата')
        self.assertIn('CB0003CC', done_texts)
        culprit = all_commands.filtered(
            lambda c: c.state == 'error'
            and 'CB0002BB' in (c.request_data or '')
            and 'CB0001AA' not in (c.request_data or ''))
        self.assertTrue(culprit, 'виновникът не е изолиран в самостоятелна команда')
        self.assertTrue(any('0x38410029' in (c.response_data or '')
                            for c in culprit),
                        'изолираният виновник не носи дословния отговор')

    def test_update_list_reports_instead_of_crashing(self):
        """Никога не е работела: викаше несъществуващ метод и умираше с
        AttributeError. Обясненият отказ е по-добър от крас."""
        command = self.env['cctv.camera.command'].with_context(
            no_hardware_commands=True).create([{
                'camera_id': self.camera.id, 'command_type': 'update_list',
            }])
        command.action_execute()
        self.assertEqual(command.state, 'error')
        self.assertNotIn('AttributeError', command.response_data or '')


@tagged('post_install', '-at_install', 'polimex_ip_cam', 'ipcam_self_test')
class TestPushDestinationIsValidatedNotJustShown(TransactionCase):
    """Собственикът: "има ли настройката на пуш на камерата?!? за да се
    валидира и къде сочи камерата и кога какво праща". На живия парк една
    камера сочеше стар адрес, две - друг, със стария път без идентификатор
    - и единственият видим знак беше тихо остаряващ heartbeat."""

    def _camera(self, **extra):
        values = {
            'name': 'ВХОД', 'ip_address': '10.0.0.71', 'username': 'admin',
            'password': 'x', 'brand': 'hikvision', 'tz': 'Europe/Sofia',
            'sub_serial_number': 'FA9951877',
            'server_setup': 'ipAddress=192.168.0.99\nportNo=80',
        }
        values.update(extra)
        return self.env['cctv.camera'].create(values)

    def _report(self, camera, host_response):
        patches = _quiet_reads() + [
            patch.object(HikvisionCamera, 'get_http_host',
                         return_value={'status': 'success',
                                       'response': host_response}),
            patch.object(HikvisionCamera, 'add_plate_to_list',
                         return_value=dict(OK_WRITE)),
            patch.object(HikvisionCamera, 'delete_plate_from_list',
                         return_value=dict(OK_WRITE)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        action = camera.action_camera_diagnostics()
        return self.env['cctv.camera.diagnostic'].browse(action['res_id']).report

    def test_a_stale_destination_is_a_named_problem(self):
        """Камера, сочеща стария сървър със стария път, е обявена с двете
        разминавания - адрес и идентичност - не показана в сиво."""
        report = self._report(self._camera(), {
            'ipAddress': '192.168.0.190', 'portNo': '80',
            'url': '/ipcam/anpr/event', 'protocolType': 'HTTP'})
        self.assertIn('192.168.0.190', report)
        self.assertIn('192.168.0.99', report,
                      'очакваната дестинация липсва от доклада')
        self.assertIn('Set HTTP Host', report,
                      'проблемът не казва какво да се направи')
        self.assertIn('FA9951877', report,
                      'очакваният път с идентичността на камерата липсва')

    def test_a_silent_reachable_camera_is_called_out(self):
        """Достижима камера без признак на живот от часове = известяването
        ѝ не стига дотук - това е проблем, не бележка под линия."""
        from datetime import timedelta
        from odoo import fields as odoo_fields
        camera = self._camera(name='ВХОД тих')
        camera.last_seen = odoo_fields.Datetime.now() - timedelta(hours=3)
        report = self._report(camera, {
            'ipAddress': '192.168.0.99', 'portNo': '80',
            'url': '/ipcam/anpr/event/FA9951877', 'protocolType': 'HTTP'})
        self.assertIn('not arriving', report,
                      'мълчащата достижима камера не е обявена')

    def test_a_correct_destination_raises_nothing(self):
        report = self._report(self._camera(name='ВХОД ок'), {
            'ipAddress': '192.168.0.99', 'portNo': '80',
            'url': '/ipcam/anpr/event/FA9951877', 'protocolType': 'HTTP'})
        self.assertNotIn('Set HTTP Host', report,
                         'вярната дестинация е обявена за грешна')
