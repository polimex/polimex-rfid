# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""A card is stored under the number it carries, or it is not stored.

The number field holds 10 characters. A longer number - a 7-byte card number
written as one decimal number, a number plate typed with many separators - was
cut to its first 10 characters without a word, and the card was saved under a
number that is not its own: it would never be found by its events, and the
number it was given may be another card's. The screen cannot do it (the field
takes 10 characters); an import and the API can.
"""

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.tests.common import RFIDAppCase

# A 7-byte card number (04 A1 B2 C3 D4 E5 F6) written as one decimal number.
SEVEN_BYTES_AS_A_NUMBER = str(int("04A1B2C3D4E5F6", 16))


@tagged("standard", "at_install", "rfid", "rfid_card")
class TestACardNumberIsKeptWhole(RFIDAppCase):
    def _card(self, number, **more):
        return self.env["hr.rfid.card"].create(
            dict(
                {
                    "number": number,
                    "employee_id": self.test_employee_id.id,
                    "company_id": self.test_company_id,
                },
                **more,
            )
        )

    def _plate(self, number):
        return self._card(
            number, card_type=self.env.ref("hr_rfid.hr_rfid_card_type_8").id
        )

    def test_a_number_that_does_not_fit_is_refused_not_cut(self):
        """A card number longer than a card holds is refused; no card is saved under its first 10 digits."""
        self.assertGreater(len(SEVEN_BYTES_AS_A_NUMBER), 10)

        with self.assertRaises(UserError):
            self._card(SEVEN_BYTES_AS_A_NUMBER)

        self.assertFalse(
            self.env["hr.rfid.card"].search(
                [("number", "=", SEVEN_BYTES_AS_A_NUMBER[:10])]
            ),
            "the card was saved under a number cut short",
        )

    def test_a_number_given_as_a_number_is_refused_too(self):
        """NEGATIVE: an import that hands the number over as a number, not as text, gets the same refusal."""
        with self.assertRaises(UserError):
            self._card(int(SEVEN_BYTES_AS_A_NUMBER))

    def test_changing_a_card_to_a_number_that_does_not_fit_is_refused(self):
        """The number of an existing card cannot be replaced by one cut short either; the card keeps its own."""
        card = self._card("0012345678")

        with self.assertRaises(UserError):
            card.write({"number": SEVEN_BYTES_AS_A_NUMBER})

        self.assertEqual(card.number, "0012345678")

    def test_a_number_that_fits_is_kept_as_before(self):
        """NEGATIVE: ten digits are stored as they are, and a shorter number gets its leading zeros."""
        self.assertEqual(self._card("5700548879").number, "5700548879")
        self.assertEqual(self._card("123").number, "0000000123")

    def test_a_plate_typed_with_many_separators_is_kept_whole(self):
        """A number plate typed with spaces and dashes is the plate, not what is left of its first 10 characters.

        "CB - 5803 - CM" has 14 characters. Cut to 10 before the separators
        were dropped, it was saved as CB5803 - somebody else's plate.
        """
        self.assertEqual(self._plate("CB - 5803 - CM").number, "CB5803CM")

    def test_a_plate_longer_than_a_card_number_is_refused(self):
        """NEGATIVE: a plate with more characters than a card number holds is refused with the number it was."""
        with self.assertRaises(ValidationError) as refused:
            self._plate("CB5803CM1234")

        self.assertIn("CB5803CM1234", str(refused.exception))
