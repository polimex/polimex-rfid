# Copyright 2022 Polimex Holding Ltd..
# License APL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.hr_rfid.tests.common import RFIDAppCase
from odoo.tests.common import HttpCase, tagged
import json

import logging

_logger = logging.getLogger(__name__)


@tagged('rfid')
class RFIDController(RFIDAppCase, HttpCase):
    def test_app(self):
        _logger.info('Start tests for iCON50 ')
        self._add_iCon50()
        self._test_R_event(self.c_50)
        _logger.info('Start tests for iCON110 ')
        self._add_iCon110()
        self._test_R1R2(self.c_110)
        # self._change_mode(self.c_110, 2)
        self._ev64(self.c_110)

        _logger.info('Start tests for iCON115 ')
        self._add_iCon115()
        self._test_R1R2(self.c_115)
        _logger.info('Start tests for iCON130 ')
        self._add_iCon130()
        self._test_R1R2R3R4(self.c_130)
        # _logger.info('Start tests for iCON180 ')
        # self._add_iCon180()
        # _logger.info('Start tests for Turnstile ')
        # self._add_Turnstile()
        _logger.info('Start tests for Temperature ')
        self._add_Temperature()
        pass

    def _add_Turnstile(self, module=234567, key='0000', id=6):
        c_turnstile = self.env['hr.rfid.ctrl'].create({
            'name': 'Turnstile iCONturnstile',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        c_turnstile.read_controller_information_cmd()

        response = self._hearbeat(self.c_turnstile.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, )

        response = self._send_cmd_response(response, '0009000601000703090000090000080401050208000401050807000008010900')
        self.assertTrue(response['cmd']['c'] == 'D7')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6')
        response = self._send_cmd_response(response, '010100010100010100010100')
        response = self._process_io_table(response, c_turnstile, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '00006E010752079200000000000000000000000000000000')
        self.assertTrue(response == {})

    def _add_iCon180(self, module=234567, key='0000', id=5):
        self.c_180 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON180',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_180.read_controller_information_cmd()

        response = self._hearbeat(self.c_180.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, )

        response = self._send_cmd_response(response, '0107000601000703090000090000080401050208000401050807000008010900')
        self.assertTrue(response['cmd']['c'] == 'D7')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6')
        response = self._send_cmd_response(response, '010100010100010100010100')
        response = self._process_io_table(response, self.c_180, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '00006E010752079200000000000000000000000000000000')
        self.assertTrue(response == {})

    def _add_iCon130(self, module=234567, key='0000', id=4):
        self.c_130 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON130',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_130.read_controller_information_cmd()

        response = self._hearbeat(self.c_130.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, )

        response = self._send_cmd_response(response, '0107000601000703090000090000080401050208000401050807000008010900')
        self.assertTrue(response['cmd']['c'] == 'D7')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6')
        response = self._send_cmd_response(response, '010100010100010100010100')
        response = self._process_io_table(response, self.c_130, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '00006E010752079200000000000000000000000000000000')
        self.assertTrue(response == {})

    def _add_iCon115(self, module=234567, key='0000', id=3):
        self.c_115 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON115',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_115.read_controller_information_cmd()

        response = self._hearbeat(self.c_115.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, )

        response = self._send_cmd_response(response, '0101000202000704000000050000040201050208010200090702070003000506')
        self.assertTrue(response['cmd']['c'] == 'D7')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6')
        response = self._send_cmd_response(response, '010402010100000000000000')
        response = self._process_io_table(response, self.c_115, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '000001000335000000000000000000000000050204000000')
        self.assertTrue(response == {})

    def _add_iCon110(self, module=234567, key='0000', id=2):
        self.c_110 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON110',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_110.read_controller_information_cmd()

        response = self._hearbeat(self.c_110.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, )

        response = self._send_cmd_response(response, '0006000400000704000000030000030201050208000200010502060003000506')
        self.assertTrue(response['cmd']['c'] == 'D7')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6')
        response = self._send_cmd_response(response, '010402010100000000000000')
        response = self._process_io_table(response, self.c_110, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '000000000771000002060422000000000000000000000000')
        self.assertTrue(response == {})

    def _add_iCon50(self, module=234567, key='0000', id=1):
        self.c_50 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON50',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_50.read_controller_information_cmd()
        response = self._hearbeat(self.c_50.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, )
        tmp = self._make_F0(12, 1, 739, 1, 1, 3, 4, 28, 0, 3500, 1500)
        response = self._send_cmd_response(response, '0102000000010703090000010000030100000208000100010502060003000506')
        self._check_added_controller(self.c_50)
        self.assertTrue(response['cmd']['c'] == 'D7')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6')
        response = self._send_cmd_response(response, '010000000000000000000000')
        response = self._process_io_table(response, self.c_50, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '000000000686000000000000000000000000010802000000')
        self.assertTrue(response == {})

    def _add_Temperature(self, module=234567, key='0000', id=22):
        self.c_temperature = self.env['hr.rfid.ctrl'].create({
            'name': 'Temperature Controller',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_temperature.read_controller_information_cmd()
        response = self._hearbeat(self.c_temperature.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, )
        # tmp = self._make_F0(12, 1, 739, 1, 1, 3, 4, 28, 0, 3500, 1500 )
        response = self._send_cmd_response(response, '0202000207080704040000050000040001050208000200000102070004000604')
        self._check_added_controller(self.c_temperature)
        self.assertTrue(response['cmd']['c'] == 'D7')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        response = self._process_io_table(response, self.c_temperature, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '000000000875000001840390000000000000000802000000')
        self.assertTrue(response['cmd']['c'] == 'F2')
        response = self._send_cmd_response(response, '0000000004')
        self.assertEqual(self.c_temperature.cards_count, 4)
        self.assertTrue(response['cmd']['c'] == 'B1' and response['cmd']['d'] == '01')
        response = self._send_cmd_response(response, '01040000500010')
        self.assertTrue(response['cmd']['c'] == 'F2' and response['cmd']['d'] == '000000000104')
        response = self._send_cmd_response(response,
                                           '02080800020807050d000001030c0d0b02010208000d070907050d000001030c020301010208010f0d0d07050d000001030c030a040102080f0b090107050d000001030c00070000')
        self.assertTrue(response == {})
        self.assertTrue(len(self.c_temperature.sensor_ids) == 4)
        self.c_temperature.sensor_ids[2].active = False
        # self.assertTrue(response['cmd']['c'] == 'B4')
        # response = self._send_cmd_response(response, '01900000018500000195000001900000')
        response = self._hearbeat(self.c_temperature.webstack_id)
        self.assertTrue(
            response['cmd']['c'] == 'D1' and response['cmd']['d'].upper() == '0208000D070907050D000001030C02030100')
        # {'convertor': 428030,
        #  'event': {'bos': 1, 'card': '0000000000', 'cmd': 'FA', 'date': '11.07.22', 'day': 1, 'dt': '01900000',
        #            'err': 0, 'event_n': 52, 'id': 29, 'reader': 2, 'time': '11:41:39', 'tos': 282},
        #  'key': '1764'}
        # {"c": "FA", "d": "0000000002 0000000001 34363922050411220000000002000000040002000000", "e": 0, "id": 29}

        self._send_cmd({
            "convertor": self.c_temperature.webstack_id.serial,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": '0000000000',
                      "cmd": "FA",
                      "time": self.test_time_10_3,
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "02560000",
                      "err": 0,
                      "event_n": 51,
                      "id": self.c_temperature.ctrl_id,
                      "reader": 2},
            "key": self.c_temperature.webstack_id.key
        }, system_event=True)

        self._send_cmd({
            "convertor": self.c_temperature.webstack_id.serial,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": '0000000000',
                      "cmd": "FA",
                      "time": self.test_time_10_3,
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "01900000",
                      "err": 0,
                      "event_n": 52,
                      "id": self.c_temperature.ctrl_id,
                      "reader": 2},
            "key": self.c_temperature.webstack_id.key
        })

        self._send_cmd({
            "convertor": self.c_temperature.webstack_id.serial,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": '0000000000',
                      "cmd": "FA",
                      "time": self.test_time_10_3,
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00800000",
                      "err": 0,
                      "event_n": 53,
                      "id": self.c_temperature.ctrl_id,
                      "reader": 2},
            "key": self.c_temperature.webstack_id.key
        }, system_event=True)

        pass
