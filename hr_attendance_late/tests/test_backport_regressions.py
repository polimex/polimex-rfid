# -*- coding: utf-8 -*-
"""Regression tests for the legal-rate feature back-ported from 19.0 (54c2d3b).

Run:  odoo-bin -i hr_attendance_late --test-enable --test-tags attendance_late_backport
"""
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install', 'attendance_late_backport')
class AttendanceLateBackportRegressions(TransactionCase):

    # ---- 54c2d3b: dated legal-rate model -----------------------------------
    def test_legal_rate_create_and_fields(self):
        rate = self.env['hr.legal.rate'].create({
            'code': 'OVERTIME',
            'name': 'Overtime coefficient',
            'date_from': '2026-01-01',
            'value': 1.5,
        })
        self.assertEqual(rate.value, 1.5)
        self.assertEqual(rate.code, 'OVERTIME')
        # currency defaulting / company optionality do not raise
        self.assertTrue(rate.id)

    def test_legal_rate_multi_company_false_tolerant(self):
        rule = self.env.ref('hr_attendance_late.ir_rule_hr_legal_rate_multi_company')
        self.assertIn("('company_id', '=', False)", rule.domain_force,
                      'global (company-less) legal rates must stay visible')

    # ---- 54c2d3b: no-show KPI on the digest --------------------------------
    def test_digest_no_show_kpi_field(self):
        self.assertIn('kpi_hr_rfid_att_no_show', self.env['digest.digest']._fields,
                      'digest must expose the no-show KPI toggle back-ported from 19')
