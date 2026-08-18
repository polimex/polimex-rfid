# -*- coding: utf-8 -*-
"""Regression tests for improvements back-ported from 19.0 to hr_attendance_multi_rfid.

Run:  odoo-bin -u hr_attendance_multi_rfid --test-enable --test-tags multi_rfid_backport
"""
from odoo import fields
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install', 'multi_rfid_backport')
class MultiRfidBackportRegressions(TransactionCase):

    # ---- 27870ac: same-second check-out must close the open attendance -----
    def test_last_open_checkin_same_timestamp(self):
        """_last_open_checkin(before_dt) must use '<=' so an exit that carries
        the SAME 1-second timestamp as the entry still matches the open
        attendance (otherwise the check-out is dropped and the record stays open)."""
        emp = self.env['hr.employee'].create({'name': 'Multi RFID BP Emp'})
        t = fields.Datetime.now()
        att = self.env['hr.attendance'].create({'employee_id': emp.id, 'check_in': t})
        found = emp._last_open_checkin(before_dt=t)
        self.assertEqual(found, att,
                         'an exit at the same timestamp as the entry must still match (<=)')

    # ---- a58ac6f: global working calendars stay visible --------------------
    def test_resource_calendar_rule_false_tolerant(self):
        rule = self.env.ref('hr_attendance_multi_rfid.ir_rule_hr_rfid_card_multi_company')
        self.assertIn('company_ids + [False]', rule.domain_force,
                      'global (company-less) working calendars must stay visible')
