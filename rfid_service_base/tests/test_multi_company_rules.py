# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Regression: ir_rule_rfid_service_tag_multi_company must tolerate
company_id=False (global / shared service tags).

Fixed form under test (security/rfid_services_multi_company.xml):
    rfid.service.tags: [('company_id', 'in', company_ids + [False])]
"""
from uuid import uuid4

from odoo.tests.common import TransactionCase, tagged, new_test_user


@tagged("post_install", "-at_install", "rfid_service")
class TestServiceTagMultiCompanyRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        other = cls.env['res.company'].sudo().search(
            [('id', '!=', cls.company_a.id)], limit=1)
        cls.company_b = other or cls.env['res.company'].create(
            {'name': 'Tag Comp Rule Co B'})
        # group_card_user (implies base.group_user) has read ACL on
        # rfid.service.tags — only the record rule is under test.
        cls.rule_user = new_test_user(
            cls.env,
            login='tag_comp_rule_user',
            groups='rfid_service_base.group_card_user',
            name='Tag Comp Rule User',
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id])],
        )

    @classmethod
    def _create_tag(cls, company_id):
        # rfid.service.tags has a global unique(name) constraint
        return cls.env['rfid.service.tags'].create({
            'name': 'Comp Rule Tag %s' % uuid4().hex[:8],
            'company_id': company_id,
        })

    def _visible(self, record):
        return self.env['rfid.service.tags'].with_user(self.rule_user).search(
            [('id', '=', record.id)])

    def test_global_tag_visible(self):
        """A service tag with company_id=False is shared — must be visible."""
        tag = self._create_tag(False)
        self.assertEqual(
            self._visible(tag), tag,
            'global (no-company) service tag must be visible to a company-A '
            'user — the company rule must tolerate company_id=False',
        )

    def test_other_company_tag_hidden(self):
        """Tolerating False must NOT leak other companies' tags."""
        tag = self._create_tag(self.company_b.id)
        self.assertFalse(
            self._visible(tag),
            'company-B service tag must stay hidden from a company-A user',
        )
