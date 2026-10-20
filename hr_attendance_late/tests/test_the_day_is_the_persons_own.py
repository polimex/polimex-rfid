"""The daily figures are filed under the person's own day.

Business statement (owner, 24.08.2026 and 20.10.2026): a stay belongs, whole,
to the day it started on - the day as the person lived it, where they work.
Sofia is two or three hours ahead of UTC, so every moment between 00:00 and
03:00 there carries the date of the day before in the database. Filed under
that stored date, a night stay lands on the evening before, is measured
against the wrong day's schedule, and the morning it really belongs to reads
as a no-show.
"""

import importlib.util
from datetime import date, timedelta

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import file_path

from odoo.addons.hr_attendance_multi_rfid.tests.common import in_sofia

MONDAY = date(2026, 2, 9)  # winter: Sofia is UTC+2
TUESDAY = date(2026, 2, 10)
WEDNESDAY = date(2026, 2, 11)
THURSDAY = date(2026, 2, 12)
FRIDAY = date(2026, 2, 13)
SUNDAY = MONDAY - timedelta(days=1)


def _upgrade_fill():
    """The 'came at / left at' backfill the upgrade to 19.0.2.3.2 runs."""
    spec = importlib.util.spec_from_file_location(
        "hr_attendance_late_mig_19_0_2_3_2",
        file_path("hr_attendance_late/migrations/19.0.2.3.2/post-migration.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.fill_first_in_last_out


@tagged("post_install", "-at_install", "hr_attendance_late")
class TestTheDayIsThePersonsOwn(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Sofia Day (test)"})
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "Sofia 08-17 (test)",
                "company_id": cls.company.id,
                "tz": "Europe/Sofia",
                "hours_per_day": 8.0,
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "%s %s" % (day, part),
                            "dayofweek": day,
                            "hour_from": start,
                            "hour_to": stop,
                            "day_period": part,
                        },
                    )
                    for day in "01234"
                    for start, stop, part in ((8, 12, "morning"), (13, 17, "afternoon"))
                ],
            }
        )
        cls.person = cls.env["hr.employee"].create(
            {
                "name": "Night Worker (test)",
                "company_id": cls.company.id,
                "resource_calendar_id": cls.calendar.id,
                "tz": "Europe/Sofia",
            }
        )

    def _day(self, day):
        return self.env["hr.attendance.extra"].search(
            [("employee_id", "=", self.person.id), ("for_date", "=", day)]
        )

    def test_a_stay_begun_after_midnight_is_that_mornings(self):
        """The guard who comes in at 00:30 on Tuesday works Tuesday.

        The HR officer opens Tuesday and finds the stay there - came at 00:30,
        one record behind the row, and the button on the row opens it. Monday
        holds no presence at all: nobody came on Monday, so Monday is the
        absence, not Tuesday.
        """
        stay = self.env["hr.attendance"].create(
            {
                "employee_id": self.person.id,
                "check_in": in_sofia(TUESDAY, 0, 30),
                "check_out": in_sofia(TUESDAY, 8, 30),
            }
        )

        # Refreshed by the record itself, as on a live installation.
        tuesday = self._day(TUESDAY)
        self.assertEqual(len(tuesday), 1, "Tuesday must have its daily row")
        self.assertAlmostEqual(
            tuesday.first_in,
            0.5,
            places=4,
            msg="Tuesday must show the arrival at 00:30 - the stay is Tuesday's",
        )
        self.assertEqual(
            int(tuesday.attendance_count or 0), 1, "and count the one stay behind it"
        )
        opened = self.env["hr.attendance"].search(
            tuesday.open_attendance_logs()["domain"]
        )
        self.assertEqual(opened, stay, "the row's button must open exactly that stay")

        # The operator recomputes both days.
        self.person.update_extra_attendance_data(
            MONDAY, TUESDAY, overwrite_existing=True
        )
        monday = self._day(MONDAY)
        self.assertTrue(monday, "a scheduled Monday with nobody in is an absence")
        self.assertAlmostEqual(
            monday.actual_work_time,
            0.0,
            places=4,
            msg="the night stay must not be Monday's worked time",
        )
        self.assertEqual(
            int(monday.attendance_count or 0), 0, "and Monday has no stay behind it"
        )
        self.assertAlmostEqual(self._day(TUESDAY).first_in, 0.5, places=4)

    def test_a_short_night_stay_updates_its_morning_by_itself(self):
        """Badged in at 00:30 and out at 01:30 on Tuesday: Tuesday shows it.

        Nobody recomputes anything - the record itself refreshes the day it
        belongs to. Both moments still carry Monday's date in UTC; refreshing
        by them would update Monday and leave Tuesday without the stay.
        """
        self.env["hr.attendance"].create(
            {
                "employee_id": self.person.id,
                "check_in": in_sofia(TUESDAY, 0, 30),
                "check_out": in_sofia(TUESDAY, 1, 30),
            }
        )
        tuesday = self._day(TUESDAY)
        self.assertEqual(len(tuesday), 1, "Tuesday must have its daily row")
        self.assertAlmostEqual(
            tuesday.first_in,
            0.5,
            places=4,
            msg="and it must show the stay that began at 00:30",
        )

    @freeze_time("2026-07-15 10:00:00")
    def test_a_winter_night_recomputed_in_summer_keeps_its_night(self):
        """Night work starts at 22:00 on the day it was done.

        Three hours on a February evening, 20:00 to 23:00: one of them is
        night work, paid with the night supplement. Recomputing that day in
        July must not move 22:00 by the summer hour and turn two of them
        into night work.
        """
        self.env["hr.attendance"].create(
            {
                "employee_id": self.person.id,
                "check_in": in_sofia(WEDNESDAY, 20, 0),
                "check_out": in_sofia(WEDNESDAY, 23, 0),
            }
        )
        self.person.update_extra_attendance_data(WEDNESDAY, overwrite_existing=True)
        day = self._day(WEDNESDAY)
        night = day.actual_work_time_night + day.overtime_night + day.extra_night
        self.assertAlmostEqual(
            night,
            1.0,
            places=4,
            msg="22:00-23:00 is the only night hour of that February evening",
        )

    def test_a_day_is_missed_only_once_it_is_over_for_the_person(self):
        """No badge on Thursday reads as an absence after Thursday's midnight.

        At 00:30 on Friday in Sofia - still Thursday in UTC - Thursday is
        over for the person and counts as missed. At 22:30 on Thursday it is
        not over yet, and nobody is marked absent for a day still going on.
        """
        with freeze_time(in_sofia(THURSDAY, 22, 30)):
            self.person.update_extra_attendance_data(THURSDAY, overwrite_existing=True)
            self.assertFalse(
                self._day(THURSDAY), "a day still going on is nobody's absence"
            )

        with freeze_time(in_sofia(FRIDAY, 0, 30)):
            self.person.update_extra_attendance_data(THURSDAY, overwrite_existing=True)
            missed = self._day(THURSDAY)
        self.assertTrue(missed, "once Thursday is over, it is a missed day")
        self.assertAlmostEqual(missed.theoretical_work_time, 8.0, places=4)
        self.assertAlmostEqual(missed.actual_work_time, 0.0, places=4)

    def test_the_persons_own_zone_decides_not_their_schedules(self):
        """In Sofia on a schedule kept in UTC: the day is Sofia's.

        Owner's decision (20.10.2026): the day is read in the person's own
        timezone, the one core cuts its overtime days in. A stay at 00:30 on
        Tuesday in Sofia is Tuesday's, although the schedule's zone - and the
        stored moment - still say Monday.
        """
        utc_hours = self.calendar.copy({"name": "Same hours, kept in UTC (test)", "tz": "UTC"})
        person = self.env["hr.employee"].create({
            "name": "Sofia on a UTC schedule (test)",
            "company_id": self.company.id,
            "resource_calendar_id": utc_hours.id,
        })
        person.tz = "Europe/Sofia"
        self.assertEqual((person.tz, person.resource_calendar_id.tz), ("Europe/Sofia", "UTC"),
                         "the fixture must build the shape under test: two zones")
        self.env["hr.attendance"].create({
            "employee_id": person.id,
            "check_in": in_sofia(TUESDAY, 0, 30),
            "check_out": in_sofia(TUESDAY, 1, 30),
        })
        person.update_extra_attendance_data(MONDAY, TUESDAY, overwrite_existing=True)
        days = self.env["hr.attendance.extra"].search([("employee_id", "=", person.id)])
        tuesday = days.filtered(lambda row: row.for_date == TUESDAY)
        monday = days.filtered(lambda row: row.for_date == MONDAY)
        self.assertAlmostEqual(tuesday.first_in, 0.5, places=4,
                               msg="the stay is Tuesday's, in Sofia")
        self.assertEqual(int(monday.attendance_count or 0), 0,
                         "and not Monday's, as the schedule's zone would have it")

    def test_a_night_after_a_free_sunday_is_monday_work(self):
        """00:30 on Monday after a free Sunday is Monday's ordinary work.

        Filed under its UTC date it became Sunday work - extra time on a rest
        day, paid at the rest-day rate - and Monday a missed day. Sunday,
        which nobody worked, has no row; Monday plans its eight hours and
        holds the stay.
        """
        self.env["hr.attendance"].create({
            "employee_id": self.person.id,
            "check_in": in_sofia(MONDAY, 0, 30),
            "check_out": in_sofia(MONDAY, 8, 30),
        })
        self.person.update_extra_attendance_data(SUNDAY, MONDAY, overwrite_existing=True)
        self.assertFalse(self._day(SUNDAY), "a free Sunday nobody worked has no row")
        monday = self._day(MONDAY)
        self.assertAlmostEqual(monday.theoretical_work_time, 8.0, places=4)
        self.assertAlmostEqual(monday.extra_time, 0.0, places=4,
                               msg="ordinary Monday work is not rest-day extra time")
        self.assertAlmostEqual(monday.first_in, 0.5, places=4)

    def test_deleting_a_short_night_stay_clears_its_morning(self):
        """A stay of 00:30-01:30 entered by mistake and deleted leaves Tuesday empty.

        Both moments carry Monday's date in UTC; refreshing by them would
        update Monday and leave Tuesday showing a stay that no longer exists.
        """
        stay = self.env["hr.attendance"].create({
            "employee_id": self.person.id,
            "check_in": in_sofia(TUESDAY, 0, 30),
            "check_out": in_sofia(TUESDAY, 1, 30),
        })
        self.assertAlmostEqual(self._day(TUESDAY).first_in, 0.5, places=4)
        stay.unlink()
        tuesday = self._day(TUESDAY)
        self.assertFalse(tuesday.first_in, "Tuesday no longer shows an arrival")
        self.assertAlmostEqual(tuesday.actual_work_time + tuesday.overtime + tuesday.extra_time,
                               0.0, places=4, msg="nor any time worked")

    def test_the_upgrade_fills_arrival_as_the_daily_figures_do(self):
        """The upgrade's 'came at / left at' for a night stay is the recompute's.

        The upgrade fills the two columns for days measured before they
        existed; a later recompute must find the same values there, or every
        such night changes the moment someone presses the button.
        """
        self.env["hr.attendance"].create({
            "employee_id": self.person.id,
            "check_in": in_sofia(TUESDAY, 0, 30),
            "check_out": in_sofia(TUESDAY, 8, 30),
        })
        tuesday = self._day(TUESDAY)
        computed = (tuesday.first_in, tuesday.last_out)
        self.assertEqual(computed, (0.5, 8.5))
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE hr_attendance_extra SET first_in = NULL, last_out = NULL WHERE id = %s",
            [tuesday.id])
        _upgrade_fill()(self.env.cr)
        tuesday.invalidate_recordset(["first_in", "last_out"])
        self.assertEqual((tuesday.first_in, tuesday.last_out), computed)

    def test_the_recompute_offers_the_officers_today(self):
        """At 00:30 on Friday in Sofia, "today" in both recompute forms is Friday.

        In UTC it is still Thursday; offered that, the officer's recompute of
        "up to today" would leave the day they are in out of it.
        """
        self.env.user.tz = "Europe/Sofia"
        with freeze_time(in_sofia(FRIDAY, 0, 30)):
            for wizard in ("hr.attendance.extra.wizard", "hr.attendance.recalc.wizard"):
                self.assertEqual(self.env[wizard]._get_default_to(), FRIDAY,
                                 "%s must offer Friday" % wizard)
