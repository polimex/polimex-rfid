"""A working schedule says what a forgotten day is worth for its own people.

The request behind this, in the customer's words through our technician
(12.11.2026): "can the customer choose how many hours the working day is when
nobody badged out? If not, take it as 7 hours." Their artists work a floating
schedule of fourteen hours a day - the frame they may work in, not a day of
pay - and crediting all fourteen for every forgotten badge is what the customer
refused. The office keeps its eight-hour day, so one number for the whole
company would not do.

The company's Forgotten Badge setting still decides WHETHER a forgotten day is
credited and what a penalty takes off; the schedule's number only replaces
"the scheduled day" in it, and never pays more than that day.
"""

from datetime import timedelta

from psycopg2 import errors

from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from .test_a_new_entry_after_a_forgotten_badge import ForgottenBadgeCase


class FloatingScheduleCase(ForgottenBadgeCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The artists' schedule as the customer has it: floating, fourteen
        # hours a day, a frame from eight to ten at night every day.
        cls.floating = cls._every_day_calendar(
            "Floating 14",
            (("morning", 8.0, 22.0),),
            flexible_hours=True,
            hours_per_day=14.0,
        )
        cls.artist = cls._person("Forgetful Artist")
        cls.artist.resource_calendar_id = cls.floating

    def _seven_hours_for_the_artists(self):
        self.floating.forgotten_badge_hours = 7.0

    def _office_day_worth(self, hours, check_in=timedelta(hours=8)):
        """The office worker forgets on Monday; what is Monday worth?"""
        self.calendar.forgotten_badge_hours = hours
        self._in(self.monday + check_in)
        self._in(self.at(self.tuesday, 8))
        return self._stays()[0]


@tagged("post_install", "-at_install", "rfid_attendance_zone", "rfid_forgotten_hours")
class TestTheScheduleSaysWhatAForgottenDayIsWorth(FloatingScheduleCase):
    def test_the_artist_who_forgot_is_credited_seven_hours(self):
        """In at ten, no badge-out; the next morning's entry closes the day at five.

        Seven hours, as the customer chose for the floating schedule - not the
        fourteen of its frame. And the new day is that day's own.
        """
        self._seven_hours_for_the_artists()
        self._in(self.at(self.monday, 10), self.artist)
        self._in(self.at(self.tuesday, 10), self.artist)

        monday, tuesday = self._stays(self.artist)
        self.assertEqual(monday.check_out, self.at(self.monday, 17))
        self.assertEqual(monday.worked_hours, 7.0)
        self.assertTrue(monday.forgotten_badge, "and it can be found to correct")
        self.assertEqual(monday.out_mode, "auto_check_out")
        self.assertFalse(tuesday.check_out)

    def test_without_a_number_the_artist_gets_the_schedules_day(self):
        """NEGATIVE: a schedule left at zero keeps crediting its own day.

        Nothing changes for a customer who never touches the new number.
        """
        self._in(self.at(self.monday, 6), self.artist)
        self._in(self.at(self.tuesday, 8), self.artist)

        self.assertEqual(self._stays(self.artist)[0].worked_hours, 14.0)

    def test_the_office_keeps_its_eight_hours(self):
        """NEGATIVE: the artists' number is theirs, not the company's.

        The office worker on the eight-hour schedule who forgets on the same
        day is still credited the working day, its lunch hour included.
        """
        self._seven_hours_for_the_artists()
        monday = self._office_day_worth(0.0)

        self.assertEqual(monday.check_out, self.at(self.monday, 17))
        self.assertEqual(monday.worked_hours, 8.0)

    def test_on_a_schedule_with_a_lunch_hour_the_hours_are_worked_hours(self):
        """Six hours on an 08-12 / 13-17 day end at three, not at two.

        Core takes the unpaid lunch hour out of a stay on a fixed schedule, so
        a day that is to count six hours must run over it. What the payroll
        clerk reads is the number the schedule says.
        """
        monday = self._office_day_worth(6.0)

        self.assertEqual(monday.check_out, self.at(self.monday, 15))
        self.assertEqual(monday.worked_hours, 6.0)

    def test_a_number_that_ends_before_lunch_does_not_step_over_it(self):
        """Boundary: four hours from eight end at twelve, the break untouched."""
        monday = self._office_day_worth(4.0)

        self.assertEqual(monday.check_out, self.at(self.monday, 12))
        self.assertEqual(monday.worked_hours, 4.0)

    def test_a_number_that_ends_inside_lunch_ends_after_it(self):
        """Four and a half hours from eight: 12:30 is lunch, the day ends at 13:30."""
        monday = self._office_day_worth(4.5)

        self.assertEqual(monday.check_out, self.at(self.monday, 13.5))
        self.assertEqual(monday.worked_hours, 4.5)

    def test_a_check_in_off_the_hour_is_credited_to_the_minute(self):
        """In at 08:03 with four hours to credit: out at 13:03, worth four hours.

        Not three hours and fifty-seven minutes because the end landed in the
        lunch hour - the payroll would show the missing minutes.
        """
        monday = self._office_day_worth(4.0, check_in=timedelta(hours=8, minutes=3))

        self.assertEqual(monday.check_out, self.monday + timedelta(hours=13, minutes=3))
        self.assertEqual(monday.worked_hours, 4.0)

    def test_a_number_above_the_day_pays_only_the_day(self):
        """Ten hours on an eight-hour schedule: a forgotten day pays eight.

        The number can lower what a forgotten day is worth, never raise it
        above a day the person did badge out of.
        """
        monday = self._office_day_worth(10.0)

        self.assertEqual(monday.check_out, self.at(self.monday, 17))
        self.assertEqual(monday.worked_hours, 8.0)

    def test_a_negative_number_is_refused(self):
        """NEGATIVE: a negative number of hours is a typing mistake, not a rule."""
        with mute_logger("odoo.sql_db"), self.assertRaises(errors.CheckViolation):
            self.floating.forgotten_badge_hours = -1.0
            self.floating.flush_recordset()

    def test_the_companys_penalty_comes_off_the_schedules_number(self):
        """Seven hours less the two the company takes off: five."""
        self._seven_hours_for_the_artists()
        self.company.write(
            {"forgotten_badge_policy": "penalty", "forgotten_badge_penalty_hours": 2.0}
        )
        self._in(self.at(self.monday, 10), self.artist)
        self._in(self.at(self.tuesday, 10), self.artist)

        self.assertEqual(self._stays(self.artist)[0].worked_hours, 5.0)

    def test_a_company_that_counts_nothing_still_counts_nothing(self):
        """NEGATIVE: the schedule's number does not overrule "count nothing".

        That setting says a person has to enter the real hours by hand, and a
        number on a schedule is no answer to it.
        """
        self._seven_hours_for_the_artists()
        self.company.write({"forgotten_badge_policy": "ignore"})
        self._in(self.at(self.monday, 10), self.artist)
        self._in(self.at(self.tuesday, 10), self.artist)

        monday = self._stays(self.artist)[0]
        self.assertEqual(monday.worked_hours, 0.0)
        self.assertTrue(monday.forgotten_badge)

    def test_a_second_stay_gets_what_is_left_of_the_seven(self):
        """Out at twelve with a badge, back at one and forgot: three more hours.

        A day is worth the schedule's number however many stays it took.
        """
        self._seven_hours_for_the_artists()
        self._in(self.at(self.monday, 8), self.artist)
        self._out(self.at(self.monday, 12), self.artist)
        self._in(self.at(self.monday, 13), self.artist)
        self._in(self.at(self.tuesday, 10), self.artist)

        first, second, _tuesday = self._stays(self.artist)
        self.assertEqual(first.worked_hours, 4.0)
        self.assertEqual(second.check_out, self.at(self.monday, 16))
        self.assertEqual(second.worked_hours, 3.0)

    def test_the_task_credits_the_schedules_number(self):
        """The scheduled task settles a forgotten day of an artist with seven."""
        self._seven_hours_for_the_artists()
        stay = self._machine_stay(self.at(self.monday, 10), employee=self.artist)

        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(stay.check_out, self.at(self.monday, 17))
        self.assertEqual(stay.worked_hours, 7.0)
        self.assertTrue(stay.forgotten_badge)

    def test_a_stay_closed_far_too_late_is_moved_back_to_the_number(self):
        """Closed at three the next night, seventeen hours: it comes back to seven.

        The note on the record says what payroll will read.
        """
        self._seven_hours_for_the_artists()
        stay = self._machine_stay(
            self.at(self.monday, 10), self.at(self.tuesday, 3), employee=self.artist
        )

        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(stay.check_out, self.at(self.monday, 17))
        self.assertEqual(stay.worked_hours, 7.0)
        notes = [
            body for body in stay.message_ids.mapped("body") if "moved back" in body
        ]
        self.assertEqual(len(notes), 1, notes)
        self.assertIn("Credited 7.00 hours", notes[0])

    def test_the_note_on_a_moved_check_out_says_what_payroll_reads(self):
        """An office day closed at three the next night comes back to five o'clock.

        Nine hours on the clock, eight of them worked: the note says eight,
        the number on the payslip, not the clock's nine.
        """
        stay = self._machine_stay(self.at(self.monday, 8), self.at(self.tuesday, 3))

        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(stay.check_out, self.at(self.monday, 17))
        self.assertEqual(stay.worked_hours, 8.0)
        notes = [
            body for body in stay.message_ids.mapped("body") if "moved back" in body
        ]
        self.assertEqual(len(notes), 1, notes)
        self.assertIn("Credited 8.00 hours", notes[0])

    def test_switched_back_on_the_task_settles_with_the_number_set_meanwhile(self):
        """The order of the steps at the customer.

        Automatic Check-Out goes off before the update, the number goes on the
        schedule, Automatic Check-Out comes back on. While it is off, the task
        leaves the forgotten day alone; once it is on, the day is worth seven,
        not the fourteen the schedule says without the number.
        """
        stay = self._machine_stay(self.at(self.monday, 10), employee=self.artist)
        self.company.auto_check_out = False

        self.env["hr.attendance"]._cron_auto_check_out()
        self.assertFalse(stay.check_out)
        self.assertFalse(stay.forgotten_badge)

        self._seven_hours_for_the_artists()
        self.company.auto_check_out = True
        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(stay.worked_hours, 7.0)

    def test_a_new_number_leaves_settled_days_alone_until_a_rebuild(self):
        """A day settled before the number was set keeps what it was credited.

        Changing the schedule does not rewrite days somebody may already have
        paid. A rebuild of the period tells the doors' story again, with the
        number that is set now.
        """
        self._in(self.at(self.monday, 10), self.artist)
        self._in(self.at(self.tuesday, 10), self.artist)
        self.assertEqual(self._stays(self.artist)[0].worked_hours, 14.0)

        self._seven_hours_for_the_artists()
        self.env["hr.attendance"]._cron_auto_check_out()
        self.assertEqual(self._stays(self.artist)[0].worked_hours, 14.0)

        self._rebuild(self.artist)
        self.assertEqual(self._stays(self.artist)[0].worked_hours, 7.0)

    def test_the_rebuild_tells_the_same_story_as_the_doors(self):
        """Same passages, same seven hours, whichever machine reads them."""
        self._seven_hours_for_the_artists()
        self._in(self.at(self.monday, 10), self.artist)
        self._in(self.at(self.tuesday, 10), self.artist)
        self._out(self.at(self.tuesday, 18), self.artist)

        self._assert_the_doors_tell_one_story(self.artist)
        self.assertEqual(self._stays(self.artist)[0].worked_hours, 7.0)

    def test_a_past_day_is_worth_what_its_own_schedule_said(self):
        """Moved to the office on Tuesday, the artist's Monday is still worth seven.

        The day is judged by the schedule of that day, and so is its number: a
        rebuild of a past period must not pay the old floating day in full
        because the person is on another schedule today.
        """
        self._seven_hours_for_the_artists()
        start = (self.monday - timedelta(days=30)).date()
        self.artist.version_id.write(
            {
                "date_version": start,
                "contract_date_start": start,
                "resource_calendar_id": self.floating.id,
            }
        )
        self.artist.create_version(
            {
                "date_version": self.tuesday.date(),
                "contract_date_start": start,
                "resource_calendar_id": self.calendar.id,
            }
        )
        self.assertEqual(self.artist.resource_calendar_id, self.calendar)
        stay = self._machine_stay(self.at(self.monday, 10), employee=self.artist)

        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(stay.check_out, self.at(self.monday, 17))
        self.assertEqual(stay.worked_hours, 7.0)


@tagged(
    "post_install", "-at_install", "rfid_forgotten_hours", "rfid_forgotten_hours_tour"
)
class TestTheNumberIsSetOnTheSchedule(HttpCase):
    """Whoever keeps the working schedules enters the number on the schedule."""

    # A tour drives the real web client, which needs to write to the database
    # the way a user does.
    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schedule = cls.env["resource.calendar"].create(
            {"name": "Tour Floating Schedule", "company_id": cls.env.company.id}
        )

    def test_seven_hours_are_typed_in_and_saved(self):
        self.start_tour(
            "/odoo/action-resource.action_resource_calendar_form",
            "hr_attendance_forgotten_badge_hours_tour",
            login="admin",
        )
        self.assertEqual(self.schedule.forgotten_badge_hours, 7.0)
