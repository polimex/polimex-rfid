# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""A customer who already has a card buys a service at the till.

The till stretches the card's own period so that it covers the service. A
card entered with no "Deactivate on" is a card that does not expire; until
16.11.2026 the till stopped with an error for such a customer instead of
making the sale.
"""

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.hr_rfid.tests.hardware import one_door


@tagged("post_install", "-at_install", "rfid_service_lifecycle", "rfid_service_till")
class TestACustomerWithACardBuysAService(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        door, _reader_in, _reader_out = one_door(cls.env, "Pool", 8861, 21)
        access_group = cls.env["hr.rfid.access.group"].create(
            {"name": "Pool visitors", "company_id": company.id}
        )
        access_group.add_doors(door)
        cls.service = cls.env["rfid.service"].create(
            {
                "name": "Monthly Pool Pass",
                "company_id": company.id,
                "service_type": "time",
                "fixed_time": False,
                "time_interval_number": 1,
                "time_interval_type": "months",
                "access_group_id": access_group.id,
            }
        )
        cls.customer = cls.env["res.partner"].create(
            {
                "name": "A Regular",
                "phone": "0700 10 200",
                "email": "regular@example.com",
            }
        )
        cls.card = cls.env["hr.rfid.card"].create(
            {
                "number": "6677889900",
                "contact_id": cls.customer.id,
                "company_id": company.id,
            }
        )

    def _sold_at_the_till(self):
        """The sale as the cashier makes it: the form's values, then the button."""
        self.env["rfid.service.sale.wiz"].create(
            {
                "service_id": self.service.id,
                "partner_id": self.customer.id,
                "mobile": self.customer.phone,
                "email": self.customer.email,
                "card_number": self.card.number,
            }
        ).write_card()
        return self.env["rfid.service.sale"].search(
            [("partner_id", "=", self.customer.id)]
        )

    def test_a_card_that_never_expires_buys_a_service(self):
        """The customer's card has no end date: the sale is made and the card still has none."""
        self.assertFalse(self.card.deactivate_on, "the starting point")

        sale = self._sold_at_the_till()

        self.assertEqual(len(sale), 1)
        self.assertEqual(sale.state, "progress")
        self.assertEqual(sale.card_id, self.card)
        self.assertFalse(self.card.deactivate_on, "the card got an end date")

    def test_a_card_that_ends_sooner_is_valid_until_the_service_ends(self):
        """A card that would run out tomorrow lasts as long as the service bought on it."""
        self.card.deactivate_on = fields.Datetime.now() + timedelta(days=1)

        sale = self._sold_at_the_till()

        self.assertEqual(self.card.deactivate_on, sale.end_date)

    def test_a_card_that_ends_later_keeps_its_own_end(self):
        """NEGATIVE: a sale never shortens the customer's card."""
        in_three_months = (fields.Datetime.now() + timedelta(days=90)).replace(
            microsecond=0
        )
        self.card.deactivate_on = in_three_months

        self._sold_at_the_till()

        self.assertEqual(self.card.deactivate_on, in_three_months)
