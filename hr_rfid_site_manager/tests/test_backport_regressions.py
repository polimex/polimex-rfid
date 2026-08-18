# -*- coding: utf-8 -*-
"""Regression tests for improvements back-ported from 19.0 to hr_rfid_site_manager.

Run:  odoo-bin -u hr_rfid_site_manager --test-enable --test-tags site_manager_backport
"""
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install', 'site_manager_backport')
class SiteManagerBackportRegressions(TransactionCase):

    # ---- a58ac6f: global sites stay visible --------------------------------
    def test_site_rule_false_tolerant(self):
        rule = self.env.ref('hr_rfid_site_manager.ir_rule_hr_rfid_site_multi_company')
        self.assertIn('company_ids + [False]', rule.domain_force,
                      'global (company-less) sites must stay visible')

    # ---- 50d27ed: hr.rfid.site parent hierarchy ----------------------------
    def test_site_parent_store(self):
        Site = self.env['hr.rfid.site']
        self.assertTrue(Site._parent_store, 'hr.rfid.site must be a parent_store hierarchy')
        parent = Site.create({'name': 'BP Parent Site'})
        child = Site.create({'name': 'BP Child Site', 'parent_id': parent.id})
        self.assertTrue(child.parent_path and child.parent_path.startswith(parent.parent_path),
                        'child parent_path must extend the parent path (hierarchy back-port)')
