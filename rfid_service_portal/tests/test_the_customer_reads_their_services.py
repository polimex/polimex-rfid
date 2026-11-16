# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""What a customer reads under "RFID Services" in the portal.

The page is the customer's: the hours are the ones on their own clock and the
state of a service is a word they understand. Until 16.11.2026 the page
printed the hours as the server keeps them and the state as the system's own
code for it.
"""

import re
from datetime import timedelta

import pytz

from odoo import fields
from odoo.tests import HttpCase, new_test_user, tagged

CUSTOMERS_TIMEZONE = "Europe/Sofia"


@tagged("post_install", "-at_install", "rfid_service_portal")
class TestTheCustomerReadsTheirServices(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        access_group = cls.env["hr.rfid.access.group"].create(
            {"name": "Pool visitors", "company_id": company.id}
        )
        cls.service = cls.env["rfid.service"].create(
            {
                "name": "Monthly Pool Pass",
                "company_id": company.id,
                "service_type": "time",
                "time_interval_number": 1,
                "time_interval_type": "months",
                "access_group_id": access_group.id,
            }
        )
        cls.customer = new_test_user(
            cls.env,
            login="pool_customer",
            password="pool_customer",
            groups="base.group_portal",
            tz=CUSTOMERS_TIMEZONE,
            lang="en_US",
        )
        # Seven minutes past a whole hour, two to three hours ago: an hour the
        # customer's clock and the server's can never show alike.
        cls.started = (fields.Datetime.now() - timedelta(hours=2)).replace(
            minute=7, second=0, microsecond=0
        )
        cls.theirs = cls._sell(cls.customer.partner_id, "POOL-0001")
        somebody = cls.env["res.partner"].create({"name": "Somebody Else"})
        cls._sell(somebody, "POOL-0002")

    @classmethod
    def _sell(cls, partner, reference):
        period = {
            "start": cls.started,
            "end": cls.started + timedelta(days=30),
        }
        access = cls.env["hr.rfid.access.group.contact.rel"].create(
            {
                "access_group_id": cls.service.access_group_id.id,
                "contact_id": partner.id,
                "activate_on": period["start"],
                "expiration": period["end"],
            }
        )
        return cls.env["rfid.service.sale"].create(
            {
                "name": reference,
                "service_id": cls.service.id,
                "company_id": cls.service.company_id.id,
                "partner_id": partner.id,
                "start_date": period["start"],
                "end_date": period["end"],
                "access_group_contact_rel": access.id,
            }
        )

    def _the_page(self):
        self.authenticate("pool_customer", "pool_customer")
        page = self.url_open("/my/rfid_services")
        self.assertEqual(page.status_code, 200)
        return page.text

    def test_the_hours_are_the_customers_own(self):
        """The service starts and ends at the hours the customer's clock shows, not the server's.

        Read off the row itself, whichever way the customer's language writes
        an hour (14:07 or 02:07 PM): the hour next to the seven minutes.
        """
        their_zone = pytz.timezone(CUSTOMERS_TIMEZONE)
        on_their_clock = {
            pytz.utc.localize(moment).astimezone(their_zone).hour % 12
            for moment in (self.theirs.start_date, self.theirs.end_date)
        }

        page = self._the_page()

        row = re.search(r"POOL-0001.*?</tr>", page, re.DOTALL)
        self.assertTrue(row, "the customer's service is not listed")
        shown = {int(hour) % 12 for hour in re.findall(r"(\d{1,2}):07", row.group(0))}
        self.assertEqual(shown, on_their_clock)
        self.assertNotIn(self.started.hour % 12, shown, "the server's hour")
        self.assertNotIn(":07:00", row.group(0), "seconds nobody needs")

    def test_the_state_is_a_word_not_a_code(self):
        """A running service reads "Active"; the system's code for it is not shown."""
        self.assertEqual(self.theirs.state, "progress", "the starting point")

        page = self._the_page()

        self.assertTrue(re.search(r">\s*Active\s*<", page), "the name of the state")
        self.assertFalse(re.search(r">\s*progress\s*<", page), "the code is shown")

    def test_somebody_elses_service_is_not_listed(self):
        """NEGATIVE: the page lists the customer's own services and nobody else's."""
        page = self._the_page()

        self.assertIn("POOL-0001", page)
        self.assertNotIn("POOL-0002", page)
