# -*- coding: utf-8 -*-
"""Записът към камерата се лекува сам, а номерата пристигат.

Бизнес твърдения (живият отказ при клиента, 2026-08-16, V5.5.0 - 400
badParameters на всеки от 1394 записа, докато списъкът стои празен):
1. Прозорецът на валидност важи по СТЕННИЯ часовник на камерата: времената
   пътуват без 'Z' и в нейната зона, не в UTC (валидираният формат е без
   суфикс; изместен прозорец пуска колата в грешните часове).
2. Камера, която отказва НЕЗАДЪЛЖИТЕЛНА подробност (свързана карта,
   прозорец), пак получава НОМЕРА - подробността се оттегля, номерът влиза.
3. Откритата работеща форма се помни на камерата и се казва веднъж -
   следващите записи не изтъргуват същите откази наново.
4. Отказ по всички форми си остава отказ - с дословния отговор на камерата.
"""
import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.polimex_ip_cam.helpers import camera_api
from odoo.addons.polimex_ip_cam.helpers.camera_api import HikvisionCamera


class _Resp:
    def __init__(self, status_code=200, text='{"statusCode":1}'):
        self.status_code = status_code
        self.text = text


REFUSAL = _Resp(400, '{"statusCode":6,"statusString":"Invalid XML Content",'
                     '"subStatusCode":"badParameters","MErrCode":"0x38410029"}')


def _cam(**kwargs):
    kwargs.setdefault('tz', 'Europe/Sofia')
    return HikvisionCamera('10.0.0.7', 80, 'admin', 'x', **kwargs)


@tagged('post_install', '-at_install', 'polimex_ip_cam', 'ipcam_lpaudit')
class TestValidityTimesSpeakTheCameraClock(TransactionCase):

    def test_utc_times_become_camera_wall_clock_without_suffix(self):
        """Прозорец 10:00Z за камера в София = 13:00 местно, без 'Z'."""
        info = _cam()._lp_record_info({
            'plateNum': 'CB5803CM', 'listType': '0',
            'startTime': '2026-05-01T10:00:00Z',
            'endTime': '2026-05-01T18:30:00Z',
        })
        self.assertEqual(info['createTime'], '2026-05-01T13:00:00')
        self.assertEqual(info['effectiveTime'], '2026-05-01T21:30:00')

    def test_naive_times_pass_through_untouched(self):
        """Час без зона е нечий избор - не го местим втори път."""
        info = _cam()._lp_record_info({
            'plateNum': 'CB0001AA', 'listType': '0',
            'startTime': '2026-06-16T15:00:00',
        })
        self.assertEqual(info['createTime'], '2026-06-16T15:00:00')

    def test_garbage_times_are_the_cameras_call(self):
        info = _cam()._lp_record_info({
            'plateNum': 'CB0001AA', 'listType': '0',
            'startTime': 'not-a-time',
        })
        self.assertEqual(info['createTime'], 'not-a-time')


