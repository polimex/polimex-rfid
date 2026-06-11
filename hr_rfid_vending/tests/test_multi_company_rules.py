# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Regression tests for the vending event multi-company record rule.

Regression: ir_rule_hr_rfid_vending_event_user_multi_company used
[('controller_id.webstack_id.company_id', 'in', company_ids)], which hides
every event whose webstack has no company (company_id=False) from all
non-superusers. The fixed domain is
['|', ('controller_id.webstack_id.company_id', '=', False),
      ('controller_id.webstack_id.company_id', 'in', company_ids)]
— mirroring hr_rfid's own rules for hr.rfid.reader / hr.rfid.event.system.

Pattern follows helpdesk_mgmt tests.test_helpdesk_security
.TestHelpdeskMultiCompanyRules: with_user(non-superuser).search()
visibility assertions.
"""
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('rfid_vending', 'rfid_vending_multi_company', 'post_install', '-at_install')
class TestVendingEventMultiCompanyRule(TransactionCase):
    """The global company rule must tolerate company_id=False on the
    controller -> webstack chain without leaking other companies' events."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        # Reuse an existing second company when available (common.py pattern),
        # otherwise create a bare one — account/stock side effects roll back.
        cls.company_b = cls.env['res.company'].search(
            [('id', '!=', cls.company_a.id)], limit=1)
        if not cls.company_b:
            cls.company_b = cls.env['res.company'].create(
                {'name': 'Vending MC Rule Co B'})

        # Non-superuser bound to company A only. group_operator implies
        # group_customer (read ACL on vending events) and carries the
        # [(1,'=',1)] group rule, so visibility reduces exactly to the
        # global multi-company rule under test. Operator also bypasses the
        # employee_id Python filter in VendingEvents.search().
        cls.user_a = cls.env['res.users'].with_context(
            no_reset_password=True).create({
                'name': 'Vending MC User A',
                'login': 'vending_mc_user_a',
                'email': 'vending_mc_user_a@example.com',
                'company_id': cls.company_a.id,
                'company_ids': [(6, 0, [cls.company_a.id])],
                'group_ids': [(6, 0, [
                    cls.env.ref('base.group_user').id,
                    cls.env.ref('hr_rfid_vending.group_operator').id,
                ])],
            })

        cls.event_a = cls._make_event_chain('A', cls.company_a.id, '911001')
        cls.event_b = cls._make_event_chain('B', cls.company_b.id, '911002')
        # NULL-company chain: explicit company_id=False on the webstack
        # (default is env.company, so the key must be passed explicitly).
        cls.event_null = cls._make_event_chain('NULL', False, '911003')

    @classmethod
    def _make_event_chain(cls, label, company_id, serial):
        """Build webstack -> controller -> reader -> vending event."""
        webstack = cls.env['hr.rfid.webstack'].create({
            'name': 'MC Test Stack %s' % label,
            'serial': serial,
            'company_id': company_id,
            'tz': 'Europe/Sofia',
            'active': True,
        })
        ctrl = cls.env['hr.rfid.ctrl'].create({
            'name': 'MC Test Vending %s' % label,
            'ctrl_id': int(serial[-1]),
            'hw_version': '16',
            'webstack_id': webstack.id,
        })
        reader = cls.env['hr.rfid.reader'].create({
            'name': 'MC Test Reader %s' % label,
            'number': 1,
            'reader_type': '0',
            'controller_id': ctrl.id,
        })
        return cls.env['hr.rfid.vending.event'].create({
            'event_action': '47',
            'event_time': fields.Datetime.now() - timedelta(minutes=1),
            'controller_id': ctrl.id,
            'ctrl_addr': ctrl.ctrl_id,
            'reader_id': reader.id,
        })

    def _visible_ids(self):
        return self.env['hr.rfid.vending.event'].with_user(self.user_a).search([
            ('id', 'in', (self.event_a | self.event_b | self.event_null).ids)
        ]).ids

    def test_own_company_event_visible(self):
        """Sanity: an event on a company-A webstack stays visible to a
        company-A user."""
        self.assertIn(
            self.event_a.id, self._visible_ids(),
            "Event on the user's own company webstack must be visible",
        )

    def test_no_company_webstack_event_visible(self):
        """Regression: an event whose controller->webstack chain ends in
        company_id=False is shared — a company-bound user must see it."""
        self.assertIn(
            self.event_null.id, self._visible_ids(),
            "Event on a no-company (shared) webstack must be visible to a "
            "company-A user — the rule must tolerate company_id=False",
        )

    def test_other_company_event_stays_hidden(self):
        """Loosening for False must NOT leak other companies' events."""
        self.assertNotIn(
            self.event_b.id, self._visible_ids(),
            "Event on a company-B webstack must stay hidden from a "
            "company-A user",
        )
