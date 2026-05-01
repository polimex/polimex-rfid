# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""End-to-end tests for the auto-refill cron entrypoint.

Existing test_12-test_14 tests cover the inner _auto_refill() helper but
bypass the cron-level scheduling logic (refill_nextcall, multi-company
loop, audit row creation). Production reports that the cron runs without
errors yet skips eligible employees, so this module specifically targets
auto_refill_job() and exhaustively covers every refill variation:

  * Cron-level: nextcall past/future/null, idempotency, advancement,
    multi-company isolation, audit row creation, history linking.
  * Refill type 'fixed': set balance up, set balance DOWN, no-op when
    equal, restore from negative.
  * Refill type 'up_to': top up to max, partial top-up when amount
    smaller than gap, no-op when full, no-op when over max.
  * Mixed cohort: many employees in one pass with mixed types and
    states; correct total_refill aggregation.
  * Cohort filtering: archived employees, employees in another company,
    employees with auto_refill flag off, employees with zero amount.
  * Audit: history.auto_refill_id linkage; no audit row when nothing
    actually changed.
"""
from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import float_compare


def fc(a, b):
    return float_compare(a, b, precision_digits=2) == 0


@tagged('rfid_vending', 'rfid_vending_auto_refill', 'post_install', '-at_install')
class TestAutoRefillCron(TransactionCase):
    """auto_refill_job() entrypoint coverage — every refill variation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.RefillModel = cls.env['hr.rfid.vending.auto.refill']
        cls.HistoryModel = cls.env['hr.rfid.vending.balance.history']
        cls.company = cls.env.company
        cls.company.write({
            'refill_interval_number': 1,
            'refill_interval_type': 'months',
            'refill_nextcall': datetime.now() - timedelta(days=1),
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_employee(self, name, company=None, **vending_vals):
        defaults = {'name': name, 'company_id': (company or self.company).id}
        emp = self.env['hr.employee'].create(defaults)
        if vending_vals:
            emp.write(vending_vals)
        return emp

    def _set_company_due(self, company=None):
        (company or self.company).refill_nextcall = (
            datetime.now() - timedelta(days=1)
        )

    def _set_company_future(self, company=None):
        (company or self.company).refill_nextcall = (
            datetime.now() + timedelta(days=1)
        )

    # ==================================================================
    # SECTION 1 — Cron entrypoint scheduling
    # ==================================================================

    def test_cron_skips_when_nextcall_in_future(self):
        """Future nextcall: cron must not modify balances."""
        self._set_company_future()
        emp = self._make_employee(
            'Future Eric',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=10.0,
            hr_rfid_vending_refill_type='fixed',
        )
        before = emp.hr_rfid_vending_balance
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertEqual(emp.hr_rfid_vending_balance, before)

    def test_cron_runs_when_nextcall_in_past(self):
        """Past nextcall: cron must run and advance the timestamp."""
        self._set_company_due()
        emp = self._make_employee(
            'Eligible Ed',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=15.0,
            hr_rfid_vending_refill_type='fixed',
        )
        old_nextcall = self.company.refill_nextcall
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.company.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 15.0))
        self.assertGreater(self.company.refill_nextcall, old_nextcall)

    def test_cron_skips_when_nextcall_is_null(self):
        """Companies with no refill_nextcall set must be skipped, not crash."""
        self.company.refill_nextcall = False
        self._make_employee(
            'No Nextcall Nina',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=10.0,
            hr_rfid_vending_refill_type='fixed',
        )
        # Must not raise.
        self.RefillModel.auto_refill_job()

    def test_cron_advances_nextcall_even_when_no_employees_match(self):
        """Empty cohort still advances nextcall — otherwise the cron loops."""
        self._set_company_due()
        old = self.company.refill_nextcall
        self.RefillModel.auto_refill_job()
        self.company.invalidate_recordset()
        self.assertGreater(self.company.refill_nextcall, old)

    def test_cron_idempotent_within_interval(self):
        """Second pass within interval must NOT refill again."""
        self._set_company_due()
        emp = self._make_employee(
            'Idem Iris',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=12.0,
            hr_rfid_vending_refill_type='fixed',
        )
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 12.0))
        # Spend then re-run.
        emp.hr_rfid_vending_add_to_balance(-5.0)
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 7.0))

    # ==================================================================
    # SECTION 2 — Refill type 'fixed'
    # ==================================================================

    def test_fixed_sets_balance_up_to_amount(self):
        """fixed: balance < refill_amount → set to refill_amount."""
        self._set_company_due()
        emp = self._make_employee(
            'Fixed Up Frank',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=20.0,
            hr_rfid_vending_refill_type='fixed',
        )
        emp.hr_rfid_vending_add_to_balance(5.0)
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 20.0))

    def test_fixed_sets_balance_down_to_amount(self):
        """fixed: balance > refill_amount → balance is RESET DOWN.

        This is a deliberate design choice: 'fixed' means the monthly
        allowance is hard-set every cycle, so unspent excess is wiped.
        """
        self._set_company_due()
        emp = self._make_employee(
            'Fixed Down Doris',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=15.0,
            hr_rfid_vending_refill_type='fixed',
        )
        emp.hr_rfid_vending_add_to_balance(40.0)
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 15.0))

    def test_fixed_no_op_when_balance_equals_amount(self):
        """fixed: balance == refill_amount → no change, no audit row."""
        self._set_company_due()
        emp = self._make_employee(
            'Equal Eddie',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=10.0,
            hr_rfid_vending_refill_type='fixed',
        )
        emp.hr_rfid_vending_add_to_balance(10.0)
        history_before = self.HistoryModel.search_count(
            [('employee_id', '=', emp.id)]
        )
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        history_after = self.HistoryModel.search_count(
            [('employee_id', '=', emp.id)]
        )
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 10.0))
        self.assertEqual(history_before, history_after)

    def test_fixed_restores_from_negative_balance(self):
        """fixed with negative balance (employee within credit limit) → set
        to refill_amount. Without a credit limit the negative is shunted
        to recharge_balance instead, so we configure one here."""
        self._set_company_due()
        emp = self._make_employee(
            'Negative Nick',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=25.0,
            hr_rfid_vending_refill_type='fixed',
            hr_rfid_vending_limit=10.0,
        )
        emp.hr_rfid_vending_add_to_balance(-8.0)
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, -8.0),
                        'Setup precondition: balance must be -8 within credit limit')
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 25.0))

    # ==================================================================
    # SECTION 3 — Refill type 'up_to'
    # ==================================================================

    def test_up_to_starts_from_zero_tops_to_max(self):
        """up_to from zero, amount >= max → top to max."""
        self._set_company_due()
        emp = self._make_employee(
            'UpTo Ursula',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=50.0,
            hr_rfid_vending_refill_type='up_to',
            hr_rfid_vending_refill_max=20.0,
        )
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 20.0))

    def test_up_to_partial_when_amount_smaller_than_gap(self):
        """up_to: amount < (max - balance) → add only amount, not full max."""
        self._set_company_due()
        emp = self._make_employee(
            'Partial Pete',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=5.0,
            hr_rfid_vending_refill_type='up_to',
            hr_rfid_vending_refill_max=100.0,
        )
        # Balance at 10, gap to max = 90, amount = 5 → final 15.
        emp.hr_rfid_vending_add_to_balance(10.0)
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 15.0))

    def test_up_to_caps_when_amount_overshoots(self):
        """up_to: amount > gap → only fill the gap, never overshoot max."""
        self._set_company_due()
        emp = self._make_employee(
            'Capped Cara',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=50.0,
            hr_rfid_vending_refill_type='up_to',
            hr_rfid_vending_refill_max=20.0,
        )
        emp.hr_rfid_vending_add_to_balance(5.0)
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 20.0))

    def test_up_to_no_op_when_balance_at_max(self):
        """up_to: balance == max → no change."""
        self._set_company_due()
        emp = self._make_employee(
            'AtMax Alex',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=10.0,
            hr_rfid_vending_refill_type='up_to',
            hr_rfid_vending_refill_max=15.0,
        )
        emp.hr_rfid_vending_add_to_balance(15.0)
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 15.0))

    def test_up_to_no_op_when_balance_above_max(self):
        """up_to: balance > max (e.g. left over from prior config) → no change."""
        self._set_company_due()
        emp = self._make_employee(
            'OverMax Olive',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=10.0,
            hr_rfid_vending_refill_type='up_to',
            hr_rfid_vending_refill_max=15.0,
        )
        emp.hr_rfid_vending_add_to_balance(25.0)
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 25.0))

    # ==================================================================
    # SECTION 4 — Cohort filtering
    # ==================================================================

    def test_filter_excludes_auto_refill_off(self):
        """auto_refill = False → never touched."""
        self._set_company_due()
        emp = self._make_employee(
            'Disabled Dave',
            hr_rfid_vending_auto_refill=False,
            hr_rfid_vending_refill_amount=20.0,
            hr_rfid_vending_refill_type='fixed',
        )
        before = emp.hr_rfid_vending_balance
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertEqual(emp.hr_rfid_vending_balance, before)

    def test_filter_excludes_zero_amount(self):
        """refill_amount = 0 → search filter excludes; no history written."""
        self._set_company_due()
        emp = self._make_employee(
            'Zero Zach',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=0.0,
            hr_rfid_vending_refill_type='fixed',
        )
        history_before = self.HistoryModel.search_count(
            [('employee_id', '=', emp.id)]
        )
        self.RefillModel.auto_refill_job()
        history_after = self.HistoryModel.search_count(
            [('employee_id', '=', emp.id)]
        )
        self.assertEqual(history_before, history_after)

    def test_filter_excludes_archived_employees(self):
        """active=False employees must NOT be refilled — search defaults to active=True."""
        self._set_company_due()
        emp = self._make_employee(
            'Archived Anna',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=10.0,
            hr_rfid_vending_refill_type='fixed',
        )
        emp.active = False
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        # archived → no refill (active=True is implicit in search)
        self.assertEqual(emp.hr_rfid_vending_balance, 0.0)

    # ==================================================================
    # SECTION 5 — Multi-company isolation
    # ==================================================================

    def test_multicompany_each_company_advances_independently(self):
        """Each company's nextcall advances independently. Refill of one
        company must not affect employees of another."""
        company_b = self.env['res.company'].create({
            'name': 'Branch B',
        })
        company_b.write({
            'refill_interval_number': 1,
            'refill_interval_type': 'months',
            'refill_nextcall': datetime.now() + timedelta(days=1),  # future
        })
        self._set_company_due(self.company)

        emp_a = self._make_employee(
            'Company A Ann',
            company=self.company,
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=10.0,
            hr_rfid_vending_refill_type='fixed',
        )
        emp_b = self._make_employee(
            'Company B Bob',
            company=company_b,
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=10.0,
            hr_rfid_vending_refill_type='fixed',
        )
        self.RefillModel.auto_refill_job()
        emp_a.invalidate_recordset()
        emp_b.invalidate_recordset()
        self.assertTrue(fc(emp_a.hr_rfid_vending_balance, 10.0))
        self.assertTrue(fc(emp_b.hr_rfid_vending_balance, 0.0),
                        'Company B was not due → emp_b must remain at 0')

    def test_multicompany_refill_does_not_leak_across_companies(self):
        """Even when both companies are due, employee balances must not be
        cross-fed (no domain leak)."""
        company_b = self.env['res.company'].create({
            'name': 'Branch C',
            'refill_interval_number': 1,
            'refill_interval_type': 'months',
            'refill_nextcall': datetime.now() - timedelta(days=1),
        })
        emp_a = self._make_employee(
            'Strict Ann',
            company=self.company,
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=10.0,
            hr_rfid_vending_refill_type='fixed',
        )
        emp_b = self._make_employee(
            'Strict Bob',
            company=company_b,
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=25.0,
            hr_rfid_vending_refill_type='fixed',
        )
        self.RefillModel.auto_refill_job()
        emp_a.invalidate_recordset()
        emp_b.invalidate_recordset()
        # Each receives its own company's amount, not the other's.
        self.assertTrue(fc(emp_a.hr_rfid_vending_balance, 10.0))
        self.assertTrue(fc(emp_b.hr_rfid_vending_balance, 25.0))

    # ==================================================================
    # SECTION 6 — Audit trail
    # ==================================================================

    def test_audit_row_created_when_at_least_one_refill(self):
        """One non-empty pass → exactly one hr.rfid.vending.auto.refill row."""
        self._set_company_due()
        self._make_employee(
            'Audit Anna',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=8.0,
            hr_rfid_vending_refill_type='fixed',
        )
        before = self.RefillModel.search_count([])
        self.RefillModel.auto_refill_job()
        after = self.RefillModel.search_count([])
        self.assertEqual(after - before, 1)

    def test_no_audit_row_when_nothing_changed(self):
        """If every employee was already at target, no audit row is created."""
        self._set_company_due()
        emp = self._make_employee(
            'Already At Target',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=10.0,
            hr_rfid_vending_refill_type='fixed',
        )
        emp.hr_rfid_vending_add_to_balance(10.0)
        before = self.RefillModel.search_count([])
        self.RefillModel.auto_refill_job()
        after = self.RefillModel.search_count([])
        self.assertEqual(before, after,
                         'No-op pass must not create an empty audit row')

    def test_history_rows_link_back_to_audit(self):
        """Every balance_history row from the pass has auto_refill_id set
        to the just-created audit record."""
        self._set_company_due()
        emp = self._make_employee(
            'Linked Lou',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=12.0,
            hr_rfid_vending_refill_type='fixed',
        )
        self.RefillModel.auto_refill_job()
        latest = self.RefillModel.search([], order='id desc', limit=1)
        history = self.HistoryModel.search([('employee_id', '=', emp.id)])
        self.assertTrue(history)
        self.assertTrue(all(h.auto_refill_id == latest for h in history))

    def test_total_refill_aggregates_across_multiple_employees(self):
        """auto_refill_total is sum of all per-employee balance_change values."""
        self._set_company_due()
        emps = []
        for i, amount in enumerate([5.0, 10.0, 15.0]):
            emps.append(self._make_employee(
                f'Cohort #{i}',
                hr_rfid_vending_auto_refill=True,
                hr_rfid_vending_refill_amount=amount,
                hr_rfid_vending_refill_type='fixed',
            ))
        self.RefillModel.auto_refill_job()
        latest = self.RefillModel.search([], order='id desc', limit=1)
        # 5 + 10 + 15 = 30 (all started from 0).
        self.assertTrue(fc(latest.auto_refill_total, 30.0))

    # ==================================================================
    # SECTION 7 — Mixed cohort
    # ==================================================================

    def test_mixed_cohort_processes_each_correctly(self):
        """Multiple employees with mixed types and edge states in one pass —
        each is processed by its own rule."""
        self._set_company_due()

        # type=fixed, balance < amount → set to amount
        e_low_fixed = self._make_employee(
            'Low Fixed',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=20.0,
            hr_rfid_vending_refill_type='fixed',
        )
        e_low_fixed.hr_rfid_vending_add_to_balance(3.0)

        # type=fixed, balance == amount → no-op
        e_eq_fixed = self._make_employee(
            'Equal Fixed',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=10.0,
            hr_rfid_vending_refill_type='fixed',
        )
        e_eq_fixed.hr_rfid_vending_add_to_balance(10.0)

        # type=up_to, balance < max → top up
        e_up_partial = self._make_employee(
            'UpTo Partial',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=50.0,
            hr_rfid_vending_refill_type='up_to',
            hr_rfid_vending_refill_max=15.0,
        )
        e_up_partial.hr_rfid_vending_add_to_balance(5.0)

        # type=up_to, balance >= max → no-op
        e_up_full = self._make_employee(
            'UpTo Full',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=50.0,
            hr_rfid_vending_refill_type='up_to',
            hr_rfid_vending_refill_max=10.0,
        )
        e_up_full.hr_rfid_vending_add_to_balance(10.0)

        # auto_refill off → no-op
        e_off = self._make_employee(
            'Off',
            hr_rfid_vending_auto_refill=False,
            hr_rfid_vending_refill_amount=99.0,
            hr_rfid_vending_refill_type='fixed',
        )

        self.RefillModel.auto_refill_job()
        for r in (e_low_fixed, e_eq_fixed, e_up_partial, e_up_full, e_off):
            r.invalidate_recordset()

        self.assertTrue(fc(e_low_fixed.hr_rfid_vending_balance, 20.0),
                        'Low fixed must be set to amount')
        self.assertTrue(fc(e_eq_fixed.hr_rfid_vending_balance, 10.0),
                        'Equal fixed unchanged')
        self.assertTrue(fc(e_up_partial.hr_rfid_vending_balance, 15.0),
                        'Up-to partial must reach max')
        self.assertTrue(fc(e_up_full.hr_rfid_vending_balance, 10.0),
                        'Up-to full unchanged')
        self.assertTrue(fc(e_off.hr_rfid_vending_balance, 0.0),
                        'auto_refill off → never touched')

    # ==================================================================
    # SECTION 8 — Configuration mutations between cycles
    # ==================================================================

    def test_changing_amount_triggers_reset_on_next_cycle(self):
        """If admin changes refill_amount mid-month, the next cycle must
        re-set the (fixed-type) balance to the new amount."""
        self._set_company_due()
        emp = self._make_employee(
            'Mutable Mike',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=10.0,
            hr_rfid_vending_refill_type='fixed',
        )
        # First cycle: balance set to 10.
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 10.0))

        # Admin bumps amount to 25; force the cron to be due again.
        emp.hr_rfid_vending_refill_amount = 25.0
        self._set_company_due()
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 25.0))

    def test_switching_type_fixed_to_up_to_keeps_balance(self):
        """Switching type from fixed → up_to mid-flight: existing balance
        preserved, top-up to max next cycle."""
        self._set_company_due()
        emp = self._make_employee(
            'Switching Sam',
            hr_rfid_vending_auto_refill=True,
            hr_rfid_vending_refill_amount=8.0,
            hr_rfid_vending_refill_type='fixed',
        )
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 8.0))

        emp.write({
            'hr_rfid_vending_refill_type': 'up_to',
            'hr_rfid_vending_refill_max': 30.0,
            'hr_rfid_vending_refill_amount': 50.0,
        })
        self._set_company_due()
        self.RefillModel.auto_refill_job()
        emp.invalidate_recordset()
        self.assertTrue(fc(emp.hr_rfid_vending_balance, 30.0),
                        'After switch to up_to, balance must top up to max')
