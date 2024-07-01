# Copyright 2022 Polimex Holding Ltd..
# License APL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_rfid.tests.controller import RFIDController
from odoo.tests.common import HttpCase, tagged
from odoo import fields

import logging

_logger = logging.getLogger(__name__)


# @tagged('post_install', '-at_install', 'migration')
@tagged('standard', 'at_install', 'migration')
class RFIDTests(RFIDController, HttpCase):
    def setUp(self):
        super(RFIDTests, self).setUp()

    def test_functionality(self):
        _logger.info('Start tests for iCON50 ')
        self._add_iCon50()
        self._test_R_event(self.c_50)
        self._test_add_remove_card_partner(self.c_50)
        self._test_add_remove_card_employee(self.c_50)
        self._test_Duress(self.c_50)
        self._test_inputs(self.c_50)
        self._ev64(self.c_50)
        self._check_no_commands()

        _logger.info('Start tests for iCON110 ')
        self._add_iCon110()
        self._test_R1R2(self.c_110)
        self._test_add_remove_card_partner(self.c_110)
        self._test_add_remove_card_employee(self.c_110)
        self._test_Duress(self.c_110)
        self._test_inputs(self.c_110)
        self._ev64(self.c_110)
        self._check_no_commands()

        _logger.info('Start tests for iCON115 ')
        self._add_iCon115()
        self._test_R1R2(self.c_115)
        self._test_add_remove_card_partner(self.c_115)
        self._test_add_remove_card_employee(self.c_115)
        self._ev64(self.c_115)
        self._check_no_commands()

        _logger.info('Start tests for Relay Controller ')
        self._add_RelayController()
        self._test_R1R2(self.c_Relay)
        self._test_add_remove_card_partner(self.c_Relay)
        self._test_add_remove_card_employee(self.c_Relay)
        # self._ev64(self.c_Relay) # TODO Check details
        self._check_no_commands()

        _logger.info('Start tests for iCON130 ')
        self._add_iCon130()
        self._test_R1R2R3R4(self.c_130)
        self._test_add_remove_card_partner(self.c_130)
        self._test_add_remove_card_employee(self.c_130)
        self._ev64(self.c_130)
        self._check_no_commands()

        # _logger.info('Start tests for iCON180 ')
        # self._add_iCon180()

        # Check for not processed responses
        # response = self._hearbeat(self.test_webstack_10_3_id)
        # self.assertEqual(response, {})

        _logger.info('Start tests for Turnstile ')
        self._add_Turnstile()
        self._test_R1R2(self.c_turnstile)
        response = self._make_event(self.c_turnstile, reader=65, event_code=3)
        self.assertEqual(response, {}, '(%s)' % self.c_turnstile.name)
        response = self._make_event(self.c_turnstile, reader=65, event_code=3)
        self.assertEqual(response, {}, '(%s)' % self.c_turnstile.name)
        self._check_no_commands()

        _logger.info('Start tests for Temperature Controller')
        self._add_Temperature()
        self._check_no_commands()

        _logger.info('Start tests for Vending Controller ')
        self._add_Vending()
        self._check_no_commands()

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

        add_door_to_ag1_wiz = self.env['hr.rfid.access.group.wizard'].with_context(
            {'active_ids': [self.test_ag_partner_1.id]}).create([{
            'door_ids': [
                (4, self.c_110.door_ids[0].id, 0),
                (4, self.c_115.door_ids[0].id, 0),
                (4, self.c_turnstile.door_ids[0].id, 0),
                (4, self.c_130.door_ids[0].id, 0),
                (4, self.c_130.door_ids[1].id, 0),
            ]
        }])
        add_door_to_ag1_wiz.add_doors()
        add_door_to_ag1_wiz.unlink()
        self._check_cmd_add_card_and_remove(self.c_110, 1, 3)
        self._check_cmd_add_card_and_remove(self.c_115, 1, 3)
        self._check_cmd_add_card_and_remove(self.c_130, 1, 15)
        self._check_cmd_add_card_and_remove(self.c_turnstile, 1, 3)

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

        # self.c_110.door_ids.apb_mode = True
        response = self._hearbeat(self.test_webstack_10_3_id)
        response = self._send_cmd_response(response)
        # self.c_115.door_ids.apb_mode = True
        # response = self._hearbeat(self.test_webstack_10_3_id)
        response = self._send_cmd_response(response)
        # self.c_130.door_ids.apb_mode = True
        # response = self._hearbeat(self.test_webstack_10_3_id)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)
        # self.c_turnstile.door_ids.apb_mode = True
        # response = self._hearbeat(self.test_webstack_10_3_id)
        response = self._send_cmd_response(response)

        self._check_cmd_add_card_and_remove(self.c_110, count=1, rights=0, mask=64)
        self._check_cmd_add_card_and_remove(self.c_115, count=1, rights=0, mask=64)
        self._check_cmd_add_card_and_remove(self.c_130, count=1, rights=0, mask=96)
        self._check_cmd_add_card_and_remove(self.c_turnstile, count=1, rights=0, mask=64)

        # Make event with card on entrance on first door
        response = self._make_event(self.c_turnstile, reader=1, event_code=63)
        # Check if new command generated for APB flag change and clear it
        self._check_cmd_add_card_and_remove(self.c_110, count=1, rights=64, mask=64)
        self._check_cmd_add_card_and_remove(self.c_115, count=1, rights=64, mask=64)
        self._check_cmd_add_card_and_remove(self.c_130, count=1, rights=96, mask=96)

        self._check_no_cmd(self.c_110)
        self._check_no_cmd(self.c_115)
        self._check_no_cmd(self.c_130)
        self._check_no_cmd(self.c_turnstile)

        self.assertTrue(test_apb_zone.employee_ids.ids == self.test_employee_id.ids)
        pass
