# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.hr_rfid.tests.controller import RFIDController
from odoo.tests.common import HttpCase, tagged

from .vending_common import VendingFlowMixin


@tagged('rfid_vending', 'rfid_vending_ev64')
class TestVendingEv64(VendingFlowMixin, RFIDController, HttpCase):
    """Test all ev64 (Cloud Card Request) paths from hardware to Odoo response."""

    _registry_readonly_enabled = False

    def setUp(self):
        super().setUp()
        self._add_Vending()

    def _assert_refusal_seen_by_the_operator(self, card_number):
        """A refused card leaves one system event saying which card, which
        machine event and when - not only a line in the server log."""
        refusals = self._system_events(event_action='64')
        self.assertEqual(len(refusals), 1)
        self.assertEqual(refusals.card_number, card_number)

    # ---- ev64 deny paths ----

    def test_ev64_card_not_found(self):
        """Card unknown to system -> deny (empty response), no vending event."""
        count_before = self._vending_event_count()
        response = self._ev64('9999999999')
        self.assertEqual(response, {}, 'Unknown card should get empty response (deny)')
        self.assertEqual(self._vending_event_count(), count_before,
                         'No vending event should be created for unknown card')
        self._assert_refusal_seen_by_the_operator('9999999999')

    def test_ev64_card_inactive(self):
        """Inactive card -> deny, no vending event."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.15)
        self.test_card_employee.active = False
        count_before = self._vending_event_count()
        response = self._ev64(self.test_card_employee.number)
        self.assertEqual(response, {}, 'Inactive card should get empty response (deny)')
        self.assertEqual(self._vending_event_count(), count_before)
        self._assert_refusal_seen_by_the_operator(self.test_card_employee.number)

    def test_ev64_employee_not_checked_in(self):
        """Employee with attendance check enabled but not checked in -> deny."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.15)
        self.test_employee_id.hr_rfid_vending_in_attendance = True
        count_before = self._vending_event_count()
        response = self._ev64(self.test_card_employee.number)
        self.assertEqual(response, {}, 'Employee not checked in should get deny')
        self.assertEqual(self._vending_event_count(), count_before)
        self._assert_refusal_seen_by_the_operator(self.test_card_employee.number)

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
        # 0.15 at scale factor 5 is 3 units.
        self._assert_balance_response(response, 3)
        self.assertEqual(self._vending_event_count(), count_before + 1,
                         'Vending event should be created on grant')
        self._check_no_commands()

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
