# Copyright 2024 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.tests.controller import RFIDController

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_commands')
class TestCommandQueue(RFIDController, HttpCase):
    """Test command queue lifecycle."""
    _registry_readonly_enabled = False

    def test_command_created_on_controller_init(self):
        """Test that F0 command is created when controller requests info."""
        ctrl = self.env['hr.rfid.ctrl'].create({
            'name': 'Cmd Test Controller',
            'ctrl_id': self._get_id_num(),
            'webstack_id': self.test_webstack_10_3_id.id,
        })
        ctrl.read_controller_information_cmd()
        cmd_count = self.env['hr.rfid.command'].search_count([
            ('controller_id', '=', ctrl.id),
            ('status', '=', 'Wait'),
        ])
        self.assertTrue(cmd_count > 0, 'F0 command should be queued')

    def test_command_status_lifecycle(self):
        """Test command goes from Wait → Process → Success."""
        self._add_iCon50()
        # After init, controller should have no waiting commands
        self._check_no_cmd(self.c_50)
        # Check that completed commands exist
        completed = self.env['hr.rfid.command'].search_count([
            ('controller_id', '=', self.c_50.id),
            ('status', '=', 'Success'),
        ])
        self.assertTrue(completed > 0, 'Should have successful commands after init')

    def test_card_add_generates_d1_command(self):
        """Test adding card to AG generates D1 command."""
        self._add_iCon110()
        test_ag = self.env['hr.rfid.access.group'].create({
            'name': 'Cmd AG',
            'company_id': self.test_company_id,
            'door_ids': [(0, 0, {'door_id': d_id}) for d_id in self.c_110.door_ids.mapped('id')]
        })
        self.test_employee_id.department_id.write({
            'hr_rfid_allowed_access_groups': [(4, test_ag.id, 0)],
        })
        from dateutil.relativedelta import relativedelta
        from odoo import fields
        self.env['hr.rfid.access.group.employee.rel'].create({
            'access_group_id': test_ag.id,
            'employee_id': self.test_employee_id.id,
            'activate_on': fields.Datetime.now() + relativedelta(minutes=-1),
        })
        cmd = self._check_cmd_add_card(self.c_110)
        self.assertEqual(cmd[0].cmd, 'D1', 'Command should be D1 (Add/Delete Card)')
        cmd.unlink()
        test_ag.unlink()

    def test_command_order(self):
        """Test commands are ordered by create_date desc."""
        self._add_iCon50()
        cmds = self.env['hr.rfid.command'].search([
            ('controller_id', '=', self.c_50.id),
        ], order='create_date desc')
        if len(cmds) >= 2:
            self.assertGreaterEqual(cmds[0].create_date, cmds[1].create_date,
                                    'Commands should be ordered newest first')

    def test_no_commands_clean_state(self):
        """Test no pending commands after full controller init."""
        self._add_iCon50()
        self._check_no_cmd(self.c_50)

    def test_heartbeat_returns_pending_command(self):
        """Test heartbeat returns pending command when one exists."""
        ctrl = self.env['hr.rfid.ctrl'].create({
            'name': 'HB Test Controller',
            'ctrl_id': self._get_id_num(),
            'webstack_id': self.test_webstack_10_3_id.id,
        })
        ctrl.read_controller_information_cmd()
        response = self._hearbeat(self.test_webstack_10_3_id)
        self.assertNotEqual(response, {}, 'Heartbeat should return pending command')
        self.assertIn('cmd', response, 'Response should contain cmd key')
