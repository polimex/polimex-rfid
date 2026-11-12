"""A forgotten badge-out must cost one day's figures, not the days after it.

The complaint behind this: somebody forgets to badge out, and the next morning's
entry reads "Already inside". The new day gets no record of its own, that
evening's exit closes one stay across both days, and the person is left with a
record of more than a day. On a customer database 1270 stays ran past 24 hours,
and the passages inside them were almost all entries marked this way.

The company has already said what a forgotten badge is worth (Settings ->
Attendances: Automatic Check-Out with its tolerance, and Forgotten Badge). So an
entry that finds a stay past that limit settles it, by that setting, and begins
a new day. Live and in a rebuild, because the same doors must tell the same
story whichever machine reads them.
"""

from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time
from psycopg2 import errors

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

from .common import in_sofia, one_door, passage

MULTI_RFID_LOG = "odoo.addons.hr_attendance_multi_rfid.models.hr_attendance"


class ForgottenBadgeCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # Eight hours of work and an unpaid hour between them, every day, with
        # two hours of tolerance: a stay is past its limit after ten hours, and
        # a credited day runs from the check-in for nine.
        cls.calendar = cls._every_day_calendar(
            "New Entry 8-17",
            (
                ("morning", 8.0, 12.0),
                ("lunch", 12.0, 13.0),
                ("afternoon", 13.0, 17.0),
            ),
            hours_per_day=8.0,
        )
        cls.company.write(
            {
                "auto_check_out": True,
                "auto_check_out_tolerance": 2.0,
                "forgotten_badge_policy": "credit_schedule",
            }
        )
        cls.door, cls.reader_in, cls.reader_out = one_door(
            cls.env, "New Entry", 8847, 13, tz="UTC"
        )
        cls.zone = cls.env["hr.rfid.zone"].create(
            {
                "name": "New Entry Zone",
                "company_id": cls.company.id,
                "attendance": True,
                "overwrite_check_in": False,
                "overwrite_check_out": False,
                "door_ids": [Command.link(cls.door.id)],
            }
        )
        cls.employee = cls._person("Forgetful Worker")
        cls.monday = (fields.Datetime.now() - timedelta(days=10)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cls.tuesday = cls.monday + timedelta(days=1)
        cls.wednesday = cls.monday + timedelta(days=2)

    @classmethod
    def _every_day_calendar(cls, name, periods, **values):
        """A schedule with the same day, Monday to Sunday, in UTC.

        :param periods: (day_period, hour_from, hour_to) of that day
        """
        return cls.env["resource.calendar"].create(
            {
                "name": name,
                "company_id": cls.company.id,
                "tz": "UTC",
                "attendance_ids": [
                    Command.create(
                        {
                            "name": "%s %s" % (day, period),
                            "dayofweek": day,
                            "hour_from": start,
                            "hour_to": stop,
                            "day_period": period,
                        }
                    )
                    for day in "0123456"
                    for period, start, stop in periods
                ],
                **values,
            }
        )

    @classmethod
    def _person(cls, name):
        return cls.env["hr.employee"].create(
            {
                "name": name,
                "company_id": cls.company.id,
                "tz": "UTC",
                "resource_calendar_id": cls.calendar.id,
            }
        )

    def at(self, day, hours):
        return day + timedelta(hours=hours)

    def _in(self, moment, employee=None):
        return passage(employee or self.employee, self.door, self.reader_in, moment)

    def _out(self, moment, employee=None):
        return passage(employee or self.employee, self.door, self.reader_out, moment)

    def _stays(self, employee=None):
        return self.env["hr.attendance"].search(
            [("employee_id", "=", (employee or self.employee).id)], order="check_in"
        )

    def _story(self, employee=None):
        """What the attendance of a person says, in the terms of the day."""
        return [
            (s.check_in, s.check_out, s.forgotten_badge) for s in self._stays(employee)
        ]

    def _machine_stay(self, start, stop=False, employee=None, zone=None):
        """A record the machinery made before this rule - overlaps included."""
        return (
            self.env["hr.attendance"]
            .with_context(no_validity_check=True)
            .create(
                {
                    "employee_id": (employee or self.employee).id,
                    "check_in": start,
                    "check_out": stop,
                    "in_zone_id": zone.id if zone else False,
                    "in_mode": "rfid",
                }
            )
        )

    def _rebuild(self, employee=None):
        (employee or self.employee).recalc_attendance(
            fields.Date.to_date(self.monday) - timedelta(days=1),
            fields.Date.to_date(self.wednesday) + timedelta(days=1),
        )

    def _assert_the_doors_tell_one_story(self, employee=None):
        """Same passages, same days, whichever machine reads them.

        And the same answer on every passage, not only on the records.
        """
        employee = employee or self.employee
        live = self._story(employee)
        passages = self.env["hr.rfid.event.user"].search(
            [("employee_id", "=", employee.id)], order="event_time"
        )
        live_verdicts = [(p.in_or_out, p.no_attendance_reason) for p in passages]

        self._rebuild(employee)

        self.assertEqual(self._story(employee), live)
        self.assertEqual(
            [(p.in_or_out, p.no_attendance_reason) for p in passages], live_verdicts
        )

    def _typed_stay(self, start, stop):
        """An operator enters a stay through the form, with every check on."""
        return self.env["hr.attendance"].create(
            {"employee_id": self.employee.id, "check_in": start, "check_out": stop}
        )

    def _with_a_card_and_anti_passback(self):
        self.door.with_context(no_hardware_commands=True).apb_mode = True
        return (
            self.env["hr.rfid.card"]
            .with_context(no_hardware_commands=True)
            .create(
                {
                    "number": "0012345678",
                    "employee_id": self.employee.id,
                    "company_id": self.company.id,
                }
            )
        )


@tagged("post_install", "-at_install", "rfid_attendance_zone")
class TestTheLivePassage(ForgottenBadgeCase):
    def test_the_next_mornings_entry_begins_a_new_day(self):
        """The worker's Tuesday stands on its own, whatever Monday forgot.

        In on Monday at eight, no badge-out, in on Tuesday at eight, out at
        half past four. Monday is credited its working day and can be found as
        a forgotten badge; Tuesday holds what Tuesday held.
        """
        self._in(self.at(self.monday, 8))
        tuesday_in = self._in(self.at(self.tuesday, 8))
        self._out(self.at(self.tuesday, 16.5))

        self.assertEqual(
            self._story(),
            [
                (self.at(self.monday, 8), self.at(self.monday, 17), True),
                (self.at(self.tuesday, 8), self.at(self.tuesday, 16.5), False),
            ],
        )
        self.assertEqual(
            self._stays()[0].out_mode,
            "auto_check_out",
            "Monday reads as closed by the system, not by a badge",
        )
        self.assertEqual(
            tuesday_in.in_or_out, "in", "and Tuesday's entry is that day's check-in"
        )
        self.assertFalse(tuesday_in.no_attendance_reason)

    def test_coming_back_the_same_day_changes_nothing(self):
        """NEGATIVE: out for lunch without a badge, back through the door.

        Well inside the day: the person is simply inside, as the passage says.
        """
        self._in(self.at(self.monday, 8))
        back = self._in(self.at(self.monday, 12.5))

        self.assertEqual(self._story(), [(self.at(self.monday, 8), False, False)])
        self.assertEqual(back.no_attendance_reason, "already_inside")

    def test_the_limit_is_the_companys_to_the_minute(self):
        """Ten hours is still the day; the first minute past it is not."""
        self._in(self.at(self.monday, 8))

        at_the_limit = self._in(self.at(self.monday, 18))
        self.assertEqual(at_the_limit.no_attendance_reason, "already_inside")
        self.assertEqual(len(self._stays()), 1)

        past_it = self._in(self.monday + timedelta(hours=18, minutes=1))
        self.assertEqual(past_it.in_or_out, "in")
        self.assertEqual(len(self._stays()), 2)

    def test_a_company_with_a_penalty_takes_it_off(self):
        """Nine hours of day less the two the company takes off."""
        self.company.write(
            {"forgotten_badge_policy": "penalty", "forgotten_badge_penalty_hours": 2.0}
        )
        self._in(self.at(self.monday, 8))
        self._in(self.at(self.tuesday, 8))

        self.assertEqual(
            self._story(),
            [
                (self.at(self.monday, 8), self.at(self.monday, 15), True),
                (self.at(self.tuesday, 8), False, False),
            ],
        )

    def test_a_company_that_counts_nothing_counts_nothing(self):
        """Monday is worth no hours and can be found; Tuesday still counts.

        The setting says somebody has to enter the real hours by hand. It does
        not say the person stops being counted until they do.
        """
        self.company.write({"forgotten_badge_policy": "ignore"})
        self._in(self.at(self.monday, 8))
        self._in(self.at(self.tuesday, 8))

        monday, tuesday = self._stays()
        self.assertEqual(monday.check_out, monday.check_in)
        self.assertEqual(monday.worked_hours, 0.0, "no working time at all")
        self.assertTrue(monday.forgotten_badge, "and marked, or nobody finds it")
        self.assertEqual(monday.out_mode, "auto_check_out")
        self.assertFalse(tuesday.check_out)

    def test_a_penalty_larger_than_the_day_counts_nothing_too(self):
        """Boundary: nothing left to credit is not a reason to stay open."""
        self.company.write(
            {"forgotten_badge_policy": "penalty", "forgotten_badge_penalty_hours": 12.0}
        )
        self._in(self.at(self.monday, 8))
        self._in(self.at(self.tuesday, 8))

        monday, tuesday = self._stays()
        self.assertEqual(monday.check_out, monday.check_in)
        self.assertTrue(monday.forgotten_badge)
        self.assertFalse(tuesday.check_out)

    def test_with_the_setting_off_nothing_is_settled(self):
        """NEGATIVE: a company that did not ask has no limit to apply."""
        self.company.auto_check_out = False
        self._in(self.at(self.monday, 8))
        tuesday_in = self._in(self.at(self.tuesday, 8))

        self.assertEqual(self._story(), [(self.at(self.monday, 8), False, False)])
        self.assertEqual(tuesday_in.no_attendance_reason, "already_inside")

    def test_a_small_tolerance_does_not_make_a_normal_day_forgotten(self):
        """With no tolerance, the day still lasts until its own end.

        Eight hours of work and a break make nine. Half past four is inside
        the day, and half past five is past it, credited to five.
        """
        self.company.auto_check_out_tolerance = 0.0
        self._in(self.at(self.monday, 8))

        inside = self._in(self.at(self.monday, 16.5))
        self.assertEqual(inside.no_attendance_reason, "already_inside")

        self._in(self.at(self.monday, 17.5))
        monday, evening = self._stays()
        self.assertEqual(monday.check_out, self.at(self.monday, 17))
        (monday | evening)._check_validity()

    def test_the_second_stay_of_a_day_gets_what_is_left_of_it(self):
        """Back from lunch, the day is not starting over.

        Eight to twelve badged, back at one, forgot. The day is worth eight
        hours, so the afternoon is credited until five, not until ten at night.
        """
        self._in(self.at(self.monday, 8))
        self._out(self.at(self.monday, 12))
        self._in(self.at(self.monday, 13))
        self._in(self.at(self.tuesday, 8))

        morning, afternoon, tuesday = self._stays()
        self.assertEqual(afternoon.check_out, self.at(self.monday, 17))
        self.assertEqual(morning.worked_hours + afternoon.worked_hours, 8.0)
        self.assertFalse(tuesday.check_out)

    def test_the_second_stay_is_judged_with_the_first(self):
        """Core's own measure: the limit is for the day, not for one stay.

        Four hours in the morning leave six before the limit. Half past seven
        in the evening is past it, though that stay alone is only six and a half.
        """
        self._in(self.at(self.monday, 8))
        self._out(self.at(self.monday, 12))
        self._in(self.at(self.monday, 13))

        inside = self._in(self.at(self.monday, 18.5))
        self.assertEqual(inside.no_attendance_reason, "already_inside")

        self._in(self.at(self.monday, 19.5))
        self.assertEqual(self._stays()[1].check_out, self.at(self.monday, 17))

    def test_a_day_that_is_already_used_up_gets_nothing_more(self):
        """Boundary: ten hours badged, back in the evening, forgot."""
        self._in(self.at(self.monday, 7))
        self._out(self.at(self.monday, 17))
        self._in(self.at(self.monday, 18))
        self._in(self.at(self.tuesday, 8))

        evening = self._stays()[1]
        self.assertEqual(evening.check_out, evening.check_in)
        self.assertTrue(evening.forgotten_badge)

    def test_every_forgotten_stay_is_settled_not_only_the_newest(self):
        """Old data can hold more than one open stay for a person."""
        self._machine_stay(self.at(self.monday, 8))
        self._machine_stay(self.at(self.tuesday, 8))
        self._in(self.at(self.wednesday, 8))

        self.assertEqual(
            self._story(),
            [
                (self.at(self.monday, 8), self.at(self.monday, 17), True),
                (self.at(self.tuesday, 8), self.at(self.tuesday, 17), True),
                (self.at(self.wednesday, 8), False, False),
            ],
        )

    def test_the_person_stays_inside_the_zone_and_the_doors_are_left_alone(self):
        """The entry must not look like the person left.

        Leaving takes them off the zone's list and queues anti-passback
        commands to the controllers. Nobody left here.
        """
        self._with_a_card_and_anti_passback()
        self._in(self.at(self.monday, 8))
        self.assertIn(self.employee, self.zone.employee_ids)

        door_class = type(self.env["hr.rfid.door"])
        with patch.object(door_class, "change_apb_flag") as flag:
            self._in(self.at(self.tuesday, 8))

        flag.assert_not_called()
        self.assertIn(self.employee, self.zone.employee_ids)

    @mute_logger(MULTI_RFID_LOG)
    def test_old_data_never_refuses_a_door_passage(self):
        """The door opened, so the passage is recorded, whatever the data says.

        A stay that cannot be settled leaves things exactly as they were. The
        failure is the one measured on a customer database: core's overtime
        engine raises this on a day with overlapping stays.
        """
        stuck = self._machine_stay(self.at(self.monday, 8))

        def refuse(*_args, **_kwargs):
            raise ValueError("Expected singleton: hr.attendance(1, 2)")

        with patch.object(type(self.env["hr.attendance"]), "_update_overtime", refuse):
            entry = self._in(self.at(self.tuesday, 8))

        self.assertTrue(entry.exists())
        self.assertEqual(entry.no_attendance_reason, "already_inside")
        self.assertFalse(stuck.check_out, "the failed write left nothing behind")
        self.assertFalse(stuck.forgotten_badge)

    def test_a_write_conflict_is_left_for_odoo_to_retry(self):
        """A lost race is not a verdict on the data.

        Absorbed here, the entry would be recorded with no attendance behind
        it, while the task that won the race closes Monday: Tuesday would be
        lost. Odoo replays the request when the error reaches it.
        """
        self._machine_stay(self.at(self.monday, 8))

        def lose_the_race(*_args, **_kwargs):
            raise errors.SerializationFailure()

        with (
            patch.object(
                type(self.env["hr.attendance"]), "_update_overtime", lose_the_race
            ),
            self.assertRaises(errors.SerializationFailure),
        ):
            self._in(self.at(self.tuesday, 8))

    def test_a_late_entry_inside_a_closed_stay_is_still_recorded(self):
        """An offline controller delivers yesterday's passage today.

        Core's overlap check would refuse the record it opens. A door passage
        is never refused.
        """
        self._typed_stay(self.at(self.monday, 8), self.at(self.monday, 17))

        late = self._in(self.at(self.monday, 10))

        self.assertTrue(late.exists())


@tagged("post_install", "-at_install", "rfid_attendance_zone")
class TestTheRebuild(ForgottenBadgeCase):
    def _walk_the_week(self):
        self._in(self.at(self.monday, 8))
        self._in(self.at(self.tuesday, 8))
        self._out(self.at(self.tuesday, 12))
        self._in(self.at(self.tuesday, 13))
        self._in(self.at(self.wednesday, 8))
        self._in(self.at(self.wednesday, 12.5))
        self._out(self.at(self.wednesday, 17))

    def test_the_rebuild_tells_the_same_story_as_the_doors_did(self):
        self._walk_the_week()
        self._assert_the_doors_tell_one_story()
        self.assertEqual(self._stays()[0].out_mode, "auto_check_out")

    def test_the_same_story_with_a_penalty(self):
        self.company.write(
            {"forgotten_badge_policy": "penalty", "forgotten_badge_penalty_hours": 2.0}
        )
        self._walk_the_week()
        self._assert_the_doors_tell_one_story()

    def test_the_same_story_when_nothing_is_counted(self):
        self.company.write({"forgotten_badge_policy": "ignore"})
        self._walk_the_week()
        self._assert_the_doors_tell_one_story()
        self.assertEqual(self._stays()[0].worked_hours, 0.0)

    def test_the_same_story_in_sofia_on_a_day_off(self):
        """A real zone and a day with no schedule reach the rebuild's judgement.

        Saturday evening on a weekday schedule: the calendar's ordinary day
        stands in for the one nobody planned, and Sunday's entry is past it.
        """
        calendar = self.env["resource.calendar"].create(
            {
                "name": "Weekdays Sofia",
                "company_id": self.company.id,
                "tz": "Europe/Sofia",
                "hours_per_day": 8.0,
                "attendance_ids": [
                    Command.create(
                        {
                            "name": "%s %s" % (day, period),
                            "dayofweek": day,
                            "hour_from": start,
                            "hour_to": stop,
                            "day_period": period,
                        }
                    )
                    for day in "01234"
                    for period, start, stop in (
                        ("morning", 8.0, 12.0),
                        ("lunch", 12.0, 13.0),
                        ("afternoon", 13.0, 17.0),
                    )
                ],
            }
        )
        self.employee.write({"tz": "Europe/Sofia", "resource_calendar_id": calendar.id})
        today = fields.Date.today()
        saturday = today - timedelta(days=(today.weekday() - 5) % 7 + 7)
        self.monday = fields.Datetime.to_datetime(saturday)
        self.wednesday = self.monday + timedelta(days=2)
        self._in(in_sofia(saturday, 18))
        self._in(in_sofia(saturday + timedelta(days=1), 18))

        first = self._stays()[0]
        self.assertEqual(
            first.check_out,
            in_sofia(saturday + timedelta(days=1), 2),
            "the ordinary working day, eight hours from six o'clock",
        )
        self._assert_the_doors_tell_one_story()

    def test_a_zone_that_moves_the_check_in_settles_all_the_same(self):
        """The limit comes first, whatever the zone does with a second entry."""
        self.zone.overwrite_check_in = True
        self._in(self.at(self.monday, 8))
        self._in(self.at(self.tuesday, 8))

        self.assertEqual(
            self._story(),
            [
                (self.at(self.monday, 8), self.at(self.monday, 17), True),
                (self.at(self.tuesday, 8), False, False),
            ],
        )

        self._rebuild()

        self.assertEqual(
            self._story(),
            [
                (self.at(self.monday, 8), self.at(self.monday, 17), True),
                (self.at(self.tuesday, 8), False, False),
            ],
        )

    def test_a_stay_across_days_comes_back_as_its_days(self):
        """What the rebuild is for: the record across two days comes apart.

        The old machinery left one record from Monday to Tuesday evening. The
        doors still hold what happened, and the rebuild puts each day back.
        """
        self._in(self.at(self.monday, 8))
        self._in(self.at(self.tuesday, 8))
        self._out(self.at(self.tuesday, 16.5))
        self._stays().unlink()
        self._machine_stay(self.at(self.monday, 8), self.at(self.tuesday, 16.5))

        self._rebuild()

        self.assertEqual(
            self._story(),
            [
                (self.at(self.monday, 8), self.at(self.monday, 17), True),
                (self.at(self.tuesday, 8), self.at(self.tuesday, 16.5), False),
            ],
        )

    def test_rebuilding_twice_changes_nothing(self):
        """The operator may press the button as often as they like."""
        self._walk_the_week()
        self._rebuild()
        first = self._story()

        self._rebuild()

        self.assertEqual(self._story(), first)

    def test_a_record_typed_in_by_hand_stands(self):
        """NEGATIVE: the operator's word stands, and nothing is written around it.

        They typed 15:00-16:00 on Monday. The entry that morning has no stay
        of its own beside it, the same answer as a pair of passages around
        their record.
        """
        monday_in = self._in(self.at(self.monday, 8))
        self._in(self.at(self.tuesday, 8))
        self._stays().unlink()
        typed = self._typed_stay(self.at(self.monday, 15), self.at(self.monday, 16))

        self._rebuild()

        self.assertEqual(
            self._story(),
            [
                (self.at(self.monday, 15), self.at(self.monday, 16), False),
                (self.at(self.tuesday, 8), False, False),
            ],
        )
        self.assertEqual(typed.in_mode, "manual")
        self.assertEqual(monday_in.no_attendance_reason, "manual_record")

    def test_with_the_setting_off_the_rebuild_settles_nothing(self):
        """NEGATIVE: the rebuild applies no limit the company did not set."""
        self.company.auto_check_out = False
        self._in(self.at(self.monday, 8))
        self._in(self.at(self.tuesday, 8))
        self._out(self.at(self.tuesday, 16.5))

        self._rebuild()

        self.assertEqual(
            self._story(),
            [(self.at(self.monday, 8), self.at(self.tuesday, 16.5), False)],
        )

    def test_a_failure_is_reported_on_the_person_and_undoes_them(self):
        """A rebuild never reports a person as done over a step that failed.

        Their records stay as they were, and the screen says something went
        wrong for them.
        """
        self._in(self.at(self.monday, 8))
        self._in(self.at(self.tuesday, 8))
        before = self._story()
        run = self.env["hr.attendance.recalc.run"].create(
            {
                "employee_ids": [Command.set(self.employee.ids)],
                "date_from": fields.Date.to_date(self.monday),
                "date_to": fields.Date.to_date(self.wednesday),
            }
        )

        def refuse(*_args, **_kwargs):
            raise ValueError("Expected singleton: hr.attendance(1, 2)")

        with patch.object(
            type(self.env["hr.attendance"]), "autoclose_attendance", refuse
        ):
            with mute_logger(
                "odoo.addons.hr_attendance_multi_rfid.models.attendance_recalc_run"
            ):
                run._run_one_employee(
                    self.employee, self.employee._recalc_attendance_context()
                )

        self.assertEqual(self._story(), before)
        self.assertEqual(
            self.env["hr.attendance.recalc.log"]
            .search([("run_id", "=", run.id)])
            .status,
            "error",
        )


@tagged("post_install", "-at_install", "rfid_attendance_zone")
class TestTheScheduledTask(ForgottenBadgeCase):
    def test_the_task_credits_what_the_company_set(self):
        """The Forgotten Badge setting is what a forgotten badge is worth.

        The company said to credit the scheduled day: eight hours and the mark,
        not the working day plus the tolerance, which is what core's own rule
        would record.
        """
        no_break = self._every_day_calendar(
            "New Entry 8-16", (("morning", 8.0, 16.0),), hours_per_day=8.0
        )
        self.employee.resource_calendar_id = no_break
        stay = self._machine_stay(self.at(self.monday, 8))

        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(stay.check_out, self.at(self.monday, 16))
        self.assertTrue(stay.forgotten_badge)

    def test_a_settled_day_needs_no_correction_note(self):
        """The task settles the record once, not twice.

        Closed one way and then moved back, it would carry a note about a
        check-out nobody ever saw.
        """
        stay = self._machine_stay(self.at(self.monday, 8))
        messages = stay.message_ids

        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(stay.check_out, self.at(self.monday, 17))
        self.assertFalse(
            (stay.message_ids - messages).filtered("body"),
            "nothing was moved: the stay was simply closed",
        )

    def test_counting_nothing_survives_the_task(self):
        """The stay is worth no hours, as the company set, and can be found."""
        self.company.write({"forgotten_badge_policy": "ignore"})
        stay = self._machine_stay(self.at(self.monday, 8))

        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(stay.check_out, stay.check_in)
        self.assertEqual(stay.worked_hours, 0.0)
        self.assertTrue(stay.forgotten_badge)

    def test_a_penalty_larger_than_the_day_survives_the_task(self):
        """The same when the penalty leaves nothing: marked, and worth no hours."""
        self.company.write(
            {"forgotten_badge_policy": "penalty", "forgotten_badge_penalty_hours": 12.0}
        )
        stay = self._machine_stay(self.at(self.monday, 8))

        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(stay.check_out, stay.check_in)
        self.assertTrue(stay.forgotten_badge)

    @mute_logger(MULTI_RFID_LOG)
    def test_one_stay_it_cannot_close_costs_nobody_else(self):
        """The reported defect: the task failed on every run, for everybody.

        One person's stay cannot be closed. Another person's forgotten stay is
        settled all the same, and the task finishes.
        """
        start = self.at(self.monday, 8)
        stuck = self._machine_stay(start)
        other = self._person("Other Worker")
        fine = self._machine_stay(start, employee=other)
        attendance = type(self.env["hr.attendance"])
        settle = attendance.autoclose_attendance

        def refuse_one(record):
            if record == stuck:
                raise ValueError("Expected singleton: hr.attendance(1, 2)")
            return settle(record)

        with patch.object(attendance, "autoclose_attendance", refuse_one):
            self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(fine.check_out, self.at(self.monday, 17))
        self.assertFalse(stuck.check_out, "this one stays for a person to correct")
        self.assertTrue(stuck.forgotten_badge, "and can be found")

    def test_a_write_conflict_is_not_taken_for_bad_data(self):
        """NEGATIVE: a lost race marks nothing and is left for the next run."""
        stay = self._machine_stay(self.at(self.monday, 8))

        def lose_the_race(*_args, **_kwargs):
            raise errors.SerializationFailure()

        with (
            patch.object(
                type(self.env["hr.attendance"]), "_update_overtime", lose_the_race
            ),
            self.assertRaises(errors.SerializationFailure),
        ):
            self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertFalse(stay.forgotten_badge)

    def _old_overlap(self, stay, start, stop):
        """Old data as it is in the table. Core's overtime engine refuses to
        write such a record, so it can only be put there directly."""
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE hr_attendance SET check_in = %s, check_out = %s WHERE id = %s",
            (start, stop, stay.id),
        )
        self.env.invalidate_all()

    def test_old_overlaps_are_settled_whichever_comes_first(self):
        """Old data, written while the overlap check did not run.

        An open stay inside an over-long closed one, and two over-long stays
        lying across each other. All of them are put right, and the result
        passes the check.
        """
        long_one = self._machine_stay(self.at(self.monday, 8), self.at(self.monday, 9))
        open_inside = self._machine_stay(self.at(self.tuesday, 8))
        other = self._person("Other Worker")
        first = self._machine_stay(
            self.at(self.monday, 8), self.at(self.monday, 9), other
        )
        second = self._machine_stay(
            self.at(self.tuesday, 8), self.at(self.tuesday, 9), other
        )
        self._old_overlap(long_one, self.at(self.monday, 8), self.at(self.wednesday, 8))
        self._old_overlap(first, self.at(self.monday, 8), self.at(self.wednesday, 8))
        self._old_overlap(second, self.at(self.tuesday, 8), self.at(self.wednesday, 9))

        self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertEqual(long_one.check_out, self.at(self.monday, 17))
        self.assertEqual(open_inside.check_out, self.at(self.tuesday, 17))
        self.assertEqual(first.check_out, self.at(self.monday, 17))
        self.assertEqual(second.check_out, self.at(self.tuesday, 17))
        (long_one | open_inside | first | second)._check_validity()

    def test_closing_an_old_stay_leaves_the_person_still_inside_alone(self):
        """Settling Monday says nothing about the person at work today.

        Their stay of today stays open, they stay on the zone's list, and no
        anti-passback command for their card goes to the doors. On a real
        database the task settles other people as well, and those are not
        this test's business.
        """
        card = self._with_a_card_and_anti_passback()
        monday = self._machine_stay(self.at(self.monday, 8), zone=self.zone)
        today = self._machine_stay(
            fields.Datetime.now() - timedelta(hours=1), zone=self.zone
        )
        self.zone.employee_ids |= self.employee

        door_class = type(self.env["hr.rfid.door"])
        with patch.object(door_class, "change_apb_flag") as flag:
            self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertEqual(monday.check_out, self.at(self.monday, 17))
        self.assertFalse(today.check_out, "they are still at work")
        self.assertIn(self.employee, self.zone.employee_ids)
        self.assertNotIn(card, [call.args[0] for call in flag.call_args_list])

    def test_an_open_stay_behind_a_later_one_ends_where_that_begins(self):
        """Old data: open since Monday morning, closed stays later that day.

        Core refuses to close the open one past the later stay's start. It is
        settled up to the NEAREST one, and they no longer overlap.
        """
        morning = self._machine_stay(self.at(self.monday, 8), zone=self.zone)
        noon = self._machine_stay(self.at(self.monday, 12), self.at(self.monday, 13))
        evening = self._machine_stay(self.at(self.monday, 14), self.at(self.monday, 15))

        self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertEqual(morning.check_out, noon.check_in)
        self.assertTrue(morning.forgotten_badge)
        (morning | noon | evening)._check_validity()

    def test_an_open_stay_inside_a_typed_day_ends_without_hours(self):
        """The operator's record already holds the day.

        A forgotten entry inside it has nothing left to credit, and core's
        overlap check would refuse any end for it. Left open, it would stay
        open for good.
        """
        typed = self._typed_stay(self.at(self.monday, 8), self.at(self.monday, 20))
        inside = self._machine_stay(self.at(self.monday, 19))

        self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertEqual(inside.check_out, inside.check_in)
        self.assertTrue(inside.forgotten_badge)
        self.assertEqual(typed.check_out, self.at(self.monday, 20))

    def test_a_colleagues_stay_does_not_cut_a_credited_day(self):
        """NEGATIVE: only the person's own next stay ends their day."""
        stay = self._machine_stay(self.at(self.monday, 8))
        self._machine_stay(
            self.at(self.monday, 12),
            self.at(self.monday, 13),
            self._person("Colleague"),
        )

        self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertEqual(stay.check_out, self.at(self.monday, 17))

    def test_a_closed_stay_never_moves_later(self):
        """NEGATIVE: settling can only shorten a stay, never invent hours."""
        self.company.auto_check_out_tolerance = 0.0
        stay = self._machine_stay(self.at(self.monday, 8), self.at(self.monday, 17.5))
        stay.in_mode = "rfid"
        self.employee.resource_calendar_id.attendance_ids.filtered(
            lambda line: line.day_period == "afternoon"
        ).hour_to = 18.0

        self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertLessEqual(stay.check_out, self.at(self.monday, 17.5))

    def test_a_long_stay_on_a_day_already_used_up_keeps_no_hours(self):
        """Ten hours badged, then a stay closed two days later.

        Nothing of the day is left to credit, and the record must not go on
        lending the person two days. The chatter keeps what it used to say.
        """
        self._machine_stay(self.at(self.monday, 7), self.at(self.monday, 17))
        long_one = self._machine_stay(
            self.at(self.monday, 18), self.at(self.wednesday, 8)
        )
        messages = long_one.message_ids

        self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertEqual(long_one.check_out, long_one.check_in)
        self.assertTrue(long_one.forgotten_badge)
        self.assertTrue((long_one.message_ids - messages).filtered("body"))

    def test_a_closed_stay_under_count_nothing_keeps_its_times(self):
        """NEGATIVE: the setting says nothing is counted, not that the times change.

        The record stays as it was, and only the mark says the day reads as
        unworked until somebody enters the real hours.
        """
        self.company.write({"forgotten_badge_policy": "ignore"})
        stay = self._machine_stay(self.at(self.monday, 8), self.at(self.tuesday, 12))

        self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertEqual(stay.check_out, self.at(self.tuesday, 12))
        self.assertTrue(stay.forgotten_badge)

    def test_the_task_stops_when_its_time_is_up_and_carries_on_next_run(self):
        """A long first run is left to the scheduler, not cut off by it.

        The oldest stay is settled and kept, the time is up, and the next run
        finds only what is left.
        """
        first = self._machine_stay(self.at(self.monday, 8))
        second = self._machine_stay(self.at(self.tuesday, 8))
        in_the_task = self.env["hr.attendance"].with_context(ir_cron_progress_id=1)
        cron_class = type(self.env["ir.cron"])

        with patch.object(cron_class, "_commit_progress", return_value=0.0):
            in_the_task.check_for_incomplete_attendances()
        self.assertEqual(
            first.check_out, self.at(self.monday, 17), "the oldest goes first"
        )
        self.assertFalse(second.check_out, "the time was up")

        with patch.object(cron_class, "_commit_progress", return_value=60.0):
            in_the_task.check_for_incomplete_attendances()
        self.assertEqual(second.check_out, self.at(self.tuesday, 17))

    def test_a_forgotten_night_stops_at_core_absence_mark(self):
        """Core's overtime engine refuses a record across its absence mark.

        Credited past it, the stay could never be closed. It ends at the mark.
        """
        stay = self._machine_stay(self.at(self.monday, 22))
        mark = self._machine_stay(self.tuesday, self.tuesday + timedelta(seconds=1))
        mark.in_mode = "technical"

        self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertEqual(stay.check_out, self.tuesday)

    def test_a_forgotten_day_the_task_and_the_next_morning(self):
        """The whole week as it happens: forgot, the task ran, next morning, out."""
        self._in(self.at(self.monday, 8))
        self.env["hr.attendance"].check_for_incomplete_attendances()
        self.assertNotIn(
            self.employee,
            self.zone.employee_ids,
            "settled: the zone no longer shows them inside",
        )

        self._in(self.at(self.tuesday, 8))
        self._out(self.at(self.tuesday, 16.5))

        self.assertEqual(
            self._story(),
            [
                (self.at(self.monday, 8), self.at(self.monday, 17), True),
                (self.at(self.tuesday, 8), self.at(self.tuesday, 16.5), False),
            ],
        )

    def test_the_task_judges_a_second_stay_with_the_first(self):
        """Core's measure, record by record: the afternoon ends with the day."""
        self._machine_stay(self.at(self.monday, 8), self.at(self.monday, 12))
        afternoon = self._machine_stay(self.at(self.monday, 13))

        self.env["hr.attendance"].with_context(
            attendance_calc_time=self.at(self.monday, 18.5)
        ).check_for_incomplete_attendances()
        self.assertFalse(afternoon.check_out, "nine and a half hours: still the day")

        self.env["hr.attendance"].with_context(
            attendance_calc_time=self.at(self.monday, 19.5)
        ).check_for_incomplete_attendances()
        self.assertEqual(afternoon.check_out, self.at(self.monday, 17))

    def test_a_person_at_work_on_a_day_off_is_left_alone(self):
        """NEGATIVE: a Sunday shift is not closed while the person is there.

        Core's own rule has no schedule to go by on a day off and closes after
        the bare tolerance: three hours into the shift, at noon, with the person
        still in the building. Owner's decision of 05.11.2026: the task runs
        without it. The ordinary working day stands in, and only a stay past
        that is settled.
        """
        weekdays = self.env["resource.calendar"].create(
            {
                "name": "Weekdays",
                "company_id": self.company.id,
                "tz": "UTC",
                "hours_per_day": 8.0,
                "attendance_ids": [
                    Command.create(
                        {
                            "name": day,
                            "dayofweek": day,
                            "hour_from": 8.0,
                            "hour_to": 16.0,
                            "day_period": "morning",
                        }
                    )
                    for day in "01234"
                ],
            }
        )
        self.employee.resource_calendar_id = weekdays
        sunday = fields.Datetime.to_datetime("2026-11-08")
        stay = self._machine_stay(self.at(sunday, 10))

        with freeze_time(self.at(sunday, 13)):
            self.env["hr.attendance"]._cron_auto_check_out()
        self.assertFalse(stay.check_out, "three hours in, still at work")

        with freeze_time(self.at(sunday, 20.5)):
            self.env["hr.attendance"]._cron_auto_check_out()
        self.assertEqual(stay.check_out, self.at(sunday, 18))
        self.assertEqual(stay.in_mode, "rfid", "a settled stay is still the machine's")


