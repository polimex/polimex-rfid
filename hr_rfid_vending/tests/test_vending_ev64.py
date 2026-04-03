# Copyright 2026 Polimex Holding Ltd..
# License APL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.hr_rfid.tests.controller import RFIDController
from odoo.tests.common import HttpCase, tagged


@tagged('rfid_vending', 'rfid_vending_ev64')
class TestVendingEv64(RFIDController, HttpCase):
    """Test all ev64 (Cloud Card Request) paths from hardware to Odoo response."""

    _registry_readonly_enabled = False

    def setUp(self):
        super().setUp()
        self._add_Vending()

    def _ev64(self, card_number, ctrl_id=None, bos=1, tos=1):
        """Send ev64 (Cloud Card Request) and return parsed response."""
        ctrl_id = ctrl_id or self.c_vending
        return self._send_cmd({
            "convertor": ctrl_id.webstack_id.serial,
            "event": {
                "bos": bos, "tos": tos,
                "card": card_number,
                "cmd": "FA",
                "date": self.test_date_10_3,
                "day": self.test_dow_10_3,
                "dt": "00000000000000",
                "time": self.test_time_10_3,
                "err": 0, "event_n": 64,
                "id": ctrl_id.ctrl_id, "reader": 1,
            },
            "key": ctrl_id.webstack_id.key
        })

    def _ev49(self, card_number, ctrl_id=None):
        """Send ev49 (VEND FAIL) event."""
        ctrl_id = ctrl_id or self.c_vending
        return self._send_cmd({
            "convertor": ctrl_id.webstack_id.serial,
            "event": {
                "bos": 1, "tos": 1,
                "card": card_number,
                "cmd": "FA",
                "date": self.test_date_10_3,
                "day": self.test_dow_10_3,
                "dt": "00000000000000",
                "time": self.test_time_10_3,
                "err": 0, "event_n": 49,
                "id": ctrl_id.ctrl_id, "reader": 1,
            },
            "key": ctrl_id.webstack_id.key
        }, system_event=True)

    def _vending_event_count(self):
        return self.env['hr.rfid.vending.event'].sudo().search_count([
            ('controller_id', '=', self.c_vending.id)
        ])

    # ---- ev64 deny paths ----

    def test_ev64_card_not_found(self):
        """Card unknown to system -> deny (empty response), no vending event."""
        count_before = self._vending_event_count()
        response = self._ev64('9999999999')
        self.assertEqual(response, {}, 'Unknown card should get empty response (deny)')
        self.assertEqual(self._vending_event_count(), count_before,
                         'No vending event should be created for unknown card')

    def test_ev64_card_inactive(self):
        """Inactive card -> deny, no vending event."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.15)
        self.test_card_employee.active = False
        count_before = self._vending_event_count()
        response = self._ev64(self.test_card_employee.number)
        self.assertEqual(response, {}, 'Inactive card should get empty response (deny)')
        self.assertEqual(self._vending_event_count(), count_before)

    def test_ev64_employee_not_checked_in(self):
        """Employee with attendance check enabled but not checked in -> deny."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.15)
        self.test_employee_id.hr_rfid_vending_in_attendance = True
        count_before = self._vending_event_count()
        response = self._ev64(self.test_card_employee.number)
        self.assertEqual(response, {}, 'Employee not checked in should get deny')
        self.assertEqual(self._vending_event_count(), count_before)

    def test_ev64_zero_balance(self):
        """Employee with zero balance -> deny, vending event created."""
        self.assertEqual(self.test_employee_id.hr_rfid_vending_balance, 0)
        count_before = self._vending_event_count()
        response = self._ev64(self.test_card_employee.number)
        self.assertEqual(response, {}, 'Zero balance should get deny')
        self.assertEqual(self._vending_event_count(), count_before + 1,
                         'Vending event should be created even on deny (for audit)')

    # ---- ev64 grant path ----

    def test_ev64_grant_with_balance(self):
        """Employee with balance -> grant (DB2 command with balance)."""
        # io_table with scale_factor=5 at position (8*2)*(0x14-1)+6*2 = 316
        # Using known good io_table from test_vending_functionality
        io = '000400030002000100080007000600050F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F000000000000000F0000000000000005'
        self.c_vending.with_context(from_controller=True).write({'io_table': io})
        self.c_vending.invalidate_recordset()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.15)
        count_before = self._vending_event_count()
        response = self._ev64(self.test_card_employee.number)
        self.assertIn('cmd', response, 'Should return DB2 command for grant')
        self.assertEqual(response['cmd']['c'], 'DB', 'Grant command should be DB')
        self.assertTrue(response['cmd']['d'].startswith('4000'), 'DB2 data should start with 4000')
        self.assertEqual(self._vending_event_count(), count_before + 1,
                         'Vending event should be created on grant')
        # Complete the DB2 response
        response = self._send_cmd_response(response, '0000')
        self.assertEqual(response, {})

    # ---- ev49 VEND FAIL ----

    def test_ev49_vend_fail_creates_system_event(self):
        """VEND FAIL (ev49) -> creates system event."""
        sys_count = self.env['hr.rfid.event.system'].search_count([
            ('webstack_id', '=', self.c_vending.webstack_id.id)
        ])
        self._ev49(self.test_card_employee.number)
        new_sys_count = self.env['hr.rfid.event.system'].search_count([
            ('webstack_id', '=', self.c_vending.webstack_id.id)
        ])
        self.assertGreater(new_sys_count, sys_count, 'VEND FAIL should create system event')

    # ---- Init sequence ----

    def test_vending_init_skips_ff(self):
        """Vending controller init sequence should NOT include FF command."""
        cmds = self.env['hr.rfid.command'].search([
            ('controller_id', '=', self.c_vending.id),
        ])
        ff_cmds = cmds.filtered(lambda c: c.cmd == 'FF')
        self.assertFalse(ff_cmds, 'FF command should not be sent to vending controllers')
