"""A forgotten badge-out must never pay better than a kept one.

The complaint behind this, from the technician who shows the system to
customers (16.11.2026), about a day somebody came in late and never badged
out: "Why is the working day counted from the hour of arrival and not from the
hour the schedule gives as the start of the working day? Now, in spite of the
missed badge and in spite of being late - two faults in one day - the employee
gets overtime."

The day used to be credited its whole length from the moment the person came
in: in at 09:07 on an 08:00-17:00 schedule, out at 18:07. An hour and seven
minutes past the schedule, which the daily figures read as overtime, and a
full day for somebody who was late.

The owner's decision the same day: a forgotten badge-out pays no more than a
day badged out properly. Whoever came in while their schedule was running is
credited to the end of that schedule; "from the hour of arrival" stays only
for whoever came in outside it - the evening performance after the office
day.
"""

from datetime import date, timedelta

from odoo.tests import tagged

from .common import in_sofia
from .test_a_new_entry_after_a_forgotten_badge import ForgottenBadgeCase

SEVEN_PAST_NINE = 9 + 7 / 60
# Mondays, one on winter time and one on summer time in Sofia.
A_WINTER_MONDAY = date(2026, 1, 12)
A_SUMMER_MONDAY = date(2026, 7, 13)


@tagged("post_install", "-at_install", "rfid_attendance_zone", "rfid_forgotten_day")
class TestAForgottenDayEndsWithTheSchedule(ForgottenBadgeCase):
    def _monday_of_the_one_who_forgot(self, hour, employee=None):
        """In on Monday, no badge-out; Tuesday morning's entry settles Monday."""
        self._in(self.at(self.monday, hour), employee)
        self._in(self.at(self.tuesday, 8), employee)
        return self._stays(employee)[0]

    def _nights(
        self, name="Nights 22-06", evening_ends=24.0, morning=(("morning", 0.0, 6.0),)
    ):
        """Ten at night to six in the morning, every day."""
        return self._every_day_calendar(
            name, (*morning, ("afternoon", 22.0, evening_ends)), hours_per_day=8.0
        )

    def _floating_fourteen(self):
        """The artists' schedule as a customer has it: a frame from eight to ten at night.

        With a week to fill, core answers "what was expected that day" for a
        floating schedule with a stand-in window around noon
        (resource_calendar.py:419) - here 05:00 to 19:00 - and its end is the
        end of nothing.
        """
        return self._every_day_calendar(
            "Floating 14",
            (("morning", 8.0, 22.0),),
            flexible_hours=True,
            hours_per_day=14.0,
            hours_per_week=40.0,
        )

    def _forgotten_on(self, calendar, name, check_in):
        """Somebody on this schedule comes in, never badges out, and the task settles it."""
        person = self._person(name)
        person.resource_calendar_id = calendar
        stay = self._machine_stay(check_in, employee=person)
        self.env["hr.attendance"].with_context(
            attendance_calc_time=self.wednesday + timedelta(hours=12)
        ).check_for_incomplete_attendances()
        return stay

    def test_late_and_forgetful_is_credited_to_the_end_of_the_schedule(self):
        """In at 09:07, no badge-out: the day ends at five, with the schedule.

        Not at 18:07. The hour and seven minutes they were late are not made
        up by forgetting to badge out, and the doors tell the same story when
        the period is rebuilt from the passages.
        """
        monday = self._monday_of_the_one_who_forgot(SEVEN_PAST_NINE)

        self.assertEqual(monday.check_out, self.at(self.monday, 17))
        self.assertAlmostEqual(monday.worked_hours, 8.0 - 67 / 60, 2)
        self.assertTrue(monday.forgotten_badge, "and it can still be found to correct")
        self.assertEqual(monday.out_mode, "auto_check_out")
        self._assert_the_doors_tell_one_story()

    def test_forgetting_never_pays_more_than_badging_out_on_time(self):
        """NEGATIVE: two people come in at 09:07; one badges out at five, one forgets.

        The one who forgot must not be credited a minute more than the one who
        badged out when the schedule ended.
        """
        kept = self._person("Late But Careful")
        self._in(self.at(self.monday, SEVEN_PAST_NINE), kept)
        self._out(self.at(self.monday, 17), kept)

        forgotten = self._monday_of_the_one_who_forgot(SEVEN_PAST_NINE)

        self.assertLessEqual(forgotten.worked_hours, self._stays(kept)[0].worked_hours)
        self.assertLessEqual(forgotten.check_out, self._stays(kept)[0].check_out)

    def test_on_time_is_credited_the_whole_day_as_before(self):
        """NEGATIVE: nothing changes for whoever came in when the day began."""
        monday = self._monday_of_the_one_who_forgot(8)

        self.assertEqual(monday.check_out, self.at(self.monday, 17))
        self.assertEqual(monday.worked_hours, 8.0)

    def test_the_evening_performance_is_still_credited_a_working_day(self):
        """In at seven in the evening, after the schedule ended: a day from then.

        The reason the day was counted from the arrival in the first place.
        Somebody called in for the evening is not inside their schedule, there
        is no end of it ahead of them, and they are credited a working day
        instead of nothing.
        """
        monday = self._monday_of_the_one_who_forgot(19)

        self.assertEqual(monday.check_out, self.at(self.monday, 19 + 9))
        self.assertTrue(monday.forgotten_badge)

    def test_whoever_came_before_the_day_began_is_credited_from_the_arrival(self):
        """In at half past seven: a working day from then, to half past four.

        Before the schedule starts is outside it as well, so the day keeps its
        own length from the arrival - it ends inside the schedule and nothing
        of it can read as overtime.
        """
        monday = self._monday_of_the_one_who_forgot(7.5)

        self.assertEqual(monday.check_out, self.at(self.monday, 16.5))
        self.assertEqual(monday.worked_hours, 8.0)

    def test_back_late_from_lunch_is_credited_to_the_end_of_the_schedule(self):
        """In from eight to twelve, back at two instead of one, no badge-out.

        Four hours of the day were left to credit, but only three of them
        were still ahead in the schedule: the afternoon ends at five, not at
        six.
        """
        self._in(self.at(self.monday, 8))
        self._out(self.at(self.monday, 12))
        self._in(self.at(self.monday, 14))
        self._in(self.at(self.tuesday, 8))

        morning, afternoon, _tuesday = self._stays()
        self.assertEqual(morning.check_out, self.at(self.monday, 12))
        self.assertEqual(afternoon.check_out, self.at(self.monday, 17))
        self.assertTrue(afternoon.forgotten_badge)

    def test_the_penalty_comes_off_the_day_that_ends_with_the_schedule(self):
        """Late, forgetful, and the company takes an hour off for forgetting.

        The day ends at five and the hour comes off that: four o'clock. Taken
        off the day counted from the arrival it would have ended at 17:07 -
        the penalty swallowed by the minutes the person was late.
        """
        self.company.write(
            {"forgotten_badge_policy": "penalty", "forgotten_badge_penalty_hours": 1.0}
        )

        monday = self._monday_of_the_one_who_forgot(SEVEN_PAST_NINE)

        self.assertEqual(monday.check_out, self.at(self.monday, 16))

    def test_the_schedules_own_number_stops_at_the_end_of_the_schedule_too(self):
        """Seven hours for a forgotten badge, in at half past ten: out at five.

        Seven worked hours from half past ten would end at half past six. The
        number says what a forgotten day is worth at most; it does not give
        back the hours somebody was late.
        """
        self.calendar.forgotten_badge_hours = 7.0

        monday = self._monday_of_the_one_who_forgot(10.5)

        self.assertEqual(monday.check_out, self.at(self.monday, 17))
        self.assertEqual(monday.worked_hours, 5.5)

    def test_the_number_and_the_penalty_on_a_late_day(self):
        """Seven hours, an hour's penalty, in at half past ten: out at four.

        Five and a half hours were still ahead in the schedule, an hour comes
        off them, and the four and a half that are left end at four.
        """
        self.calendar.forgotten_badge_hours = 7.0
        self.company.write(
            {"forgotten_badge_policy": "penalty", "forgotten_badge_penalty_hours": 1.0}
        )

        monday = self._monday_of_the_one_who_forgot(10.5)

        self.assertEqual(monday.check_out, self.at(self.monday, 16))
        self.assertEqual(monday.worked_hours, 4.5)

    def test_a_floating_schedule_has_no_end_to_stop_at(self):
        """NEGATIVE: the artist in at three in the afternoon keeps their seven hours.

        A floating schedule is a frame people may work in, not hours they are
        late for or leave early from. Nobody on it is "inside the schedule"
        or past its end, so the day is counted from the arrival as before: to
        ten in the evening, not to the seven o'clock core's stand-in ends at.
        Measured on a customer database before this was guarded: 772 of the
        artists' forgotten days would have been cut there.
        """
        floating = self._floating_fourteen()
        floating.forgotten_badge_hours = 7.0
        artist = self._person("Afternoon Artist")
        artist.resource_calendar_id = floating
        stand_in_ends = max(
            stop
            for _start, stop, _meta in artist._get_expected_attendances(
                *artist._local_days_bounds(self.monday.date(), self.monday.date())
            )
        )
        self.assertLess(
            stand_in_ends.replace(tzinfo=None),
            self.at(self.monday, 22),
            "the premise: core describes a day for this schedule that ends before "
            "the seven hours from three o'clock do",
        )

        self._in(self.at(self.monday, 15), artist)
        self._in(self.at(self.tuesday, 15), artist)

        monday = self._stays(artist)[0]
        self.assertEqual(monday.check_out, self.at(self.monday, 22))
        self.assertEqual(monday.worked_hours, 7.0)

    def test_an_afternoon_off_ends_the_day_at_noon(self):
        """Approved leave for the afternoon: the day they owed ended at twelve.

        Late in the morning and no badge-out, they are credited to noon - the
        end of what they were scheduled for that day - not into the afternoon
        they had off.
        """
        self.env["resource.calendar.leaves"].create(
            {
                "name": "Afternoon off",
                "calendar_id": self.calendar.id,
                "resource_id": self.employee.resource_id.id,
                "company_id": self.company.id,
                "date_from": self.at(self.monday, 12),
                "date_to": self.at(self.monday, 17),
                "time_type": "leave",
            }
        )

        monday = self._monday_of_the_one_who_forgot(SEVEN_PAST_NINE)

        self.assertEqual(monday.check_out, self.at(self.monday, 12))

    def test_a_shift_that_crosses_midnight_is_not_cut_at_midnight(self):
        """Ten at night to six in the morning, in half an hour late, no badge-out.

        The schedule of that day reaches midnight and goes straight on the
        next morning. The end of what the person came in for is six, so that
        is where the night is credited to - not midnight, which would leave
        an hour and a half of an eight-hour night.
        """
        night = self._forgotten_on(
            self._nights(), "Night Guard", self.at(self.monday, 22.5)
        )

        self.assertEqual(night.check_out, self.at(self.tuesday, 6))
        self.assertTrue(night.forgotten_badge)

    def test_late_for_a_night_that_began_the_evening_before(self):
        """Half past midnight on the ten-to-six shift, no badge-out: credited to six.

        The stay began after midnight, so it belongs to the new day - and the
        first thing that day's schedule holds is the rest of last night's
        shift. That is what the person came in for, and it ends at six that
        morning, not with the shift that begins at ten the same evening.
        """
        night = self._forgotten_on(
            self._nights(), "Late Night Guard", self.at(self.tuesday, 0.5)
        )

        self.assertEqual(night.check_out, self.at(self.tuesday, 6))

    def test_a_break_in_the_night_does_not_end_the_shift(self):
        """Ten to six with half an hour off at two: the night still ends at six.

        The break is the schedule's own; the work goes on after it, and so
        does the night of whoever came in at half past ten and forgot.
        """
        with_a_break = self._nights(
            "Nights 22-06 With A Break",
            morning=(
                ("morning", 0.0, 2.0),
                ("lunch", 2.0, 2.5),
                ("afternoon", 2.5, 6.0),
            ),
        )

        night = self._forgotten_on(
            with_a_break, "Night Guard With A Break", self.at(self.monday, 22.5)
        )

        self.assertEqual(night.check_out, self.at(self.tuesday, 6))

    def test_a_post_manned_round_the_clock_has_no_end_to_stop_at(self):
        """NEGATIVE: a schedule that never stops keeps the day counted from the arrival.

        Day and night without a gap, every day: there is no end of the
        schedule ahead of anybody, so nothing here can say when the person
        should have left. The day is credited from the arrival, as before.
        """
        post = self._every_day_calendar(
            "Round The Clock",
            (("morning", 0.0, 12.0), ("afternoon", 12.0, 24.0)),
            hours_per_day=24.0,
        )

        stay = self._forgotten_on(post, "Post Guard", self.at(self.monday, 19))

        self.assertAlmostEqual(
            stay.check_out, self.at(self.monday, 19 + 24), delta=timedelta(seconds=1)
        )

    def test_a_schedule_that_ends_at_midnight_ends_there(self):
        """NEGATIVE: an evening shift to midnight with a free morning after it.

        Nothing goes on after midnight here, so the day of whoever came in
        late and forgot ends at midnight - not at the end of the next
        evening's shift.
        """
        evenings = self._every_day_calendar(
            "Evenings 16-24", (("afternoon", 16.0, 24.0),), hours_per_day=8.0
        )

        evening = self._forgotten_on(
            evenings, "Evening Usher", self.at(self.monday, 17)
        )

        self.assertEqual(evening.check_out, self.at(self.tuesday, 0))

    def test_a_night_typed_in_up_to_a_minute_before_midnight_is_one_shift_too(self):
        """The evening part entered as 22:00-23:59: the night still ends at six.

        A minute short of midnight is how many schedules are typed in. The
        shift goes on the next morning all the same.
        """
        nights = self._nights("Nights 22-23:59", evening_ends=23 + 59 / 60)

        night = self._forgotten_on(
            nights, "Night Guard To 23:59", self.at(self.monday, 22.5)
        )

        self.assertEqual(night.check_out, self.at(self.tuesday, 6))

    def test_a_quarter_of_an_hour_before_the_end_is_credited_a_quarter_of_an_hour(self):
        """In at 16:45, no badge-out: the schedule ended at five, and so does the day.

        Whoever really stayed on for the evening has the hours entered by
        hand; the record is marked as a forgotten badge, so it can be found.
        """
        monday = self._monday_of_the_one_who_forgot(16.75)

        self.assertEqual(monday.check_out, self.at(self.monday, 17))
        self.assertEqual(monday.worked_hours, 0.25)
        self.assertTrue(monday.forgotten_badge)

    def test_a_day_settled_before_the_rule_keeps_its_end_until_a_rebuild(self):
        """Monday was settled while the day was still counted from the arrival: out at 18:07.

        The scheduled task leaves a settled day alone - nobody's past record
        moves because the module was updated. A rebuild of the period
        (Re-create Attendance records) settles it again by the rule in force:
        out at five.
        """
        monday = self._monday_of_the_one_who_forgot(SEVEN_PAST_NINE)
        as_it_was = self.at(self.monday, 18) + timedelta(minutes=7)
        monday.with_context(
            rfid_machinery_write=True, no_validity_check=True
        ).check_out = as_it_was

        self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertEqual(monday.check_out, as_it_was)

        self._rebuild()

        self.assertEqual(self._stays()[0].check_out, self.at(self.monday, 17))

    def test_in_on_the_minute_the_schedule_ends_is_an_evening_arrival(self):
        """In at five sharp: the schedule has ended, there is no end of it ahead.

        The day is counted from the arrival, as for anybody who comes in for
        the evening.
        """
        monday = self._monday_of_the_one_who_forgot(17)

        self.assertEqual(monday.check_out, self.at(self.monday, 17 + 9))

    def _moved_on_tuesday(self, person, from_calendar, to_calendar):
        """On one schedule up to Monday, on another from Tuesday."""
        start = (self.monday - timedelta(days=30)).date()
        person.version_id.write(
            {
                "date_version": start,
                "contract_date_start": start,
                "resource_calendar_id": from_calendar.id,
            }
        )
        person.create_version(
            {
                "date_version": self.tuesday.date(),
                "contract_date_start": start,
                "resource_calendar_id": to_calendar.id,
            }
        )
        self.assertEqual(person.resource_calendar_id, to_calendar)

    def test_a_past_day_ends_with_the_schedule_the_person_was_on_then(self):
        """In the office on Monday, moved to the floating schedule on Tuesday.

        Monday is judged by Monday's schedule: in at 09:07 and forgotten, the
        day ends at five - though the person is on a schedule with no end
        today.
        """
        clerk = self._person("Clerk Until Monday")
        self._moved_on_tuesday(clerk, self.calendar, self._floating_fourteen())
        stay = self._machine_stay(self.at(self.monday, SEVEN_PAST_NINE), employee=clerk)

        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(stay.check_out, self.at(self.monday, 17))

    def test_a_past_day_on_the_floating_schedule_is_not_cut_by_todays_office(self):
        """NEGATIVE: on the floating schedule on Monday, in the office from Tuesday.

        Monday had no end to stop at: in at three in the afternoon with seven
        hours for a forgotten badge, the day ends at ten - not at the five of
        the office the person works in today.
        """
        floating = self._floating_fourteen()
        floating.forgotten_badge_hours = 7.0
        artist = self._person("Artist Until Monday")
        self._moved_on_tuesday(artist, floating, self.calendar)
        stay = self._machine_stay(self.at(self.monday, 15), employee=artist)

        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(stay.check_out, self.at(self.monday, 22))


