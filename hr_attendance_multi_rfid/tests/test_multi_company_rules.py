# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Regression: the module's multi-company rule on the CORE model
resource.calendar must tolerate company_id=False — core ships global
working calendars (company_id=False) which every employee must see.

Fixed form under test (security XML of this module,
ir_rule_hr_rfid_card_multi_company on resource.calendar):
    [('company_id', 'in', company_ids + [False])]

Note: core's resource module ships NO multi-company rule on
resource.calendar itself — this module's rule is the only one, so the
strict form used to hide every global calendar from all non-superusers.
"""
from odoo.tests.common import TransactionCase, tagged, new_test_user


@tagged("post_install", "-at_install", "rfid_attendance_multi_company")
class TestResourceCalendarMultiCompanyRule(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        other = cls.env['res.company'].sudo().search(
            [('id', '!=', cls.company_a.id)], limit=1)
        cls.company_b = other or cls.env['res.company'].create(
            {'name': 'Calendar Comp Rule Co B'})
        # Plain internal user: core grants base.group_user read on
        # resource.calendar — only the record rule is under test.
        cls.rule_user = new_test_user(
            cls.env,
            login='calendar_comp_rule_user',
            groups='base.group_user',
            name='Calendar Comp Rule User',
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id])],
        )

    def _visible(self, record):
        return self.env['resource.calendar'].with_user(self.rule_user).search(
            [('id', '=', record.id)])

    def test_global_calendar_visible(self):
        """A working calendar with company_id=False is global — it must be
        visible to a company-bound non-superuser."""
        calendar = self.env['resource.calendar'].create({
            'name': 'Comp Rule Global Calendar',
            'company_id': False,
        })
        self.assertEqual(
            self._visible(calendar), calendar,
            'global (no-company) working calendar must be visible to a '
            'company-A user — the company rule must tolerate '
            'company_id=False',
        )

    def test_other_company_calendar_hidden(self):
        """Tolerating False must NOT leak other companies' calendars."""
        calendar = self.env['resource.calendar'].create({
            'name': 'Comp Rule Co-B Calendar',
            'company_id': self.company_b.id,
        })
        self.assertFalse(
            self._visible(calendar),
            'company-B working calendar must stay hidden from a company-A '
            'user',
        )
