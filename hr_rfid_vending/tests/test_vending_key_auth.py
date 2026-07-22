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

    # A real, provisioned module key. '0000' is the unprovisioned sentinel
    # (owner decision 2026-07-19 + FW-Q26): a webstack still holding '0000'
    # adopts the first real key presented (G1 heal / TOFU provisioning), so a
    # forged-event rejection can only be proven on a device that already has a
    # real key. The security property under test is exactly that.
    PROVISIONED_KEY = 'AB12'  # 4-char module key (field size=4), non-'0000'

    def setUp(self):
        super().setUp()
        self._add_Vending()
        # Provision the module with a real key so this suite exercises a
        # PROVISIONED device (not the keyless/'0000' TOFU path).
        self.c_vending.webstack_id.key = self.PROVISIONED_KEY
        self.assertEqual(self.c_vending.webstack_id.key, self.PROVISIONED_KEY)

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

        self._ev64_with_key(self.test_card_employee.number, self.PROVISIONED_KEY)

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
