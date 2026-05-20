# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""
Regression tests for hr.rfid.card.barcode_number.

The portal QR-code, the foldable badge PDF, and the full-page ticket PDF
all read `card.barcode_number`. The reader/scanner that consumes that
QR decodes the printed hex back to the 5+5 decimal that the controller
firmware actually sends on every scan, and Odoo looks the card up by
`internal_number`. So the QR hex MUST be the hex of the card's
`internal_number` — not of whatever raw `number` the user typed in.

Prior to the fix, `_compute_barcode_number` fed `card.number` to
`w34_to_hex`. That worked for `card_input_type='w34'` (5+5 decimal input)
but mis-encoded `'w34s'` cards (10d single-decimal input) because
`w34_to_hex` always splits its argument as two 5-digit decimals.

Bug case: w34s card with number='2760500060'
  * internal_number (5+5 dec, what hardware sends) = '4212158204'
  * Hardware/programmed hex                       = 'A489E35C'
  * Buggy QR (w34_to_hex of raw number)           = '6BD5003C'   <- wrong
  * Fixed QR (w34_to_hex of internal_number)      = 'A489E35C'   <- right
"""
from odoo.tests.common import tagged
from .common import RFIDAppCase


@tagged('standard', 'at_install', 'rfid', 'rfid_card', 'rfid_barcode')
class TestBarcodeNumber(RFIDAppCase):

    def _make_card(self, number, card_input_type):
        return self.env['hr.rfid.card'].create({
            'number': number,
            'card_input_type': card_input_type,
            'card_reference': f'Test {card_input_type} {number}',
            'contact_id': self.test_partner.id,
            'company_id': self.test_company_id,
        })

    def test_w34_card_barcode_matches_hardware_hex(self):
        """Card in 5+5 dec format: barcode_number == hex of the same hex pair."""
        card = self._make_card('0012345678', 'w34')
        # number is already 5+5, so internal_number == number.
        self.assertEqual(card.internal_number, '0012345678')
        # 00123 -> 0x007B, 45678 -> 0xB26E.
        self.assertEqual(card.barcode_number, '007BB26E')
        # Round-trip: hex_to_w34 of the QR must equal what hardware sends.
        self.assertEqual(
            self.env['hr.rfid.card'].hex_to_w34(card.barcode_number),
            card.internal_number,
        )

    def test_w34s_card_barcode_matches_hardware_hex(self):
        """Regression: w34s (10d single decimal) card encodes correctly.

        Hardware programs the card at hex(int(number)); reader sends
        internal_number on scan. The QR must encode the same hex as
        the hardware, not the wrong hex from splitting the user's
        10-digit decimal into 5+5.
        """
        # int('2760500060') = 0xA489E35C; split as 4-hex pairs:
        #   A489 -> 42121, E35C -> 58204 -> internal_number = '4212158204'.
        card = self._make_card('2760500060', 'w34s')
        self.assertEqual(card.internal_number, '4212158204')
        # The QR must carry the hardware hex, not the buggy raw-number split.
        self.assertEqual(card.barcode_number, 'A489E35C')
        self.assertNotEqual(
            card.barcode_number, '6BD5003C',
            "Regression: barcode_number must not be w34_to_hex(card.number) for w34s cards",
        )
        # Round-trip: hex_to_w34(barcode_number) must recover internal_number.
        self.assertEqual(
            self.env['hr.rfid.card'].hex_to_w34(card.barcode_number),
            card.internal_number,
        )

    def test_barcode_number_recomputes_when_input_type_changes(self):
        """Customer-reported flow: changing card_input_type must invalidate QR.

        @api.depends must include internal_number (which itself depends on
        number + card_input_type). Otherwise the QR keeps the old hex while
        the controller now expects a different internal_number — every
        scan fails with 'Could not find the card'.
        """
        card = self._make_card('0012345678', 'w34')
        qr_w34 = card.barcode_number
        self.assertEqual(qr_w34, '007BB26E')

        card.card_input_type = 'w34s'
        card.invalidate_recordset(['internal_number', 'barcode_number'])
        # Now internal_number recomputes from the same '0012345678' as if it
        # were a 10d decimal: int(12345678) = 0xBC614E -> 8-hex '00BC614E'
        # -> dec pair '00188','24910' -> internal_number '0018824910'.
        self.assertEqual(card.internal_number, '0018824910')
        # The QR must follow.
        self.assertEqual(card.barcode_number, '00BC614E')
        self.assertNotEqual(
            card.barcode_number, qr_w34,
            "barcode_number must update when card_input_type flips and "
            "internal_number changes",
        )

    def test_helpers_are_inverse_on_internal_number(self):
        """w34_to_hex and hex_to_w34 are inverses on the canonical 5+5 form.

        Each half maps to four hex digits (0..0xFFFF = 65535), so we
        sample inputs whose halves stay inside that range.
        """
        Card = self.env['hr.rfid.card']
        for w34 in ('0012345678', '4212158204', '0018824910', '6553565535'):
            self.assertEqual(
                Card.hex_to_w34(Card.w34_to_hex(w34)),
                w34,
                f"hex_to_w34(w34_to_hex({w34!r})) must be identity",
            )