@tagged('post_install', '-at_install', 'polimex_ip_cam', 'ipcam_lpaudit')
class TestTheWriteLadder(TransactionCase):

    def _put_refusing_cards(self, calls):
        def fake_put(url, **kwargs):
            body = json.loads(kwargs['data'])
            if 'DelLicensePlateAuditData' in url:
                calls.append('delete')
                return _Resp()
            record = body['LicensePlateInfoList'][0]
            calls.append(record)
            if record.get('cardNo'):
                return REFUSAL
            return _Resp()
        return fake_put

    def test_a_refused_card_number_does_not_cost_the_plate(self):
        """Фирмуер, който отказва свързаната карта, пак получава номера.

        Пътят е каноничен: запис -> (изтегляне + повторен запис, ако
        номерът вече съществува) -> запис без картата. Отказът тук не
        зависи от съществуването, затова минава чак третата стъпка."""
        calls = []
        cam = _cam()
        cam._lp_audit_api = True
        with patch.object(camera_api.requests, 'put',
                          side_effect=self._put_refusing_cards(calls)):
            result = cam.add_plate_to_list([{
                'plateNum': 'CB5803CM', 'listType': '0', 'cardNo': '0000012345',
            }])
        self.assertEqual(result['status'], 'success',
                         'номерът се загуби заради незадължителна подробност')
        self.assertEqual(result['shape_used'], 'no_card')
        adds = [c for c in calls if c != 'delete']
        self.assertEqual(adds[-1]['cardNo'], '',
                         'финалният опит трябва да оттегли картата, не да я повтори')
        self.assertEqual(len(adds), 3,
                         'редът е запис -> повторен запис след изтегляне -> без карта')
        self.assertIn('delete', calls, 'replace стъпката липсва')

    def test_a_remembered_shape_skips_the_doomed_attempt(self):
        """Запомнената форма праща записа директно - един опит, не два."""
        calls = []
        cam = _cam(record_shape='no_card')
        cam._lp_audit_api = True
        with patch.object(camera_api.requests, 'put',
                          side_effect=self._put_refusing_cards(calls)):
            result = cam.add_plate_to_list([{
                'plateNum': 'CB6605BE', 'listType': '0', 'cardNo': '0000012345',
            }])
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(calls), 1,
                         'камерата пак беше обстрелвана с форма, която отказва')

    def test_refused_everywhere_stays_refused_with_the_cameras_words(self):
        cam = _cam()
        cam._lp_audit_api = True
        with patch.object(camera_api.requests, 'put', return_value=REFUSAL):
            result = cam.add_plate_to_list([{'plateNum': 'CB0000XX', 'listType': '0'}])
        self.assertEqual(result['status'], 'failed')
        self.assertIn('0x38410029', str(result['error']),
                      'дословният отговор на камерата се губи')

    def test_a_plate_already_on_the_camera_is_replaced_not_lost(self):
        """Живият обект: камерите пазят списъците от старата система и
        този фирмуер отказва запис върху съществуващ номер. Номерът не
        се губи - изтегля се и се записва наново (replace, не гадаене)."""
        seen = []

        def fake_put(url, **kwargs):
            body = json.loads(kwargs['data'])
            if 'DelLicensePlateAuditData' in url:
                seen.append('delete')
                return _Resp()
            seen.append('add')
            # Отказва, докато номерът "съществува"; след изтриване минава.
            return _Resp() if 'delete' in seen else REFUSAL

        cam = _cam()
        cam._lp_audit_api = True
        with patch.object(camera_api.requests, 'put', side_effect=fake_put):
            result = cam.add_plate_to_list([{'plateNum': 'PB4181KC',
                                             'listType': '0'}])
        self.assertEqual(result['status'], 'success',
                         'номер, който камерата вече държи, се изгуби')
        self.assertTrue(result.get('replaced'))
        self.assertEqual(seen, ['add', 'delete', 'add'],
                         'редът е запис -> изтегляне -> запис, нищо повече')


@tagged('post_install', '-at_install', 'polimex_ip_cam', 'ipcam_lpaudit')
class TestTheCameraRemembersItsShape(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.camera = cls.env['cctv.camera'].create({
            'name': 'Вход', 'ip_address': '10.0.0.7', 'username': 'admin',
            'password': 'x', 'brand': 'hikvision', 'tz': 'Europe/Sofia',
        })

    def test_the_discovered_shape_is_persisted_and_announced_once(self):
        """Първата команда открива формата; втората я ползва наготово."""
        command = self.env['cctv.camera.command'].with_context(
            no_hardware_commands=True).create([{
                'camera_id': self.camera.id, 'command_type': 'add_plate',
                'request_data': 'plateNum=CB5803CM\nlistType=0\ncardNo=0000012345',
            }])
        with patch.object(HikvisionCamera, 'add_plate_to_list',
                          return_value={'status': 'success',
                                        'shape_used': 'no_card'}):
            command.action_execute()
        self.assertEqual(command.state, 'done')
        self.assertEqual(self.camera.lp_record_shape, 'no_card',
                         'откритата форма не се помни - всяка команда ще я '
                         'преоткрива с излишни откази')
        notes = self.camera.message_ids.filtered(
            lambda m: 'record' in (m.body or '') or 'запис' in (m.body or ''))
        self.assertTrue(notes, 'операторът не е уведомен, че записите са '
                               'понижени - тихо понижение')
        api = self.camera.get_api()
        self.assertEqual(api.record_shape, 'no_card',
                         'следващата връзка не тръгва от запомнената форма')
