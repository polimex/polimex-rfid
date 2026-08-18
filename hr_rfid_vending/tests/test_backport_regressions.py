# -*- coding: utf-8 -*-
"""Regression tests for improvements back-ported from the 19.0 branch to hr_rfid_vending.

Run:  odoo-bin -i hr_rfid_vending --test-enable --test-tags vending_backport
"""
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install', 'vending_backport')
class VendingBackportRegressions(TransactionCase):

    # ---- be4c293: purchase reversal wizard ----------------------------------
    def test_reversal_wizard_wired(self):
        """The reversal wizard model exists, is wired (event_id -> vending event)
        and exposes action_reverse + the idempotency guard."""
        model = self.env['hr.rfid.vending.event.reverse']
        self.assertIn('event_id', model._fields)
        self.assertEqual(model._fields['event_id'].comodel_name, 'hr.rfid.vending.event')
        self.assertTrue(hasattr(model, 'action_reverse'))
        self.assertTrue(hasattr(model, '_is_already_reversed'))

    def test_reversal_wizard_has_acl(self):
        """be4c293 also ships an ir.model.access row so operators can use it."""
        imodel = self.env['ir.model'].search(
            [('model', '=', 'hr.rfid.vending.event.reverse')], limit=1)
        self.assertTrue(imodel, 'reversal wizard model must be registered')
        acls = self.env['ir.model.access'].search([('model_id', '=', imodel.id)])
        self.assertTrue(acls, 'reversal wizard must have at least one ACL row')

    # ---- a58ac6f: multi-company broken-chain tolerance ----------------------
    def test_vending_event_rule_broken_chain(self):
        """Controller-less / global vending events must stay visible (the rule
        tolerates a broken controller_id -> webstack_id -> company_id chain)."""
        rule = self.env.ref(
            'hr_rfid_vending.ir_rule_hr_rfid_vending_event_user_multi_company')
        self.assertIn("('controller_id', '=', False)", rule.domain_force,
                      'vending event rule must tolerate a missing controller (broken chain)')
        self.assertIn("('controller_id.webstack_id.company_id', '=', False)", rule.domain_force,
                      'vending event rule must tolerate a company-less webstack')
