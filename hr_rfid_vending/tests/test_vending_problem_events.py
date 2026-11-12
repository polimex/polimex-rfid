"""What the operator reads when a vending machine reports a problem.

Before this, events 48 and 49 both landed as "the vending machine reported an
error (data ...)" with the raw bytes: a card holder whose credit simply went
back because they chose nothing read like a breakdown, and a real breakdown did
not say which one. The meanings come from the protocol team's reading of the
three firmwares (protocol change D48, 12.11.2026): event 49 returns the credit
(product 0 = nothing chosen), event 48 carries an error code whose meaning
depends on the firmware.
"""

from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.tests.controller import RFIDController

from .vending_common import VendingFlowMixin, fc, take_everyone_off_auto_refill


def vending_part(product=0, code=0):
    """The 14 hex digits of an FA vending event: PIN, product, price, credit."""
    return "0000%02X%02X000000" % (product, code)


@tagged("rfid_vending", "rfid_vending_problems", "post_install", "-at_install")
class TestVendingProblemsInWords(VendingFlowMixin, RFIDController, HttpCase):
    _registry_readonly_enabled = False

    def _problem(self, hw, event_n, product=0, code=0):
        self._add_Vending(hw=hw)
        self._vending_event(event_n, dt=vending_part(product, code), system_event=True)
        events = self._system_events(event_action=str(event_n))
        self.assertEqual(len(events), 1)
        return events.error_description

    def test_a_credit_returned_with_nothing_chosen_is_not_a_breakdown(self):
        """49 with product 0: the credit went back, nothing was chosen."""
        text = self._problem(16, 49, product=0)
        self.assertIn("nothing was chosen", text)
        self.assertNotIn("error", text.lower())

    def test_an_item_that_did_not_come_out_is_named(self):
        """49 with product 7: item 7 did not come out, the credit went back."""
        self.assertIn("Item 7 did not come out", self._problem(20, 49, product=7))

    def test_a_machine_that_does_not_answer_says_so(self):
        """48 code 0 on the Executive (16): the machine does not answer."""
        self.assertIn("does not answer", self._problem(16, 48, code=0))

    def test_an_mdb_session_closed_by_timeout_points_at_the_machine(self):
        """48 code 3 on MDB (21): the session closed after 30 seconds."""
        self.assertIn("after 30 seconds", self._problem(21, 48, code=3))

    def test_a_code_the_firmware_does_not_have_is_shown_as_it_came(self):
        """NEGATIVE: code 1 exists on 16 only; on 20 it is not given a meaning."""
        text = self._problem(20, 48, code=1)
        self.assertIn("error 1", text)
        self.assertNotIn("is back", text)

    def test_a_returned_credit_moves_no_money(self):
        """NEGATIVE: the words changed, the balance does not."""
        take_everyone_off_auto_refill(self.env)
        self._add_Vending(hw=16)
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)

        self._vending_event(49, dt=vending_part(0), system_event=True)

        self.assertEqual(self._vending_event_count(), 0)
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.50))
