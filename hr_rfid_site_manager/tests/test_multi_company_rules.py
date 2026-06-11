# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Regression: ir_rule_hr_rfid_site_multi_company must tolerate
company_id=False (global / shared sites).

Fixed form under test (security/hr_rfid_multi_company.xml):
    hr.rfid.site: [('company_id', 'in', company_ids + [False])]
"""
from odoo.tests.common import TransactionCase, tagged, new_test_user


@tagged("post_install", "-at_install", "rfid_site_manager")
class TestSiteMultiCompanyRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        other = cls.env['res.company'].sudo().search(
            [('id', '!=', cls.company_a.id)], limit=1)
        cls.company_b = other or cls.env['res.company'].create(
            {'name': 'Site Comp Rule Co B'})
        # Guard has full ACL on hr.rfid.site — only the record rule
        # is under test. Bound to company A ONLY.
        cls.rule_user = new_test_user(
            cls.env,
            login='site_comp_rule_guard',
            groups='base.group_user,hr_rfid_site_manager.group_guard',
            name='Site Comp Rule Guard',
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id])],
        )

    def _visible(self, record):
        return self.env['hr.rfid.site'].with_user(self.rule_user).search(
            [('id', '=', record.id)])

    def test_global_site_visible(self):
        """A site with company_id=False is shared — must be visible."""
        site = self.env['hr.rfid.site'].create({
            'name': 'Comp Rule Global Site',
            'company_id': False,
        })
        self.assertEqual(
            self._visible(site), site,
            'global (no-company) site must be visible to a company-A user '
            '— the company rule must tolerate company_id=False',
        )

    def test_other_company_site_hidden(self):
        """Tolerating False must NOT leak other companies' sites."""
        site = self.env['hr.rfid.site'].create({
            'name': 'Comp Rule Co-B Site',
            'company_id': self.company_b.id,
        })
        self.assertFalse(
            self._visible(site),
            'company-B site must stay hidden from a company-A user',
        )
