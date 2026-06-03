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
        """Night supplement only effective from euro adoption (2026-01-01)."""
        Rate = self.env['hr.legal.rate']
        self.assertEqual(Rate._get_rate('night_supplement', date(2025, 12, 31)), 0.0)
        self.assertEqual(Rate._get_rate('night_supplement', date(2026, 1, 1)), 0.51)

    def test_generates_fixed_and_moving_holidays(self):
        """Fixed dates + Orthodox-Easter cluster created as global leaves."""
        created = self.company._generate_bg_public_holidays(2026)
        days = {l.date_from.date() for l in created}
        # Fixed
        self.assertIn(date(2026, 3, 3), days, "Liberation Day")
        self.assertIn(date(2026, 5, 24), days, "Culture Day")
        self.assertIn(date(2026, 12, 25), days, "Christmas")
        # Moving — Orthodox Easter 2026 = Apr 12 → Fri 10 / Sat 11 / Mon 13
        self.assertIn(date(2026, 4, 10), days, "Good Friday")
        self.assertIn(date(2026, 4, 11), days, "Holy Saturday")
        self.assertIn(date(2026, 4, 13), days, "Easter Monday")
        # All global (no resource) on the company calendar
        self.assertTrue(all(not l.resource_id for l in created))
        self.assertTrue(all(l.calendar_id == self.company.resource_calendar_id
                            for l in created))

    def test_generation_is_idempotent(self):
        """Re-running the same year creates nothing new."""
        first = self.company._generate_bg_public_holidays(2026)
        self.assertTrue(first)
        second = self.company._generate_bg_public_holidays(2026)
        self.assertFalse(second, "Re-run must not duplicate holidays")

    def test_easter_differs_by_year(self):
        """Moving cluster tracks the year (regression vs hardcoded dates)."""
        c2026 = self.company._generate_bg_public_holidays(2026)
        # Orthodox Easter 2027 = May 2 → Good Friday Apr 30
        c2027 = self.company._generate_bg_public_holidays(2027)
        days27 = {l.date_from.date() for l in c2027}
        self.assertIn(date(2027, 4, 30), days27, "2027 Good Friday")
        self.assertNotIn(date(2026, 4, 10), days27, "must not reuse 2026 date")
