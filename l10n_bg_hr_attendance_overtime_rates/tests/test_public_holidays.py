# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
import importlib.util
from datetime import date, datetime, time
from unittest.mock import patch

from pytz import timezone, utc

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger
from odoo.tools.misc import file_path

SOFIA = timezone("Europe/Sofia")


@tagged("post_install", "-at_install", "l10n_bg_overtime", "bg_holidays")
class TestBgPublicHolidays(TransactionCase):
    """Bulgarian public-holiday generation + seeded legal rates."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # The holidays are for a company in Bulgaria, as the yearly cron
        # requires.
        cls.company.country_id = cls.env.ref("base.bg")
        # Ensure the company has a working calendar to attach holidays to.
        if not cls.company.resource_calendar_id:
            cls.company.resource_calendar_id = cls.env["resource.calendar"].create(
                {"name": "Test Cal", "company_id": cls.company.id}
            )
        cls.company.resource_calendar_id.tz = "Europe/Sofia"

    def test_seeded_legal_rates(self):
        """КТ чл. 262 multipliers are seeded and resolvable."""
        Rate = self.env["hr.legal.rate"]
        d = date(2026, 6, 1)
        self.assertEqual(Rate._get_rate("overtime_workday", d), 1.5)
        self.assertEqual(Rate._get_rate("overtime_weekend", d), 1.75)
        self.assertEqual(Rate._get_rate("overtime_holiday", d), 2.0)
        self.assertEqual(Rate._get_rate("night_supplement", d), 0.51)

    def test_night_supplement_dated_at_2026(self):
        """The statutory night supplement this module ships starts on its date.

        Asked of the module's OWN row rather than of the global lookup: any
        other module - or the customer - may hold a night rate of their own
        with an earlier date, and that is their business, not a fault in the
        figure shipped here.
        """
        rate = self.env.ref(
            "l10n_bg_hr_attendance_overtime_rates.rate_night_supplement_2026",
            raise_if_not_found=False,
        )
        self.assertTrue(rate, "The module must ship a night-supplement rate")
        self.assertEqual(rate.code, "night_supplement")
        self.assertEqual(rate.value, 0.51)
        self.assertEqual(rate.date_from, date(2026, 1, 1))

    # -- helpers ---------------------------------------------------------

    def _company_holidays(self, company=None):
        """The company's public holidays for everybody: no schedule, no person."""
        return self.env["resource.calendar.leaves"].search(
            [
                ("company_id", "=", (company or self.company).id),
                ("calendar_id", "=", False),
                ("resource_id", "=", False),
            ]
        )

    def _holidays_of_the_year(self, year):
        """Every official day the company holds for everybody that year.

        The question the payroll clerk asks is "is 3 March a holiday for us",
        never "did that one call create it". Asking the company keeps the test
        true on a database where the days are already there - which is every
        demo installation, and every customer who ran the generator once last
        year.
        """
        # The day of a holiday is the company's own day: its first moment is
        # stored in UTC, which in Sofia is the evening before.
        days = {
            utc.localize(leave.date_from).astimezone(SOFIA).date()
            for leave in self._company_holidays()
        }
        return {day for day in days if day.year == year}

    def _liberation_day(self, year):
        return self._company_holidays().filtered(
            lambda leave: leave.name == "Liberation Day"
            and utc.localize(leave.date_from).astimezone(SOFIA).date()
            == date(year, 3, 3)
        )

    def _assert_the_sofia_day(self, leave, year, who):
        self.assertEqual(
            len(leave), 1, "3 March %s must be held once, for everybody" % year
        )
        begins = utc.localize(leave.date_from).astimezone(SOFIA)
        ends = utc.localize(leave.date_to).astimezone(SOFIA)
        self.assertEqual(
            (begins.date(), begins.hour, begins.minute),
            (date(year, 3, 3), 0, 0),
            "the holiday begins at midnight in Sofia (run by %s)" % who,
        )
        self.assertEqual(
            (ends.date(), ends.hour, ends.minute),
            (date(year, 3, 3), 23, 59),
            "and ends at the last minute of that day there (run by %s)" % who,
        )

    def _schedule(self, name, company):
        """A Monday-to-Friday schedule of that company, 8 hours a day in Sofia."""
        return self.env["resource.calendar"].create(
            {
                "name": name,
                "company_id": company.id,
                "tz": "Europe/Sofia",
            }
        )

    def _employee(self, name, schedule):
        return self.env["hr.employee"].create(
            {
                "name": name,
                "company_id": schedule.company_id.id,
                "resource_calendar_id": schedule.id,
                "tz": "Europe/Sofia",
            }
        )

    def _owed_hours(self, employee, day):
        """Hours the person owes on that day of theirs, holidays deducted -
        what every daily figure and the time-off count read."""
        start = SOFIA.localize(datetime.combine(day, time.min))
        stop = SOFIA.localize(datetime.combine(day, time.max))
        return employee._get_work_days_data_batch(start, stop)[employee.id]["hours"]

    # -- the official days -----------------------------------------------

    def test_a_holiday_is_the_whole_day_where_the_company_works(self):
        """Liberation Day runs from midnight to midnight in Sofia.

        A worker on the night of 2 March is not on holiday, and one on the
        night of 4 March is not either: the holiday is the third, as the
        company lives it - whoever fills the year in: an HR officer in Sofia,
        one in another zone running it again, or the yearly cron, which runs
        with no zone at all.
        """
        # A year nobody has filled in yet, so the days are the ones made here.
        self.env.user.tz = "Europe/Sofia"
        self.company._generate_bg_public_holidays(2031)
        self._assert_the_sofia_day(
            self._liberation_day(2031), 2031, "an officer in Sofia"
        )
        held = len(self._company_holidays())

        # Run again from another zone: nothing is added and nothing moves.
        self.env.user.tz = "America/New_York"
        self.company._generate_bg_public_holidays(2031)
        self.assertEqual(
            len(self._company_holidays()),
            held,
            "a second run, from any zone, adds no day twice",
        )
        self._assert_the_sofia_day(self._liberation_day(2031), 2031, "a second officer")

        # The yearly cron, as the scheduler runs it: no user zone at all.
        # Next year may already be filled in on this database - by the demo,
        # or by another localisation module - and then the cron leaves it; so
        # what is asked is that 3 March is a holiday for everybody, once.
        root = self.env.ref("base.user_root")
        root.tz = False
        next_year = fields.Date.today().year + 1
        self.env["res.company"].with_user(root)._cron_generate_bg_public_holidays()
        noon = (
            SOFIA.localize(datetime(next_year, 3, 3, 12))
            .astimezone(utc)
            .replace(tzinfo=None)
        )
        held = self._company_holidays().filtered(
            lambda leave: leave.date_from <= noon <= leave.date_to
        )
        self.assertEqual(
            len(held), 1, "the cron holds 3 March %s for everybody, once" % next_year
        )
        if held.name == "Liberation Day":
            self._assert_the_sofia_day(held, next_year, "the cron")

    def test_generates_fixed_and_moving_holidays(self):
        """Fixed dates + Orthodox-Easter cluster, held for everybody."""
        self.company._generate_bg_public_holidays(2026)
        days = self._holidays_of_the_year(2026)
        # Fixed
        self.assertIn(date(2026, 3, 3), days, "Liberation Day")
        self.assertIn(date(2026, 5, 24), days, "Culture Day")
        self.assertIn(date(2026, 12, 25), days, "Christmas")
        # Moving - Orthodox Easter 2026 = Apr 12 -> Fri 10 / Sat 11 / Mon 13
        self.assertIn(date(2026, 4, 10), days, "Good Friday")
        self.assertIn(date(2026, 4, 11), days, "Holy Saturday")
        self.assertIn(date(2026, 4, 13), days, "Easter Monday")

    def test_generation_is_idempotent(self):
        """Running the generator again leaves the year as it was.

        Written against the company's days rather than the call's return
        value: on a database where the year is already filled in - a demo
        instance, or a customer who ran it last year - the first call
        legitimately creates nothing.
        """
        self.company._generate_bg_public_holidays(2026)
        after_first = self._holidays_of_the_year(2026)
        self.assertTrue(after_first, "The year must be filled in by now")

        self.company._generate_bg_public_holidays(2026)
        self.assertEqual(
            self._holidays_of_the_year(2026),
            after_first,
            "Re-run must not duplicate holidays",
        )

    def test_easter_differs_by_year(self):
        """Moving cluster tracks the year (regression vs hardcoded dates)."""
        self.company._generate_bg_public_holidays(2026)
        # Orthodox Easter 2027 = May 2 -> Good Friday Apr 30
        self.company._generate_bg_public_holidays(2027)
        days27 = self._holidays_of_the_year(2027)
        self.assertIn(date(2027, 4, 30), days27, "2027 Good Friday")
        self.assertNotIn(date(2026, 4, 10), days27, "must not reuse 2026 date")

    # -- who the days are for --------------------------------------------

    def test_a_person_on_another_schedule_gets_the_holiday(self):
        """Liberation Day is a day off for everybody in the company.

        The Labour Code gives the official days to every employee, not to the
        ones on the company's main schedule. A person on the shift schedule
        owes no hours on Monday 3 March 2031 - and owes the full day on the
        Tuesday after, so the zero is the holiday and not an empty schedule.
        """
        shifts = self._schedule("Shifts", self.company)
        person = self._employee("On shifts", shifts)
        self.assertEqual(
            self._owed_hours(person, date(2031, 3, 3)),
            8.0,
            "before the year is filled in, the Monday is a working day",
        )

        self.company._generate_bg_public_holidays(2031)

        self.assertEqual(
            self._owed_hours(person, date(2031, 3, 3)),
            0.0,
            "Liberation Day is not owed on the shift schedule either",
        )
        self.assertEqual(
            self._owed_hours(person, date(2031, 3, 4)),
            8.0,
            "the day after is an ordinary working day",
        )
        holidays = person._get_public_holidays(
            datetime(2031, 3, 2), datetime(2031, 3, 4)
        )
        self.assertIn(
            "Liberation Day",
            holidays.mapped("name"),
            "Time Off shows the holiday to the person on shifts",
        )

    def test_another_company_keeps_its_own_days(self):
        """A company abroad in the same database gets no Bulgarian holiday.

        Neither from the officer who fills in the Bulgarian company's year, nor
        from the yearly cron, although it keeps public holidays of its own.
        """
        abroad = self.env["res.company"].create(
            {"name": "Abroad", "country_id": self.env.ref("base.de").id}
        )
        schedule = self._schedule("Abroad week", abroad)
        abroad.resource_calendar_id = schedule
        person = self._employee("Abroad", schedule)
        self.env["resource.calendar.leaves"].with_company(abroad).create(
            {
                "name": "Own closing day",
                "company_id": abroad.id,
                "calendar_id": False,
                "resource_id": False,
                "date_from": datetime(2031, 8, 14, 22, 0),
                "date_to": datetime(2031, 8, 15, 21, 59, 59),
            }
        )

        self.company._generate_bg_public_holidays(2031)
        self.env["res.company"]._cron_generate_bg_public_holidays()

        self.assertEqual(
            self._owed_hours(person, date(2031, 3, 3)),
            8.0,
            "3 March is an ordinary day in the other company",
        )
        self.assertEqual(
            self._company_holidays(abroad).mapped("name"),
            ["Own closing day"],
            "the other company holds only its own day",
        )

    def test_a_day_already_held_for_one_schedule_does_not_stop_the_year(self):
        """A holiday the company already entered for one schedule stays.

        Core refuses two public holidays over the same hours of one company.
        The day already held is left as it is, and every other day of the year
        is still filled in.
        """
        shifts = self._schedule("Shifts", self.company)
        self.env["resource.calendar.leaves"].create(
            {
                "name": "Liberation Day, entered by hand",
                "company_id": self.company.id,
                "calendar_id": shifts.id,
                "resource_id": False,
                "date_from": SOFIA.localize(datetime(2032, 3, 3))
                .astimezone(utc)
                .replace(tzinfo=None),
                "date_to": SOFIA.localize(datetime(2032, 3, 3, 23, 59, 59))
                .astimezone(utc)
                .replace(tzinfo=None),
            }
        )

        self.company._generate_bg_public_holidays(2032)

        days = self._holidays_of_the_year(2032)
        self.assertNotIn(date(2032, 3, 3), days, "the day held by hand is not doubled")
        self.assertIn(date(2032, 9, 22), days, "the rest of the year is filled in")
        self.assertIn(date(2032, 12, 25), days, "to its end")

    # -- the days earlier versions made ----------------------------------

    def _old_holiday(self, name, day, schedule=None):
        """A holiday the way earlier versions made it: on the company's schedule,
        handed over by an officer in Sofia (core reads the bounds of a holiday
        tied to a schedule in the zone of the user who enters it)."""
        self.env.user.tz = "Europe/Sofia"
        return self.env["resource.calendar.leaves"].create(
            {
                "name": name,
                "company_id": self.company.id,
                "calendar_id": (schedule or self.company.resource_calendar_id).id,
                "resource_id": False,
                "date_from": SOFIA.localize(datetime.combine(day, time.min))
                .astimezone(utc)
                .replace(tzinfo=None),
                "date_to": SOFIA.localize(datetime.combine(day, time.max))
                .astimezone(utc)
                .replace(tzinfo=None),
                "time_type": "leave",
            }
        )

    def test_the_upgrade_gives_the_old_days_to_everybody(self):
        """After the upgrade a person on shifts gets the days made before it.

        A closing day the company set for its main schedule on an ordinary
        date is the company's own decision and keeps its schedule.
        """
        shifts = self._schedule("Shifts", self.company)
        person = self._employee("On shifts", shifts)
        liberation = self._old_holiday("Liberation Day", date(2033, 3, 3))
        closing = self._old_holiday("Inventory day", date(2033, 3, 4))
        self.assertEqual(
            self._owed_hours(person, date(2033, 3, 3)),
            8.0,
            "before the upgrade the person on shifts worked through it",
        )

        released = self.env["res.company"]._hand_bg_public_holidays_to_everyone()

        self.assertIn(liberation, released)
        self.assertFalse(
            liberation.calendar_id, "the official day is held for everybody"
        )
        self.assertEqual(liberation.company_id, self.company, "and stays the company's")
        self.assertEqual(
            self._owed_hours(person, date(2033, 3, 3)),
            0.0,
            "the person on shifts owes nothing on Liberation Day",
        )
        self.assertEqual(
            closing.calendar_id,
            self.company.resource_calendar_id,
            "the company's own closing day keeps its schedule",
        )
        self.assertEqual(
            self._owed_hours(person, date(2033, 3, 4)),
            8.0,
            "and the person on shifts still works that day",
        )

        self.assertFalse(
            self.env["res.company"]._hand_bg_public_holidays_to_everyone(),
            "running the upgrade step again changes nothing",
        )

    def test_the_upgrade_leaves_a_day_held_twice_for_a_person(self):
        """An old official day that another holiday of the company overlaps
        stays on its schedule instead of stopping the whole upgrade."""
        shifts = self._schedule("Shifts", self.company)
        old = self._old_holiday("Liberation Day", date(2033, 3, 3))
        self._old_holiday("Liberation Day, shifts", date(2033, 3, 3), schedule=shifts)
        unification = self._old_holiday("Unification Day", date(2033, 9, 6))

        released = self.env["res.company"]._hand_bg_public_holidays_to_everyone()

        self.assertEqual(old.calendar_id, self.company.resource_calendar_id)
        self.assertIn(unification, released, "the other days are still released")
        self.assertFalse(unification.calendar_id)

    def test_a_year_filled_in_from_another_zone_is_the_sofia_day(self):
        """An officer abroad, or a run with no zone at all, fills in the Sofia
        day: 3 March runs from midnight to midnight where the company works."""
        self.env.user.tz = "America/New_York"
        self.company._generate_bg_public_holidays(2034)
        self._assert_the_sofia_day(
            self._liberation_day(2034), 2034, "an officer abroad"
        )

        self.env.user.tz = False
        self.company._generate_bg_public_holidays(2035)
        self._assert_the_sofia_day(
            self._liberation_day(2035), 2035, "a run with no zone"
        )

    def test_the_wizard_fills_in_another_company_and_lists_its_year(self):
        """HR picks the branch in the wizard: the branch gets the year, and the
        list it opens is the branch's holidays of that year, every one."""
        branch = self.env["res.company"].create(
            {"name": "Branch", "country_id": self.env.ref("base.bg").id}
        )
        branch.resource_calendar_id = self._schedule("Branch week", branch)
        wizard = self.env["l10n.bg.generate.holidays.wizard"].create(
            {"year": 2031, "company_id": branch.id}
        )

        action = wizard.action_generate()

        listed = self.env["resource.calendar.leaves"].search(action["domain"])
        self.assertEqual(set(listed.mapped("company_id")), {branch})
        self.assertEqual(len(listed), 13, "every official day of 2031 is in the list")
        self.assertIn("Liberation Day", listed.mapped("name"))
        self.assertFalse(
            listed.mapped("calendar_id"), "held for everybody in the branch"
        )

    # -- the upgrade, further cases --------------------------------------

    def test_the_upgrade_script_itself_gives_the_days_to_everybody(self):
        """What the deploy runs - the upgrade script - releases the old days."""
        shifts = self._schedule("Shifts", self.company)
        person = self._employee("On shifts", shifts)
        self._old_holiday("Liberation Day", date(2033, 3, 3))
        path = file_path(
            "l10n_bg_hr_attendance_overtime_rates/migrations/19.0.1.0.6/post-migrate.py"
        )
        spec = importlib.util.spec_from_file_location("bg_holidays_upgrade", path)
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)

        script.migrate(self.env.cr, "19.0.1.0.5")

        self.env.invalidate_all()
        self.assertEqual(self._owed_hours(person, date(2033, 3, 3)), 0.0)

    def test_the_upgrade_gives_back_the_day_of_time_off(self):
        """A person on shifts who took 2-4 March 2033 off had the holiday
        counted as a day of leave; after the upgrade it is two days."""
        shifts = self._schedule("Shifts", self.company)
        person = self._employee("On shifts", shifts)
        self._old_holiday("Liberation Day", date(2033, 3, 3))
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Paid leave (test)",
                "requires_allocation": False,
                "leave_validation_type": "no_validation",
                "request_unit": "day",
            }
        )
        leave = self.env["hr.leave"].create(
            {
                "employee_id": person.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": date(2033, 3, 2),
                "request_date_to": date(2033, 3, 4),
            }
        )
        self.assertEqual(
            leave.number_of_days, 3, "before: the holiday is a day of leave"
        )

        self.env["res.company"]._hand_bg_public_holidays_to_everyone()

        self.assertEqual(leave.number_of_days, 2, "after: the holiday is not")

    def test_the_upgrade_reaches_a_schedule_the_company_has_left(self):
        """Days made while the company's main schedule was another one are
        released too."""
        former = self._schedule("Former main week", self.company)
        old = self._old_holiday("Liberation Day", date(2033, 3, 3), schedule=former)

        self.env["res.company"]._hand_bg_public_holidays_to_everyone()

        self.assertFalse(old.calendar_id)

    def test_the_upgrade_knows_days_made_from_utc_midnight(self):
        """Versions before the zone fix made the day from midnight UTC - 02:00
        in Sofia. It is still that official day and is released."""
        self.env.user.tz = "Europe/Sofia"
        old = self.env["resource.calendar.leaves"].create(
            {
                "name": "Liberation Day",
                "company_id": self.company.id,
                "calendar_id": self.company.resource_calendar_id.id,
                "resource_id": False,
                "date_from": datetime(2033, 3, 3, 0, 0),
                "date_to": datetime(2033, 3, 3, 23, 59, 59),
                "time_type": "leave",
            }
        )

        self.env["res.company"]._hand_bg_public_holidays_to_everyone()

        self.assertFalse(old.calendar_id)

    def test_the_upgrade_leaves_a_company_abroad_alone(self):
        """A company in another country keeps its own day on its schedule."""
        abroad = self.env["res.company"].create(
            {"name": "Abroad", "country_id": self.env.ref("base.de").id}
        )
        schedule = self._schedule("Abroad week", abroad)
        self.env.user.tz = "Europe/Sofia"
        their_day = (
            self.env["resource.calendar.leaves"]
            .with_company(abroad)
            .create(
                {
                    "name": "Their Christmas",
                    "company_id": abroad.id,
                    "calendar_id": schedule.id,
                    "resource_id": False,
                    "date_from": SOFIA.localize(datetime(2033, 12, 25))
                    .astimezone(utc)
                    .replace(tzinfo=None),
                    "date_to": SOFIA.localize(datetime(2033, 12, 25, 23, 59, 59))
                    .astimezone(utc)
                    .replace(tzinfo=None),
                    "time_type": "leave",
                }
            )
        )

        self.env["res.company"]._hand_bg_public_holidays_to_everyone()

        self.assertEqual(their_day.calendar_id, schedule)

    def test_the_upgrade_leaves_settled_days_and_closures_alone(self):
        """A day already over keeps its schedule - its time off and pay are
        settled - and so does a closure of several days that begins on an
        official date."""
        past = self._old_holiday("Liberation Day", date(2020, 3, 3))
        self.env.user.tz = "Europe/Sofia"
        closure = self.env["resource.calendar.leaves"].create(
            {
                "name": "Closed between the holidays",
                "company_id": self.company.id,
                "calendar_id": self.company.resource_calendar_id.id,
                "resource_id": False,
                "date_from": SOFIA.localize(datetime(2033, 12, 24))
                .astimezone(utc)
                .replace(tzinfo=None),
                "date_to": SOFIA.localize(datetime(2033, 12, 31, 23, 59, 59))
                .astimezone(utc)
                .replace(tzinfo=None),
                "time_type": "leave",
            }
        )

        released = self.env["res.company"]._hand_bg_public_holidays_to_everyone()

        self.assertNotIn(past, released)
        self.assertEqual(past.calendar_id, self.company.resource_calendar_id)
        self.assertEqual(closure.calendar_id, self.company.resource_calendar_id)

    def test_a_day_core_refuses_does_not_stop_the_upgrade(self):
        """Core counting the time off on one day again refuses it: that day
        stays on its schedule, the others are released and the upgrade ends."""
        refused = self._old_holiday("Liberation Day", date(2033, 3, 3))
        other = self._old_holiday("Unification Day", date(2033, 9, 6))
        Leave = type(self.env["resource.calendar.leaves"])
        original = Leave.write

        def write(records, vals):
            if refused in records and "calendar_id" in vals:
                raise ValidationError(
                    records.env._("the time off on it does not fit any more")
                )
            return original(records, vals)

        with (
            patch.object(Leave, "write", write),
            mute_logger(
                "odoo.addons.l10n_bg_hr_attendance_overtime_rates.models.res_company"
            ),
        ):
            released = self.env["res.company"]._hand_bg_public_holidays_to_everyone()

        self.assertEqual(refused.calendar_id, self.company.resource_calendar_id)
        self.assertIn(other, released)
        self.assertFalse(other.calendar_id)
