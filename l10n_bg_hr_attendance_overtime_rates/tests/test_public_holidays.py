# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from pytz import timezone, utc


@tagged('post_install', '-at_install', 'l10n_bg_overtime', 'bg_holidays')
class TestBgPublicHolidays(TransactionCase):
    """Bulgarian public-holiday generation + seeded legal rates."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # Ensure the company has a working calendar to attach holidays to.
        if not cls.company.resource_calendar_id:
            cls.company.resource_calendar_id = cls.env['resource.calendar'].create(
                {'name': 'Test Cal', 'company_id': cls.company.id})

    def test_seeded_legal_rates(self):
        """КТ чл. 262 multipliers are seeded and resolvable."""
        Rate = self.env['hr.legal.rate']
        d = date(2026, 6, 1)
        self.assertEqual(Rate._get_rate('overtime_workday', d), 1.5)
        self.assertEqual(Rate._get_rate('overtime_weekend', d), 1.75)
        self.assertEqual(Rate._get_rate('overtime_holiday', d), 2.0)
        self.assertEqual(Rate._get_rate('night_supplement', d), 0.51)

    def test_night_supplement_dated_at_2026(self):
        """The statutory night supplement this module ships starts on its date.

        Asked of the module's OWN row rather than of the global lookup: any
        other module - or the customer - may hold a night rate of their own
        with an earlier date, and that is their business, not a fault in the
        figure shipped here.
        """
        rate = self.env.ref(
            'l10n_bg_hr_attendance_overtime_rates.rate_night_supplement_2026',
            raise_if_not_found=False)
        self.assertTrue(rate, "The module must ship a night-supplement rate")
        self.assertEqual(rate.code, 'night_supplement')
        self.assertEqual(rate.value, 0.51)
        self.assertEqual(rate.date_from, date(2026, 1, 1))

    def _holidays_on_the_calendar(self, year):
        """Every official day the company's calendar holds for that year.

        The question the payroll clerk asks is "is 3 March a holiday on our
        calendar", never "did that one call create it". Asking the calendar
        keeps the test true on a database where the days are already there -
        which is every demo installation, and every customer who ran the
        generator once last year.
        """
        calendar = self.company.resource_calendar_id
        # The day of a holiday is the calendar's own day: its first moment is
        # stored in UTC, which in Sofia is the evening before.
        tz = timezone(calendar.tz or 'UTC')
        leaves = self.env['resource.calendar.leaves'].search([
            ('calendar_id', '=', calendar.id),
            ('resource_id', '=', False),
            ('date_from', '>=', date(year - 1, 12, 31)),
            ('date_from', '<', date(year + 1, 1, 1)),
        ])
        days = {utc.localize(leave.date_from).astimezone(tz).date() for leave in leaves}
        return {day for day in days if day.year == year}

    def _liberation_day(self, year):
        return self.env['resource.calendar.leaves'].search([
            ('calendar_id', '=', self.company.resource_calendar_id.id),
            ('resource_id', '=', False),
            ('name', '=', 'Liberation Day'),
            ('date_from', '>=', date(year, 3, 2)),
            ('date_from', '<', date(year, 3, 4)),
        ])

    def _assert_the_sofia_day(self, leave, year, who):
        sofia = timezone('Europe/Sofia')
        self.assertEqual(len(leave), 1, "3 March %s must be on the calendar once" % year)
        begins = utc.localize(leave.date_from).astimezone(sofia)
        ends = utc.localize(leave.date_to).astimezone(sofia)
        self.assertEqual((begins.date(), begins.hour, begins.minute), (date(year, 3, 3), 0, 0),
                         "the holiday begins at midnight in Sofia (run by %s)" % who)
        self.assertEqual((ends.date(), ends.hour, ends.minute), (date(year, 3, 3), 23, 59),
                         "and ends at the last minute of that day there (run by %s)" % who)

    def test_a_holiday_is_the_whole_day_where_the_company_works(self):
        """Liberation Day runs from midnight to midnight in Sofia.

        A worker on the night of 2 March is not on holiday, and one on the
        night of 4 March is not either: the holiday is the third, as the
        company lives it - whoever fills the year in: an HR officer in Sofia,
        one in another zone running it again, or the yearly cron, which runs
        with no zone at all. Handed over as midnight to midnight in UTC, the
        officer's run made it 02:00 on the third to 01:59 on the fourth in
        Sofia.
        """
        self.company.resource_calendar_id.tz = 'Europe/Sofia'
        Leaves = self.env['resource.calendar.leaves']
        # A year nobody has filled in yet, so the days are the ones made here.
        self.env.user.tz = 'Europe/Sofia'
        self.company._generate_bg_public_holidays(2031)
        self._assert_the_sofia_day(self._liberation_day(2031), 2031, 'an officer in Sofia')
        held = Leaves.search_count([('calendar_id', '=', self.company.resource_calendar_id.id),
                                    ('resource_id', '=', False)])

        # Run again from another zone: nothing is added and nothing moves.
        self.env.user.tz = 'America/New_York'
        self.company._generate_bg_public_holidays(2031)
        self.assertEqual(
            Leaves.search_count([('calendar_id', '=', self.company.resource_calendar_id.id),
                                 ('resource_id', '=', False)]),
            held, "a second run, from any zone, adds no day twice")
        self._assert_the_sofia_day(self._liberation_day(2031), 2031, 'a second officer')

        # The yearly cron, as the scheduler runs it: no user zone at all.
        root = self.env.ref('base.user_root')
        root.tz = False
        next_year = fields.Date.today().year + 1
        self.env['res.company'].with_user(root)._cron_generate_bg_public_holidays()
        self._assert_the_sofia_day(self._liberation_day(next_year), next_year, 'the cron')

    def test_generates_fixed_and_moving_holidays(self):
        """Fixed dates + Orthodox-Easter cluster created as global leaves."""
        self.company._generate_bg_public_holidays(2026)
        days = self._holidays_on_the_calendar(2026)
        # Fixed
        self.assertIn(date(2026, 3, 3), days, "Liberation Day")
        self.assertIn(date(2026, 5, 24), days, "Culture Day")
        self.assertIn(date(2026, 12, 25), days, "Christmas")
        # Moving - Orthodox Easter 2026 = Apr 12 -> Fri 10 / Sat 11 / Mon 13
        self.assertIn(date(2026, 4, 10), days, "Good Friday")
        self.assertIn(date(2026, 4, 11), days, "Holy Saturday")
        self.assertIn(date(2026, 4, 13), days, "Easter Monday")
        # Official days belong to everybody, so they carry no employee - a day
        # attached to one resource would take the holiday away from the rest.
        leaves = self.env['resource.calendar.leaves'].search([
            ('calendar_id', '=', self.company.resource_calendar_id.id),
            ('date_from', '>=', date(2026, 1, 1)),
            ('date_from', '<=', date(2026, 12, 31)),
        ])
        self.assertTrue(leaves, "The year must hold official days at all")
        self.assertTrue(all(not leave.resource_id for leave in leaves))

    def test_generation_is_idempotent(self):
        """Running the generator again leaves the calendar as it was.

        Written against the CALENDAR rather than the call's return value: on a
        database where the year is already filled in - a demo instance, or a
        customer who ran it last year - the first call legitimately creates
        nothing, and a test that demands otherwise would only pass on a
        database nobody has.
        """
        self.company._generate_bg_public_holidays(2026)
        after_first = self._holidays_on_the_calendar(2026)
        self.assertTrue(after_first, "The year must be filled in by now")

        self.company._generate_bg_public_holidays(2026)
        self.assertEqual(
            self._holidays_on_the_calendar(2026), after_first,
            "Re-run must not duplicate holidays",
        )

    def test_easter_differs_by_year(self):
        """Moving cluster tracks the year (regression vs hardcoded dates)."""
        self.company._generate_bg_public_holidays(2026)
        # Orthodox Easter 2027 = May 2 -> Good Friday Apr 30
        self.company._generate_bg_public_holidays(2027)
        days27 = self._holidays_on_the_calendar(2027)
        self.assertIn(date(2027, 4, 30), days27, "2027 Good Friday")
        self.assertNotIn(date(2026, 4, 10), days27, "must not reuse 2026 date")
