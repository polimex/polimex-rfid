# Copyright 2022 Polimex Holding Ltd..
# License APL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_rfid.tests.common import RFIDAppCase
from odoo.tests.common import HttpCase, tagged
from odoo import fields
import json

import logging

_logger = logging.getLogger(__name__)


@tagged('rfid')
class RFIDController(RFIDAppCase, HttpCase):
    def test_app(self):
        _logger.info('Start tests for iCON50 ')
        self._add_iCon50()
        self._test_R_event(self.c_50)
        self._test_add_remove_card_partner(self.c_50)
        self._test_add_remove_card_employee(self.c_50)
        self._test_Duress(self.c_50)
        self._test_inputs(self.c_50)
        self._ev64(self.c_50)

        # Check for not processed responses
        response = self._hearbeat(self.test_webstack_10_3_id)
        self.assertEqual(response, {})

        _logger.info('Start tests for iCON110 ')
        self._add_iCon110()
        self._test_R1R2(self.c_110)
        self._test_add_remove_card_partner(self.c_110)
        self._test_add_remove_card_employee(self.c_110)
        self._test_Duress(self.c_110)
        self._test_inputs(self.c_110)
        self._ev64(self.c_110)

        # Check for not processed responses
        response = self._hearbeat(self.test_webstack_10_3_id)
        self.assertEqual(response, {})

        _logger.info('Start tests for iCON115 ')
        self._add_iCon115()
        self._test_R1R2(self.c_115)
        self._test_add_remove_card_partner(self.c_115)
        self._test_add_remove_card_employee(self.c_115)
        self._ev64(self.c_115)

        # Check for not processed responses
        response = self._hearbeat(self.test_webstack_10_3_id)
        self.assertEqual(response, {})

        _logger.info('Start tests for Relay Controller ')
        self._add_RelayController()
        self._test_R1R2(self.c_Relay)
        self._test_add_remove_card_partner(self.c_Relay)
        self._test_add_remove_card_employee(self.c_Relay)
        # self._ev64(self.c_Relay) # TODO Check details

        _logger.info('Start tests for iCON130 ')
        self._add_iCon130()
        self._test_R1R2R3R4(self.c_130)
        self._test_add_remove_card_partner(self.c_130)
        self._test_add_remove_card_employee(self.c_130)
        self._ev64(self.c_130)

        # _logger.info('Start tests for iCON180 ')
        # self._add_iCon180()

        # Check for not processed responses
        # response = self._hearbeat(self.test_webstack_10_3_id)
        # self.assertEqual(response, {})

        _logger.info('Start tests for Turnstile ')
        self._add_Turnstile()

        # Check for not processed responses
        response = self._hearbeat(self.test_webstack_10_3_id)
        self.assertEqual(response, {})

        _logger.info('Start tests for Temperature ')
        self._add_Temperature()
        pass

        # Check for not processed responses
        response = self._hearbeat(self.test_webstack_10_3_id)
        self.assertEqual(response, {})

        self._test_global_APB()


    def _test_add_remove_card_employee(self, ctrl):
        # fix ag validity
        self._check_no_cmd(ctrl)

        test_ag_id = self.env['hr.rfid.access.group'].create({
            'name': 'Test Access Group 2',
            'company_id': self.test_company_id,
            'door_ids': [(0, 0, {'door_id': d_id}) for d_id in ctrl.door_ids.mapped('id')]
        })
        # assign AG to department
        self.test_employee_id.department_id.write({
            'hr_rfid_allowed_access_groups': [(4, test_ag_id.id, 0)],
        })

        # AG in future
        test_employee_ag_rel = self.env['hr.rfid.access.group.employee.rel'].create({
            'access_group_id': test_ag_id.id,
            'employee_id': self.test_employee_id.id,
            'activate_on': fields.Datetime.now() + relativedelta(hours=1),
            'expiration': fields.Datetime.now() + relativedelta(hours=2),
            'visits_counting': True,
            'permitted_visits': 1,
        })
        # tmp = test_partner_ag_rel.state

        # check no generated commands
        self._check_no_cmd(ctrl)
        # make ag active for cron activation
        test_employee_ag_rel.activate_on = fields.Datetime.now() + relativedelta(minutes=-1)
        # check generated commands
        self._check_cmd_add_card_and_remove(ctrl)
        self._check_no_cmd(ctrl)

        # make ag inactive for cron activation
        test_employee_ag_rel.write({
            'activate_on': fields.Datetime.now() + relativedelta(minutes=-3),
            'expiration': fields.Datetime.now() + relativedelta(minutes=-1),
        })

        # check generated commands
        self._check_cmd_delete_card_and_remove(ctrl)
        self._check_no_cmd(ctrl)

        # make ag active with 1 visit to check stop after visit counting
        test_employee_ag_rel.write({
            'activate_on': fields.Datetime.now() + relativedelta(minutes=-3),
            'expiration': fields.Datetime.now() + relativedelta(minutes=+3),
        })
        self._check_cmd_add_card_and_remove(ctrl)
        self._check_no_cmd(ctrl)

        test_employee_ag_rel.write({
            'visits_counter': 1,
        })
        # check generated commands
        self._check_cmd_delete_card_and_remove(ctrl)
        self._check_no_cmd(ctrl)

        # Cleanup all local data
        test_ag_id.unlink()
        # self._clear_ctrl_cmd(ctrl)

    def _test_add_remove_card_partner(self, ctrl):
        # fix ag validity
        self._check_no_cmd(ctrl)

        test_ag_id = self.env['hr.rfid.access.group'].create({
            'name': 'Test Access Group 1',
            'company_id': self.test_company_id,
            'door_ids': [(0, 0, {'door_id': d_id}) for d_id in ctrl.door_ids.mapped('id')]
        })

        # AG in future
        test_partner_ag_rel = self.env['hr.rfid.access.group.contact.rel'].create({
            'access_group_id': test_ag_id.id,
            'contact_id': self.test_partner.id,
            'activate_on': fields.Datetime.now() + relativedelta(hours=1),
            'expiration': fields.Datetime.now() + relativedelta(hours=2),
            'visits_counting': True,
            'permitted_visits': 1,
        })
        # card in past
        self.test_card_partner.activate_on = fields.Datetime.now() + relativedelta(hours=-1)
        self.test_card_partner.deactivate_on = fields.Datetime.now() + relativedelta(minutes=-30)
        # tmp = test_partner_ag_rel.state

        # check no generated commands
        self._check_no_cmd(ctrl)
        # make ag active for cron activation
        test_partner_ag_rel.activate_on = fields.Datetime.now() + relativedelta(minutes=-1)
        # check no generated commands because card validity
        self._check_no_cmd(ctrl)
        # card in presence
        self.test_card_partner.write(
            {'activate_on': fields.Datetime.now() + relativedelta(hours=-1),
             'deactivate_on': fields.Datetime.now() + relativedelta(minutes=+30)})

        # check generated commands
        self._check_cmd_add_card_and_remove(ctrl)
        self._check_no_cmd(ctrl)

        # make ag inactive for cron activation
        test_partner_ag_rel.write({
            'activate_on': fields.Datetime.now() + relativedelta(minutes=-3),
            'expiration': fields.Datetime.now() + relativedelta(minutes=-1),
        })

        # check generated commands
        self._check_cmd_delete_card_and_remove(ctrl)
        self._check_no_cmd(ctrl)

        # make ag active with 1 visit to check stop after visit counting
        test_partner_ag_rel.write({
            'activate_on': fields.Datetime.now() + relativedelta(minutes=-3),
            'expiration': fields.Datetime.now() + relativedelta(minutes=+3),
        })
        self._check_cmd_add_card_and_remove(ctrl)
        self._check_no_cmd(ctrl)

        test_partner_ag_rel.write({
            'visits_counter': 1,
        })
        # check generated commands
        self._check_cmd_delete_card_and_remove(ctrl)
        self._check_no_cmd(ctrl)

        # Cleanup all local data
        test_ag_id.unlink()
        # self._clear_ctrl_cmd(ctrl)

        # call cron

        # check for new commands
    def _test_global_APB(self):
        self._change_mode(self.c_110, 1)  # Change mode to 1 door with two readers
        self.assertTrue(self.c_110.mode == 1)
        self._change_mode(self.c_115, 1)  # Change mode to 1 door with two readers
        self.assertTrue(self.c_115.mode == 1)
        self._change_mode(self.c_130, 2)  # Change mode to 2 door with two readers
        self.assertTrue(self.c_130.mode == 2)

        self.c_110.door_ids.apb_mode = True
        response = self._hearbeat(self.test_webstack_10_3_id)
        response = self._send_cmd_response(response)
        self.c_115.door_ids.apb_mode = True
        response = self._hearbeat(self.test_webstack_10_3_id)
        response = self._send_cmd_response(response)
        self.c_130.door_ids.apb_mode = True
        response = self._hearbeat(self.test_webstack_10_3_id)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)
        self.c_turnstile.door_ids.apb_mode = True
        response = self._hearbeat(self.test_webstack_10_3_id)
        response = self._send_cmd_response(response)
        # Make zone for Global APB
        test_apb_zone = self.env['hr.rfid.zone'].create({
            'name': 'Test APB Zone',
            'company_id': self.test_company_id,
            'anti_pass_back': True,
            'door_ids': [
                (4, self.c_110.door_ids[0].id, 0),
                (4, self.c_115.door_ids[0].id, 0),
                (4, self.c_130.door_ids[0].id, 0),
                (4, self.c_130.door_ids[1].id, 0),
                (4, self.c_turnstile.door_ids[0].id, 0),
            ]
        })

        # Make event with card on entrance on first door
        response = self._make_event(self.c_turnstile, reader=1, event_code=3)
        # Check if new command generated for APB flag change and clear it
        response = self._send_cmd_response(response, '0000000000')
        response = self._send_cmd_response(response, '0000000000')
        response = self._send_cmd_response(response, '0000000000')
        self.assertEqual(response, {})
        pass

    # Create controllers
    def _add_Turnstile(self, module=234567, key='0000', id=None):
        id = id or self._get_id_num()
        c_turnstile = self.env['hr.rfid.ctrl'].create({
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
        response = self._send_cmd_response(response, '00006E010752079200000000000000000000000000000000')
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
        response = self._send_cmd_response(response, '00006E010752079200000000000000000000000000000000')
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

        response = self._send_cmd_response(response, self._get_F0_response(self.c_Relay))
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
        response = self._send_cmd_response(response, '000001000335000000000000000000000000050204000000')
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
        response = self._send_cmd_response(response, '000001000335000000000000000000000000050204000000')
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
        response = self._send_cmd_response(response, '000000000771000002060422000000000000000000000000')
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
        response = self._send_cmd_response(response, '000000000686000000000000000000000000010802000000')
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
        response = self._send_cmd_response(response, '0202000207080704040000050000040001050208000200000102070004000604')
        self._check_added_controller(self.c_temperature)
        self.assertTrue(response['cmd']['c'] == 'D7', '(%s)' % self.c_temperature.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_temperature.name)
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC', '(%s)' % self.c_temperature.name)
        response = self._send_cmd_response(response)
        response = self._process_io_table(response, self.c_temperature, module, key)
        self.assertTrue(response['cmd']['c'] == 'B3', '(%s)' % self.c_temperature.name)
        response = self._send_cmd_response(response, '000000000875000001840390000000000000000802000000')
        self.assertTrue(response['cmd']['c'] == 'F2', '(%s)' % self.c_temperature.name)
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
        # {'convertor': 428030,
        #  'event': {'bos': 1, 'card': '0000000000', 'cmd': 'FA', 'date': '11.07.22', 'day': 1, 'dt': '01900000',
        #            'err': 0, 'event_n': 52, 'id': 29, 'reader': 2, 'time': '11:41:39', 'tos': 282},
        #  'key': '1764'}
        # {"c": "FA", "d": "0000000002 0000000001 34363922050411220000000002000000040002000000", "e": 0, "id": 29}
        self._send_cmd_response(response, '0000')  # TODO ???!?? 0000 do not know what is it
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
