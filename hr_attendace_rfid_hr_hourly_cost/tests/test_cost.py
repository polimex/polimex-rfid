# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_hourly_cost", "rfid_cost_rates")
class TestAttendanceCostRates(TransactionCase):
    """Day-cost breakdown using dated legal rates + holiday detection.

    Hourly cost 10.0; КТ multipliers workday 1.5 / weekend 1.75 / holiday 2.0;
    night supplement +0.51/hour (additive). Holidays seeded for 2026 so
    2026-05-24 (Culture Day) is an official holiday.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.Rate = cls.env['hr.legal.rate']
        # Ensure rates exist independent of l10n_bg seed order.
        cls._ensure_rate('overtime_workday', '2020-01-01', 1.5)
        cls._ensure_rate('overtime_weekend', '2020-01-01', 1.75)
        cls._ensure_rate('overtime_holiday', '2020-01-01', 2.0)
        cls._ensure_rate('night_supplement', '2026-01-01', 0.51)
        if not cls.company.resource_calendar_id:
            cls.company.resource_calendar_id = cls.env['resource.calendar'].create(
                {'name': 'Cost Test Cal', 'company_id': cls.company.id})
        # Seed a known holiday (2026-05-24).
        cls.company._generate_bg_public_holidays(2026)
        cls.emp = cls.env['hr.employee'].create({
            'name': 'Cost Rate Emp', 'company_id': cls.company.id, 'hourly_cost': 10.0,
        })

    @classmethod
    def _ensure_rate(cls, code, date_from, value):
        existing = cls.env['hr.legal.rate'].search([
            ('code', '=', code), ('company_id', '=', False)], limit=1)
        if not existing:
            cls.env['hr.legal.rate'].create(
                {'code': code, 'date_from': date_from, 'value': value})

    def _mk(self, for_date, **kw):
        return self.env['hr.attendance.extra'].create({
            'employee_id': self.emp.id, 'for_date': for_date, **kw})

    def test_workday_overtime(self):
        rec = self._mk('2026-06-01', actual_work_time=8.0, overtime=2.0)
        self.assertEqual(rec.cost_regular, 80.0)
        self.assertEqual(rec.cost_overtime, 30.0)   # 2 * 10 * 1.5
        self.assertEqual(rec.actual_work_time_cost, 110.0)

    def test_weekend_extra(self):
        rec = self._mk('2026-06-06', extra_time=6.0)  # Saturday, not a holiday
        self.assertFalse(rec._is_public_holiday())
        self.assertEqual(rec.cost_extra, 105.0)       # 6 * 10 * 1.75
        self.assertEqual(rec.actual_work_time_cost, 105.0)

    def test_holiday_extra_uses_higher_rate(self):
        rec = self._mk('2026-05-24', extra_time=6.0)  # Culture Day (seeded)
        self.assertTrue(rec._is_public_holiday())
        self.assertEqual(rec.cost_extra, 120.0)       # 6 * 10 * 2.0
        self.assertEqual(rec.actual_work_time_cost, 120.0)

    def test_night_supplement_additive(self):
        rec = self._mk('2026-06-02', actual_work_time=8.0, actual_work_time_night=4.0)
        self.assertEqual(rec.cost_regular, 80.0)
        self.assertAlmostEqual(rec.cost_night_supplement, 2.04)  # 4 * 0.51
        self.assertAlmostEqual(rec.actual_work_time_cost, 82.04)

    def test_night_supplement_on_overtime_and_extra(self):
        """Night supplement covers night hours regardless of class."""
        rec = self._mk('2026-06-06', extra_time=6.0, extra_night=3.0)
        # extra cost 6*10*1.75=105 ; night supp 3*0.51=1.53
        self.assertAlmostEqual(rec.cost_night_supplement, 1.53)
        self.assertAlmostEqual(rec.actual_work_time_cost, 106.53)

    def test_no_rates_falls_back_to_flat(self):
        """With multipliers missing for a class, premium defaults to base (1.0)."""
        # Use a code-less scenario: a date before any night rate → no supplement.
        rec = self._mk('2025-06-02', actual_work_time=8.0, actual_work_time_night=4.0)
        # night_supplement not effective in 2025 → 0 supplement
        self.assertEqual(rec.cost_night_supplement, 0.0)
        self.assertEqual(rec.actual_work_time_cost, 80.0)

    def test_historical_rate_preserved(self):
        """A later night-rate row must not change a past day's cost on recompute."""
        rec = self._mk('2026-06-02', actual_work_time=0.0, actual_work_time_night=10.0)
        self.assertAlmostEqual(rec.cost_night_supplement, 5.10)  # 10 * 0.51
        # Add a 2027 rate; recompute 2026 record — must still use 0.51.
        self.Rate.create({'code': 'night_supplement', 'date_from': '2027-01-01', 'value': 0.70})
        rec.invalidate_recordset(['cost_night_supplement', 'actual_work_time_cost'])
        rec._compute_actual_work_time_cost()
        self.assertAlmostEqual(rec.cost_night_supplement, 5.10)
