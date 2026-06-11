# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.hr_rfid.tests.controller import RFIDController
from odoo.tests.common import HttpCase, tagged


@tagged('rfid_vending', 'rfid_vending_key_auth')
class TestVendingKeyAuth(RFIDController, HttpCase):
    """Security regression: the vending /hr/rfid/event override must validate
    the module key (constant-time) before processing any event.

    Before the fix the override short-circuited the base handler's key check,
    so a forged event for a known serial could drive a vending grant (DB2)
    without ever presenting the module key.
    """

    _registry_readonly_enabled = False

    def setUp(self):
        super().setUp()
        self._add_Vending()
        # The add flow adopts key '0000' on the webstack via TOFU.
        self.assertEqual(self.c_vending.webstack_id.key, '0000')

    def _ev64_with_key(self, card_number, key):
        """Send an ev64 (Cloud Card Request) signed with an explicit key."""
        return self._send_cmd({
            "convertor": self.c_vending.webstack_id.serial,
            "event": {
                "bos": 1, "tos": 1,
                "card": card_number,
                "cmd": "FA",
                "date": self.test_date_10_3,
                "day": self.test_dow_10_3,
                "dt": "00000000000000",
                "time": self.test_time_10_3,
                "err": 0, "event_n": 64,
                "id": self.c_vending.ctrl_id, "reader": 1,
            },
            "key": key,
        })

    def _vending_event_count(self):
        return self.env['hr.rfid.vending.event'].sudo().search_count([
            ('controller_id', '=', self.c_vending.id)
        ])

    def _key_mismatch_sys_events(self):
        return self.env['hr.rfid.event.system'].sudo().search_count([
            ('webstack_id', '=', self.c_vending.webstack_id.id),
            ('error_description', 'ilike', 'key and key in json did not match'),
        ])

    def test_wrong_key_rejected(self):
        """A forged event with the wrong key is rejected: no vending event, no
        grant command, and a 'key did not match' system event is recorded."""
        ev_before = self._vending_event_count()
        mismatch_before = self._key_mismatch_sys_events()

        response = self._ev64_with_key(self.test_card_employee.number, 'DEAD')

        self.assertEqual(response, {}, 'Wrong key must be rejected (empty response)')
        self.assertEqual(self._vending_event_count(), ev_before,
                         'No vending event may be created for an unauthenticated event')
        self.assertEqual(self._key_mismatch_sys_events(), mismatch_before + 1,
                         'A key-mismatch system event must be logged')

    def test_correct_key_reaches_vending(self):
        """The same event WITH the correct key passes authentication and reaches
        the vending logic — proving the only thing the rejection above gated on
        is the key. A zero-balance ev64 is denied but still records a vending
        event for audit, which is the observable proof it got past auth."""
        ev_before = self._vending_event_count()

        self._ev64_with_key(self.test_card_employee.number, '0000')

        self.assertEqual(self._vending_event_count(), ev_before + 1,
                         'Correct key must let the event reach the vending logic')

    def test_no_convertor_delegates_without_crash(self):
        """A POST with no 'convertor' (raw/barcode device) must not crash the
        vending override — it delegates to the base raw-data handler."""
        ev_before = self._vending_event_count()
        response = self._send_cmd({'something': 'else'})
        self.assertIsInstance(response, dict, 'Delegation must return cleanly, not crash')
        self.assertEqual(self._vending_event_count(), ev_before,
                         'A non-convertor POST must not create a vending event')
