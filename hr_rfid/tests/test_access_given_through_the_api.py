# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Access and cards given to a contact through the API.

res.partner.add_access_group and add_card_number are what an integration
calls (a reception desk, a booking system) to let a visitor in. Given a
second time for the same group or card they widen what the contact already
has. They wrote fields that do not exist and compared a date with nothing,
so the second call always failed.
"""

from datetime import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid", "rfid_access_group")
class TestAccessGivenThroughTheApi(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contact = cls.env["res.partner"].create({"name": "A Visitor"})
        cls.group = cls.env["hr.rfid.access.group"].create(
            {"name": "Visitors", "company_id": cls.env.company.id}
        )

    def _membership(self):
        return self.contact.hr_rfid_access_group_ids.filtered(
            lambda rel: rel.access_group_id == self.group
        )

    def test_a_second_grant_widens_the_period_and_adds_the_visits(self):
        self.contact.add_access_group(
            self.group.id,
            activate_on=datetime(2026, 12, 2, 8),
            expire_on=datetime(2026, 12, 5, 18),
            visits=3,
        )
        self.contact.add_access_group(
            self.group.id,
            activate_on=datetime(2026, 12, 1, 8),
            expire_on=datetime(2026, 12, 10, 18),
            visits=2,
        )

        rel = self._membership()
        self.assertEqual(len(rel), 1)
        self.assertEqual(rel.activate_on, datetime(2026, 12, 1, 8))
        self.assertEqual(rel.expiration, datetime(2026, 12, 10, 18))
        self.assertTrue(rel.visits_counting)
        self.assertEqual(rel.permitted_visits, 5)

    def test_a_second_grant_without_dates_keeps_them(self):
        self.contact.add_access_group(
            self.group.id,
            activate_on=datetime(2026, 12, 2, 8),
            expire_on=datetime(2026, 12, 5, 18),
        )
        self.contact.add_access_group(self.group.id)

        rel = self._membership()
        self.assertEqual(rel.activate_on, datetime(2026, 12, 2, 8))
        self.assertEqual(rel.expiration, datetime(2026, 12, 5, 18))

    def test_a_card_given_twice_widens_its_period(self):
        self.contact.add_card_number(
            "0012340099",
            activate_on=datetime(2026, 12, 2, 8),
            expire_on=datetime(2026, 12, 5, 18),
        )
        self.contact.add_card_number("0012340099", expire_on=datetime(2026, 12, 9, 18))

        card = self.contact.hr_rfid_card_ids
        self.assertEqual(len(card), 1)
        self.assertEqual(card.activate_on, datetime(2026, 12, 2, 8))
        self.assertEqual(card.deactivate_on, datetime(2026, 12, 9, 18))
