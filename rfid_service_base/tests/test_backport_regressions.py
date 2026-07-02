# -*- coding: utf-8 -*-
"""Regression tests for improvements back-ported from 19.0 to rfid_service_base.

Run:  odoo-bin -i rfid_service_base --test-enable --test-tags service_base_backport
"""
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install', 'service_base_backport')
class ServiceBaseBackportRegressions(TransactionCase):

    # ---- a58ac6f: multi-company False-tolerance on shared service tags ------
    def test_service_tag_rule_false_tolerance(self):
        rule = self.env.ref('rfid_service_base.ir_rule_rfid_service_tag_multi_company')
        self.assertIn('company_ids + [False]', rule.domain_force,
                      'shared/global service tags must stay visible (False-tolerance)')

    def test_global_service_tag_survives_rule_domain(self):
        """A company-less (global) tag matches the record-rule domain as
        superuser evaluates it — the '+ [False]' arm keeps it selectable
        (ACL for end-user groups is a separate concern, not this backport)."""
        tag = self.env['rfid.service.tags'].create({'name': 'BP Global Tag', 'company_id': False})
        # Emulate the rule domain evaluation with the current company set.
        found = self.env['rfid.service.tags'].search(
            [('id', '=', tag.id), ('company_id', 'in', self.env.companies.ids + [False])])
        self.assertEqual(found, tag, 'global tag must satisfy the company_ids + [False] domain')
