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
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from odoo.addons.hr_rfid.tests.hardware import one_door


class _AtTheTill(TransactionCase):
    """A pool with one door, a monthly pass, and a customer with a card."""

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


@tagged("post_install", "-at_install", "rfid_service_lifecycle", "rfid_service_till")
class TestACustomerWithACardBuysAService(_AtTheTill):
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


@tagged("post_install", "-at_install", "rfid_service_lifecycle", "rfid_service_till")
class TestTheCardIsTheOneOfTheServicesCompany(_AtTheTill):
    """A card number is unique within a company, not across companies.

    The owner, 16.11.2026 (open item 193): the till looked for the card in
    every company - with the same number in two companies the sale stopped
    with an error, and a number taken in another company showed the cashier
    the name of that company's customer.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_company = cls.env["res.company"].create({"name": "Another Tenant"})
        cls.their_customer = cls.env["res.partner"].create(
            {"name": "Their Customer", "company_id": cls.other_company.id}
        )
        cls.their_card = cls.env["hr.rfid.card"].create(
            {
                "number": "5544332211",
                "contact_id": cls.their_customer.id,
                "company_id": cls.other_company.id,
            }
        )

    def _sold_with_number(self, number):
        self.env["rfid.service.sale.wiz"].create(
            {
                "service_id": self.service.id,
                "partner_id": self.customer.id,
                "mobile": self.customer.phone,
                "email": self.customer.email,
                "card_number": number,
            }
        ).write_card()
        return self.env["rfid.service.sale"].search(
            [("partner_id", "=", self.customer.id)]
        )

    def test_a_number_another_company_uses_is_sold_here_on_a_card_of_this_company(self):
        """The same number in another company does not stop the sale: the customer gets a card of this company."""
        sale = self._sold_with_number("5544332211")

        self.assertEqual(sale.state, "progress")
        self.assertEqual(sale.card_id.number, "5544332211")
        self.assertEqual(sale.card_id.company_id, self.env.company)
        self.assertEqual(sale.card_id.contact_id, self.customer)

    def test_the_other_companys_card_is_left_as_it_was(self):
        """NEGATIVE: the other company's card keeps its holder and its period."""
        before = (
            self.their_card.contact_id,
            self.their_card.activate_on,
            self.their_card.deactivate_on,
        )

        self._sold_with_number("5544332211")

        after = (
            self.their_card.contact_id,
            self.their_card.activate_on,
            self.their_card.deactivate_on,
        )
        self.assertEqual(after, before)

    def test_a_number_taken_in_this_company_is_still_refused(self):
        """NEGATIVE: a card of this company held by somebody else is not handed to the customer."""
        somebody = self.env["res.partner"].create({"name": "Somebody Here"})
        self.env["hr.rfid.card"].create(
            {
                "number": "5544332299",
                "contact_id": somebody.id,
                "company_id": self.env.company.id,
            }
        )

        with self.assertRaisesRegex(UserError, "already used by partner Somebody Here"):
            self._sold_with_number("5544332299")

    def test_a_card_of_no_company_is_the_customers_card(self):
        """A card that belongs to no company is found by its number, as before."""
        loose = self.env["hr.rfid.card"].create(
            {
                "number": "5544332277",
                "contact_id": self.customer.id,
                "company_id": False,
            }
        )

        sale = self._sold_with_number("5544332277")

        self.assertEqual(sale.card_id, loose)


@tagged("post_install", "-at_install", "rfid_service_lifecycle", "rfid_service_till")
class TestTheVisitsLeftOnAService(_AtTheTill):
    """The sale shows how many more times the customer can come in.

    The owner, 16.11.2026 (open item 185): "Remaining Visits" showed the
    visits used - 0 on a new 10-visit card, 10 on one used up.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service.write({"service_type": "time_count", "visits": 10})

    def test_a_new_service_has_all_its_visits_left(self):
        sale = self._sold_at_the_till()

        self.assertEqual(sale.visits, 10)

    def test_every_entry_takes_one_visit(self):
        sale = self._sold_at_the_till()

        sale.access_group_contact_rel.visits_counter = 3

        self.assertEqual(sale.visits, 7)

    def test_a_service_used_up_has_none_left_and_is_over(self):
        sale = self._sold_at_the_till()

        sale.access_group_contact_rel.visits_counter = 10

        self.assertEqual(sale.visits, 0)
        self.assertEqual(sale.state, "finished")

    def test_the_cashier_reads_the_visits_left(self):
        """A cashier with the rights of the services only reads the sale and its visits left."""
        sale = self._sold_at_the_till()
        sale.access_group_contact_rel.visits_counter = 2
        cashier = new_test_user(
            self.env,
            login="pool_cashier",
            groups="base.group_user,rfid_service_base.group_card_user",
        )

        self.assertEqual(sale.with_user(cashier).visits, 8)

    def test_a_service_for_a_period_only_shows_no_visits(self):
        """NEGATIVE: a service with no limit on visits has nothing to count down."""
        self.service.write({"service_type": "time", "visits": 0})
        sale = self._sold_at_the_till()
        sale.access_group_contact_rel.visits_counter = 4

        self.assertEqual(sale.visits, 0)
