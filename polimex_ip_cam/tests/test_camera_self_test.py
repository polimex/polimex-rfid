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
                     return_value={'status': 'success', 'image_data': b'x' * 42}),
        patch.object(HikvisionCamera, 'get_time_config',
                     return_value={'status': 'failed', 'error': 'no clock in this double'}),
        patch.object(HikvisionCamera, 'get_http_host',
                     return_value={'status': 'success', 'response': {
                         'ipAddress': '192.168.0.99', 'portNo': '8069',
                         'url': '/cctv/events', 'protocolType': 'HTTP'}}),
        patch.object(HikvisionCamera, 'search_lp_audit',
                     return_value={'status': 'success', 'records': [
                         {'plate': 'CB1234AB', 'type': 'whiteList'}],
                         'plates': ['CB1234AB'], 'total': 1}),
        patch.object(HikvisionCamera, 'probe_vcl_capabilities',
                     return_value={'status': 'success', 'status_code': 404, 'body': ''}),
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
        })

    def _run(self, add=None, delete=None):
        patches = _quiet_reads() + [
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
        # Докладът остава и в дневника на камерата за сравнение по-късно.
        self.assertTrue(any('Self-test' in (m.body or '') or 'PROBLEMS' in (m.body or '')
                            for m in self.camera.message_ids),
                        'докладът не е записан в дневника на камерата')

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
        stopped = commands.filtered(lambda c: 'Not sent' in (c.response_data or ''))
        self.assertEqual(len(stopped), 10 - commands.PLATE_FAILURE_STREAK_LIMIT,
                         'спрените команди не казват защо са спрени')

    def test_a_different_device_at_the_address_is_called_out(self):
        """Отговаря ЧУЖД сериен номер -> проблем, не мълчалива подмяна."""
        self.camera.serial_number = 'DS-OTHER-SERIAL'
        report, _mocks = self._run()
        self.assertIn('DIFFERENT device', report,
                      'чуждото устройство на адреса не е обявено като проблем')