@tagged("post_install", "-at_install", "rfid_attendance_zone", "rfid_forgotten_day")
class TestTheScheduleEndsWhereThePersonIs(ForgottenBadgeCase):
    """The end of the schedule is an hour on the wall where the person works.

    Sofia is two hours ahead of the database's clock in winter and three in
    summer; a day and a night there are different stretches of time than the
    same dates are in UTC.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sofia_office = cls._every_day_calendar(
            "Sofia Office 8-17",
            (
                ("morning", 8.0, 12.0),
                ("lunch", 12.0, 13.0),
                ("afternoon", 13.0, 17.0),
            ),
            hours_per_day=8.0,
            tz="Europe/Sofia",
        )
        cls.sofia_nights = cls._every_day_calendar(
            "Sofia Nights 22-06",
            (("morning", 0.0, 6.0), ("afternoon", 22.0, 24.0)),
            hours_per_day=8.0,
            tz="Europe/Sofia",
        )

    def _in_sofia_on(self, name, calendar):
        person = self._person(name)
        person.write({"tz": "Europe/Sofia", "resource_calendar_id": calendar.id})
        return person

    def _late_and_forgetful_on(self, monday):
        clerk = self._in_sofia_on("Sofia Clerk %s" % monday, self.sofia_office)
        self._in(in_sofia(monday, 9, 7), clerk)
        self._in(in_sofia(monday + timedelta(days=1), 8), clerk)
        return self._stays(clerk)[0]

    def test_in_winter_the_day_ends_at_five_on_the_sofia_clock(self):
        """In at 09:07 in Sofia in January, no badge-out: out at 17:00 there."""
        monday = self._late_and_forgetful_on(A_WINTER_MONDAY)

        self.assertEqual(monday.check_out, in_sofia(A_WINTER_MONDAY, 17))

    def test_in_summer_the_day_ends_at_five_on_the_sofia_clock(self):
        """The same in July, when Sofia is three hours ahead and not two."""
        monday = self._late_and_forgetful_on(A_SUMMER_MONDAY)

        self.assertEqual(monday.check_out, in_sofia(A_SUMMER_MONDAY, 17))

    def _night_of(self, guard, check_in):
        night = self._machine_stay(check_in, employee=guard)
        self.env["hr.attendance"].with_context(
            attendance_calc_time=check_in + timedelta(days=2)
        ).check_for_incomplete_attendances()
        return night

    def test_a_sofia_night_ends_at_six_in_the_morning_there(self):
        """In at 22:30 on Monday in Sofia, no badge-out: out at 06:00 on Tuesday."""
        guard = self._in_sofia_on("Sofia Night Guard", self.sofia_nights)

        night = self._night_of(guard, in_sofia(A_SUMMER_MONDAY, 22, 30))

        self.assertEqual(
            night.check_out, in_sofia(A_SUMMER_MONDAY + timedelta(days=1), 6)
        )

    def test_half_past_midnight_in_sofia_is_still_last_nights_shift(self):
        """In at 00:30 on Tuesday in Sofia - the database still reads Monday.

        The stay is Tuesday's, it came in under the shift that began on Monday
        evening, and it ends at six that same Tuesday morning.
        """
        guard = self._in_sofia_on("Late Sofia Night Guard", self.sofia_nights)
        tuesday = A_SUMMER_MONDAY + timedelta(days=1)

        night = self._night_of(guard, in_sofia(tuesday, 0, 30))

        self.assertEqual(night.check_out, in_sofia(tuesday, 6))
