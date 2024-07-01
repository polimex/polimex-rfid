# Copyright 2022 Polimex Holding Ltd..
# License APL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


class RFIDController(RFIDAppCase):
    def setUp(self):
        super(RFIDController, self).setUp()
        self.c_50 = None
        self.c_110 = None
        self.c_115 = None
        self.c_Relay = None
        self.c_130 = None
        self.c_180 = None
        self.c_turnstile = None
        self.c_vending = None
        self.c_temperature = None
        self.default_F0 = {
            6: '0006000400000704000000030000030201050208000200010502060003000506',  # iCON110
            9: '0009050006030704010000090000080201050208000101050807000008010900',  # Turnstile
            11: '0101000202000704000000050000040201050208010200090702070003000506',  # iCON115
            12: '0102000000010703090000010000030100000208000100010502060003000506',  # iCON50
            16: '0106000003090704020000010000010201050200002200090702070003000506',  # Vending Controller
            17: '0107000601000703090000090000080401050208000401050807000008010900',  # iCON130
            22: '0202000207080704040000050000040001050208000200000102070004000604',  # Temperature Controller
            30: '0300070004060704010000050001000200080206000200090702070003000506',  # Relay controller 30
            31: '0301070004060704010000050001000200080206000200090702070003000506',  # Relay controller 31
            32: '0302070004060704010000050001000200080206000200090702070003000506',  # Relay controller 32
        }
        self.default_B3 = {
            6: '000000000771000002060422000000000000000000000000',  # iCON110
            9: '00006E010752079200000000000000000000000000000000',  # Turnstile
            11: '000001000335000000000000000000000000050204000000',  # iCON115
            12: '000000000686000000000000000000000000010802000000',  # iCON50
            16: '00006E010752079200000000000000000000000000000000',  # Vending Controller
            17: '00006E010752079200000000000000000000000000000000',  # iCON130
            22: '000000000875000001840390000000000000000802000000',  # Temperature Controller
            30: '000001000335000000000000000000000000050204000000',  # Relay controller 30
            31: '000001000335000000000000000000000000050204000000',  # Relay controller 31
            32: '000001000335000000000000000000000000050204000000',  # Relay controller 32
        }
    # Create controllers

    def _add_Vending(self, module=234567, key='0000', id=None):
        id = id or self._get_id_num()
        self.c_vending = self.env['hr.rfid.ctrl'].create({
            'name': 'Turnstile Vending',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_vending.read_controller_information_cmd()

        response = self._hearbeat(self.c_vending.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, '(%s)' % self.c_vending.name)
        response = self._send_cmd_response(response, self.default_F0[16])
        self.assertTrue(
            response['cmd']['c'] == 'D5' and response['cmd']['d'] == '22', '(%s)' % self.c_vending.name)  # {'cmd': {'id': 7, 'c': 'D5', 'd': '22'}}
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F0', '(%s)' % self.c_vending.name)
        response = self._send_cmd_response(response, self.default_F0[16])
        self.assertTrue(response['cmd']['c'] == 'D7', '(%s)' % self.c_vending.name)  #
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_vending.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_vending.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6', '(%s)' % self.c_vending.name)
        response = self._send_cmd_response(response, '010100010100010100010100')
        self.assertTrue(response['cmd']['c'] == 'F9' and response['cmd']['d'] == '01', '(%s)' % self.c_vending.name)
        response = self._process_io_table(response, self.c_vending)
        self.assertTrue(response['cmd']['c'] == 'B3', '(%s)' % self.c_vending.name)
        response = self._send_cmd_response(response, self.default_B3[16])
        self.assertTrue(response['cmd']['c'] == 'FB')
        response = self._send_cmd_response(response, '0f000000')
        self.assertTrue(response == {}, '(%s)' % self.c_vending.name)

    def _add_Turnstile(self, module=234567, key='0000', id=None):
        id = id or self._get_id_num()
        self.c_turnstile = self.env['hr.rfid.ctrl'].create({
            'name': 'Turnstile iCON Turnstile',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_turnstile.read_controller_information_cmd()

        response = self._hearbeat(self.c_turnstile.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, '(%s)' % self.c_turnstile.name)

        response = self._send_cmd_response(response, self.default_F0[9])
        self.assertTrue(response['cmd']['c'] == 'D7', '(%s)' % self.c_turnstile.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_turnstile.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_turnstile.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6', '(%s)' % self.c_turnstile.name)
        response = self._send_cmd_response(response, '010100010100010100010100')
        response = self._process_io_table(response, self.c_turnstile, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3', '(%s)' % self.c_turnstile.name)
        response = self._send_cmd_response(response, self.default_B3[9])
        self.assertTrue(response['cmd']['c'] == 'FB')
        response = self._send_cmd_response(response, '0f000000')
        self.assertTrue(response['cmd']['c'] == 'FC')
        response = self._send_cmd_response(response, '00')
        self.assertTrue(response == {}, '(%s)' % self.c_turnstile.name)

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
        self.assertTrue(response['cmd']['c'] == 'FB')
        response = self._send_cmd_response(response, '7f7f0000')
        self.assertTrue(response == {})

    def _add_iCon130(self, module=234567, key='0000', id=None):
        id = id or self._get_id_num()
        self.c_130 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON130',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_130.read_controller_information_cmd()

        response = self._hearbeat(self.c_130.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, '(%s)' % self.c_130.name)

        response = self._send_cmd_response(response, self.default_F0[17])
        self.assertTrue(response['cmd']['c'] == 'D7', '(%s)' % self.c_130.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_130.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_130.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6', '(%s)' % self.c_130.name)
        response = self._send_cmd_response(response, '010100010100010100010100')
        response = self._process_io_table(response, self.c_130, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3', '(%s)' % self.c_130.name)
        response = self._send_cmd_response(response, self.default_B3[17])
        self.assertTrue(response['cmd']['c'] == 'FB')
        response = self._send_cmd_response(response, '0f000000')
        self.assertTrue(response == {}, '(%s)' % self.c_130.name)

    def _add_RelayController(self, module=234567, key='0000', id=None):
        id = id or self._get_id_num()
        self.c_Relay = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller Relay',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_Relay.read_controller_information_cmd()

        response = self._hearbeat(self.c_Relay.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, '(%s)' % self.c_Relay.name)

        response = self._send_cmd_response(response, self.default_F0[30])
        self.assertTrue(response['cmd']['c'] == 'D7', '(%s)' % self.c_Relay.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_Relay.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_Relay.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6', '(%s)' % self.c_Relay.name)
        response = self._send_cmd_response(response, '010402010100000000000000')
        response = self._process_io_table(response, self.c_Relay, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3', '(%s)' % self.c_Relay.name)
        response = self._send_cmd_response(response, self.default_B3[30])
        self.assertTrue(response['cmd']['c'] == 'FB')
        response = self._send_cmd_response(response, '07000000')
        self.assertTrue(response == {}, '(%s)' % self.c_Relay.name)

    def _add_iCon115(self, module=234567, key='0000', id=None):
        id = id or self._get_id_num()
        self.c_115 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON115',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_115.read_controller_information_cmd()

        response = self._hearbeat(self.c_115.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, '(%s)' % self.c_115.name)

        response = self._send_cmd_response(response, self.default_F0[11])
        self.assertTrue(response['cmd']['c'] == 'D7', '(%s)' % self.c_115.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_115.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_115.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6', '(%s)' % self.c_115.name)
        response = self._send_cmd_response(response, '010402010100000000000000')
        response = self._process_io_table(response, self.c_115, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3', '(%s)' % self.c_115.name)
        response = self._send_cmd_response(response, self.default_B3[11])
        self.assertTrue(response['cmd']['c'] == 'FB')
        response = self._send_cmd_response(response, '07000000')
        self.assertTrue(response == {}, '(%s)' % self.c_115.name)

    def _add_iCon110(self, module=234567, key='0000', id=None):
        id = id or self._get_id_num()
        self.c_110 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON110',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_110.read_controller_information_cmd()

        response = self._hearbeat(self.c_110.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, '(%s)' % self.c_110.name)

        response = self._send_cmd_response(response, self.default_F0[6])
        self.assertTrue(response['cmd']['c'] == 'D7', '(%s)' % self.c_110.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_110.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_110.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6', '(%s)' % self.c_110.name)
        response = self._send_cmd_response(response, '010402010100000000000000')
        response = self._process_io_table(response, self.c_110, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3', '(%s)' % self.c_110.name)
        response = self._send_cmd_response(response, self.default_B3[6])
        self.assertTrue(response['cmd']['c'] == 'FB')
        response = self._send_cmd_response(response, '07000000')
        self.assertTrue(response == {}, '(%s)' % self.c_110.name)

    def _add_iCon50(self, module=234567, key='0000', id=None):
        id = id or self._get_id_num()
        self.c_50 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON50',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_50.read_controller_information_cmd()
        response = self._hearbeat(self.c_50.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, '(%s)' % self.c_50.name)
        # tmp = self._make_F0(12, 1, 739, 1, 1, 3, 4, 28, 0, 3500, 1500)
        response = self._send_cmd_response(response, self.default_F0[12])
        self._check_added_controller(self.c_50)
        self.assertTrue(response['cmd']['c'] == 'D7', '(%s)' % self.c_50.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_50.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_50.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6', '(%s)' % self.c_50.name)
        response = self._send_cmd_response(response, '010000000000000000000000')
        response = self._process_io_table(response, self.c_50, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, self.default_B3[12])
        self.assertTrue(response['cmd']['c'] == 'FB')
        response = self._send_cmd_response(response, '01000000')
        self.assertTrue(response == {}, '(%s)' % self.c_50.name)

    def _add_Temperature(self, module=234567, key='0000', id=None):
        id = id or self._get_id_num()
        self.c_temperature = self.env['hr.rfid.ctrl'].create({
            'name': 'Temperature Controller',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_temperature.read_controller_information_cmd()
        response = self._hearbeat(self.c_temperature.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, '(%s)' % self.c_temperature.name)
        # tmp = self._make_F0(12, 1, 739, 1, 1, 3, 4, 28, 0, 3500, 1500 )
        response = self._send_cmd_response(response, self.default_F0[22])
        self._check_added_controller(self.c_temperature)
        self.assertTrue(response['cmd']['c'] == 'D7', '(%s)' % self.c_temperature.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_temperature.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_temperature.name)
        response = self._send_cmd_response(response)
        response = self._process_io_table(response, self.c_temperature, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3', '(%s)' % self.c_temperature.name)
        response = self._send_cmd_response(response, self.default_B3[22])
        self.assertTrue(response['cmd']['c'] == 'FB')
        response = self._send_cmd_response(response, '0f000000')
        self.assertEqual(response['cmd']['c'],'F2', '(%s)' % self.c_temperature.name)
        response = self._send_cmd_response(response, '0000000004')
        self.assertEqual(self.c_temperature.cards_count, 4, '(%s)' % self.c_temperature.name)
        self.assertTrue(response['cmd']['c'] == 'B1' and response['cmd']['d'] == '01', '(%s)' % self.c_temperature.name)
        response = self._send_cmd_response(response, '01040000500010')
        self.assertTrue(response['cmd']['c'] == 'F2' and response['cmd']['d'] == '000000000104',
                        '(%s)' % self.c_temperature.name)
        response = self._send_cmd_response(response,
                                           '02080800020807050d000001030c0d0b02010208000d070907050d000001030c020301010208010f0d0d07050d000001030c030a040102080f0b090107050d000001030c00070000')
        self.assertTrue(response == {}, '(%s)' % self.c_temperature.name)
        self.assertTrue(len(self.c_temperature.sensor_ids) == 4, '(%s)' % self.c_temperature.name)
        self.c_temperature.sensor_ids[2].active = False
        # self.assertTrue(response['cmd']['c'] == 'B4')
        # response = self._send_cmd_response(response, '01900000018500000195000001900000')
        response = self._hearbeat(self.c_temperature.webstack_id)
        self.assertTrue(
            response['cmd']['c'] == 'D1' and response['cmd']['d'].upper() == '0208000D070907050D000001030C02030100',
            '(%s)' % self.c_temperature.name)
        self._send_cmd_response(response)
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
