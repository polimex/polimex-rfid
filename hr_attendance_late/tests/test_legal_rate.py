# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'hr_attendance_late', 'legal_rate')
class TestHrLegalRate(TransactionCase):
    """Temporal lookup of dated legal coefficients.

    The cost calculation depends on picking the value effective on the worked
    day, so a statutory change applied via a new dated row never recalculates
    past periods. These tests pin that behaviour plus the company-override and
    cache-invalidation contracts.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rate = cls.env['hr.legal.rate']
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({'name': 'Legal Rate Co B'})
        cls.Rate.create([
            {'code': 'zz_test_night', 'date_from': '2025-01-01', 'value': 1.00},
            {'code': 'zz_test_night', 'date_from': '2026-01-01', 'value': 0.51},
            {'code': 'zz_test_night', 'date_from': '2026-01-01', 'value': 0.60,
             'company_id': cls.company.id},
            {'code': 'zz_test_weekend', 'date_from': '2020-01-01', 'value': 1.75},
        ])

    def test_picks_value_effective_on_date(self):
        """Latest date_from on or before the queried date wins."""
        self.assertEqual(self.Rate._get_rate('zz_test_night', date(2025, 6, 1)), 1.00)
        self.assertEqual(self.Rate._get_rate('zz_test_night', date(2026, 6, 1)), 0.51)

    def test_boundary_on_effective_date(self):
        """date_from is inclusive — the value applies from that day."""
        self.assertEqual(self.Rate._get_rate('zz_test_night', date(2026, 1, 1)), 0.51)
        self.assertEqual(self.Rate._get_rate('zz_test_night', date(2025, 12, 31)), 1.00)

    def test_company_override_wins_over_global(self):
        """A company-specific row beats the global one when both are effective."""
        self.assertEqual(
            self.Rate._get_rate('zz_test_night', date(2026, 6, 1), self.company.id),
            0.60,
        )

    def test_company_falls_back_to_global(self):
        """No company row → global value is used."""
        # other_company has no override → global 0.51
        self.assertEqual(
            self.Rate._get_rate('zz_test_night', date(2026, 6, 1), self.other_company.id),
            0.51,
        )
        # company override only exists from 2026 → 2025 query falls back to global
        self.assertEqual(
            self.Rate._get_rate('zz_test_night', date(2025, 6, 1), self.company.id),
            1.00,
        )

    def test_missing_code_returns_zero(self):
        self.assertEqual(self.Rate._get_rate('does_not_exist', date(2026, 6, 1)), 0.0)

    def test_before_any_effective_date_returns_zero(self):
        self.assertEqual(self.Rate._get_rate('zz_test_night', date(2024, 1, 1)), 0.0)

    def test_cache_invalidated_on_create(self):
        """ormcache must not serve a stale miss after a new row is added."""
        # Prime the cache with a miss for 2027.
        self.assertEqual(self.Rate._get_rate('zz_test_night', date(2027, 6, 1)), 0.51)
        self.Rate.create([{'code': 'zz_test_night', 'date_from': '2027-01-01', 'value': 0.70}])
        self.assertEqual(self.Rate._get_rate('zz_test_night', date(2027, 6, 1)), 0.70)

    def test_cache_invalidated_on_write(self):
        rate = self.Rate.search([('code', '=', 'zz_test_weekend')], limit=1)
        self.assertEqual(self.Rate._get_rate('zz_test_weekend', date(2026, 6, 1)), 1.75)
        rate.value = 1.80
        self.assertEqual(self.Rate._get_rate('zz_test_weekend', date(2026, 6, 1)), 1.80)

    def test_unique_constraint(self):
        """Same code + date_from + company cannot be duplicated.

        SQL UNIQUE (models.Constraint) raises IntegrityError, not
        ValidationError — see odoo19-gotchas.
        """
        from psycopg2 import IntegrityError
        from odoo.tools import mute_logger
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            with self.env.cr.savepoint():
                self.Rate.create([{'code': 'zz_test_weekend',
                                   'date_from': '2020-01-01', 'value': 2.0}])
                self.env.flush_all()  # constraint fires on flush, not create
