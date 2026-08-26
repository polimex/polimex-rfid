# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


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
        leaves = self.env['resource.calendar.leaves'].search([
            ('calendar_id', '=', self.company.resource_calendar_id.id),
            ('resource_id', '=', False),
            ('date_from', '>=', date(year, 1, 1)),
            ('date_from', '<=', date(year, 12, 31)),
        ])
        return {leave.date_from.date() for leave in leaves}

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
