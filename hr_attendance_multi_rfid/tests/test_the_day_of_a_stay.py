"""A stay is judged by the day the person lived it.

Business statement (owner, 20.10.2026): every daily figure of the set reads
the day in the person's own zone - the same zone core cuts its overtime days
in, and the only zone Odoo 20 knows. Two days a year the clocks change, and
that day is 23 or 25 hours long where the person works; its schedule must not
borrow an hour of the next one.
"""

from datetime import date

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from .common import in_sofia


@tagged("post_install", "-at_install", "rfid_attendance_figures")
class TestTheDayOfAStay(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A night shift that starts on Monday at midnight - and nothing on
        # Sunday, so Sunday is worth no hours at all.
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "Monday night (test)",
                "tz": "Europe/Sofia",
                "hours_per_day": 6.0,
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Monday night",
                            "dayofweek": "0",
                            "hour_from": 0,
                            "hour_to": 6,
                            "day_period": "morning",
                        },
                    )
                ],
            }
        )
        cls.person = cls.env["hr.employee"].create(
            {
                "name": "Night Guard (test)",
                "resource_calendar_id": cls.calendar.id,
                "tz": "Europe/Sofia",
            }
        )

    def test_the_sunday_the_clocks_go_forward_borrows_nothing_from_monday(self):
        """A Sunday call-out on 29 March is judged by Sunday, which is free.

        That Sunday is 23 hours long in Sofia. Taken as 24 from its midnight,
        it reached 01:00 on Monday and lent the person an hour of Monday's
        night shift - a stay on a free day would then be judged against a
        working day that never was.
        """
        stay = self.env["hr.attendance"].create(
            {
                "employee_id": self.person.id,
                "check_in": in_sofia(date(2026, 3, 29), 10),
                "check_out": in_sofia(date(2026, 3, 29), 12),
            }
        )
        self.assertEqual(
            stay._scheduled_day(),
            (0.0, 0.0),
            "Sunday is not a working day for this person",
        )

    def test_a_stay_after_midnight_is_judged_by_that_mornings_schedule(self):
        """The Monday night shift is Monday's, though UTC still says Sunday."""
        stay = self.env["hr.attendance"].create(
            {
                "employee_id": self.person.id,
                "check_in": in_sofia(date(2026, 3, 2), 0, 5),
                "check_out": in_sofia(date(2026, 3, 2), 6),
            }
        )
        hours, _span = stay._scheduled_day()
        self.assertAlmostEqual(
            hours, 6.0, places=4, msg="the stay is judged by Monday's six hours"
        )

    def test_a_chosen_day_lasts_as_long_as_it_did_where_the_person_works(self):
        """25 October 2026 is 25 hours long in Sofia, 29 March 23 hours."""
        for day, hours in ((date(2026, 10, 25), 25), (date(2026, 3, 29), 23)):
            start, end = self.person._local_days_window(day, day)
            self.assertEqual(
                start, in_sofia(day, 0), "the day begins at midnight where they work"
            )
            self.assertEqual((end - start).total_seconds() / 3600, hours)
        self.assertEqual(
            self.person._local_day(in_sofia(date(2026, 3, 2), 0, 5)),
            date(2026, 3, 2),
            "five past midnight in Sofia is that morning's date",
        )