@tagged("post_install", "-at_install", "rfid_attendance_zone")
class TestTheOperatorsWord(ForgottenBadgeCase):
    def test_the_real_hours_replace_the_guess(self):
        """The remedy the setting promises: the operator enters the real hours.

        The person stayed until half past seven. The stay stops reading as
        forgotten, and the task does not move it back.
        """
        self._in(self.at(self.monday, 8))
        self._in(self.at(self.tuesday, 8))
        monday = self._stays()[0]
        self.assertTrue(monday.forgotten_badge)

        monday.check_out = self.at(self.monday, 19.5)

        self.assertFalse(monday.forgotten_badge)
        self.assertEqual(monday.in_mode, "manual")
        self.env["hr.attendance"].check_for_incomplete_attendances()
        self.assertEqual(monday.check_out, self.at(self.monday, 19.5))

    def test_the_real_hours_count_where_nothing_was_credited(self):
        """The same under Count nothing: the day is worth what they entered."""
        self.company.write({"forgotten_badge_policy": "ignore"})
        self._in(self.at(self.monday, 8))
        self._in(self.at(self.tuesday, 8))
        monday = self._stays()[0]

        monday.check_out = self.at(self.monday, 17)

        self.assertEqual(monday.worked_hours, 8.0)
        self.assertFalse(monday.stay_is_not_credible())

    def test_a_long_day_entered_by_hand_is_left_alone(self):
        """NEGATIVE: however long, a check-out an operator typed is their word."""
        typed = self._typed_stay(self.at(self.monday, 8), self.at(self.monday, 22))

        self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertEqual(typed.check_out, self.at(self.monday, 22))
        self.assertFalse(typed.forgotten_badge)

    def test_a_stay_left_open_by_hand_is_still_settled(self):
        """NEGATIVE: an open record states nothing about when the person left."""
        stay = self.env["hr.attendance"].create(
            {"employee_id": self.employee.id, "check_in": self.at(self.monday, 8)}
        )

        self.env["hr.attendance"].check_for_incomplete_attendances()

        self.assertEqual(stay.check_out, self.at(self.monday, 17))


