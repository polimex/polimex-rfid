# Copyright 2022 Polimex Holding Ltd..
# License APL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.hr_rfid.tests.common import RFIDAppCase
from odoo.tests.common import HttpCase, tagged
import json


@tagged('rfid')
class RFIDController(RFIDAppCase, HttpCase):
    def test_app(self):
        self._add_iCon50()

        self._add_iCon110()

        self._add_iCon115()

        self._add_iCon130()

        # self._add_iCon180()

        # self._add_Turnstile()

    def _add_Turnstile(self, module=234567, key='0000', id=6):
        c_turnstile = self.env['hr.rfid.ctrl'].create({
            'name': 'Turnstile iCONturnstile',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        c_turnstile.read_controller_information_cmd()

        response = self._hearbeat(serial=module, key=key)
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
        c_180 = self.env['hr.rfid.ctrl'].create({
# Copyright 2022 Polimex Holding Ltd..
            'name': 'Controller iCON180',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        c_180.read_controller_information_cmd()

        response = self._hearbeat(serial=module, key=key)
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
        response = self._process_io_table(response, c_180, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '00006E010752079200000000000000000000000000000000')
        self.assertTrue(response == {})

    def _add_iCon130(self, module=234567, key='0000', id=4):
        c_130 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON130',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        c_130.read_controller_information_cmd()

        response = self._hearbeat(serial=module, key=key)
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
        response = self._process_io_table(response, c_130, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '00006E010752079200000000000000000000000000000000')
        self.assertTrue(response == {})

    def _add_iCon115(self, module=234567, key='0000', id=3):
        c_115 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON115',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        c_115.read_controller_information_cmd()

        response = self._hearbeat(serial=module, key=key)
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
        response = self._process_io_table(response, c_115, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '000001000335000000000000000000000000050204000000')
        self.assertTrue(response == {})

    def _add_iCon110(self, module=234567, key='0000', id=2):
        c_110 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON110',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        c_110.read_controller_information_cmd()

        response = self._hearbeat(serial=module, key=key)
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
        response = self._process_io_table(response, c_110, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '000000000771000002060422000000000000000000000000')
        self.assertTrue(response == {})

    def _add_iCon50(self, module=234567, key='0000', id=1):
        c_50 = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller iCON50',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        c_50.read_controller_information_cmd()
        response = self._hearbeat(serial=module, key=key)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, )

        response = self._send_cmd_response(response, '0102000002060703090000010000030100000208000100010502060003000506')
        self.assertTrue(response['cmd']['c'] == 'D7')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6')
        response = self._send_cmd_response(response, '010402010100000000000000')
        response = self._process_io_table(response, c_50, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '000000000771000002060422000000000000000000000000')
        self.assertTrue(response == {})