@tagged("post_install", "-at_install", "rfid_attendance_zone")
class TestTheOverlapCheck(ForgottenBadgeCase):
    def test_an_operator_cannot_type_an_overlap(self):
        """Refused with core's own message, not a server error later.

        An overlap breaks core's overtime engine for the whole day, so it is
        stopped where it is typed.
        """
        self._typed_stay(self.at(self.monday, 8), self.at(self.monday, 16))

        with self.assertRaises(ValidationError):
            self._typed_stay(self.at(self.monday, 9), self.at(self.monday, 10))

    def test_an_operator_cannot_stretch_a_stay_over_the_next(self):
        """Editing is checked the same way as creating."""
        first = self._typed_stay(self.at(self.monday, 8), self.at(self.monday, 12))
        self._typed_stay(self.at(self.monday, 13), self.at(self.monday, 16))

        with self.assertRaises(ValidationError):
            first.check_out = self.at(self.monday, 14)

    def test_an_operator_cannot_move_a_check_in_or_a_person_into_an_overlap(self):
        """All three fields the check depends on trigger it."""
        self._typed_stay(self.at(self.monday, 8), self.at(self.monday, 12))
        later = self._typed_stay(self.at(self.monday, 13), self.at(self.monday, 16))
        with self.assertRaises(ValidationError):
            later.check_in = self.at(self.monday, 11)

        other = self._person("Other Worker")
        theirs = self.env["hr.attendance"].create(
            {
                "employee_id": other.id,
                "check_in": self.at(self.monday, 9),
                "check_out": self.at(self.monday, 10),
            }
        )
        with self.assertRaises(ValidationError):
            theirs.employee_id = self.employee

    def test_an_operator_can_still_correct_a_stay(self):
        """NEGATIVE: the check refuses overlaps and nothing else."""
        first = self._typed_stay(self.at(self.monday, 8), self.at(self.monday, 12))
        self._typed_stay(self.at(self.monday, 13), self.at(self.monday, 16))

        first.check_out = self.at(self.monday, 13)

        self.assertEqual(first.check_out, self.at(self.monday, 13))
