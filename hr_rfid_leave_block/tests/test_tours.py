# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "rfid_leave_block", "rfid_leave_block_tour")
class TestLeaveBlockTour(HttpCase):

    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        admin = cls.env["res.users"].search([("login", "=", "admin")], limit=1)
        admin.write({
            "lang": "en_US",
            "tz": "Europe/Sofia",
            # Approving as the Time Off Officer (leave_validation_type='hr').
            "group_ids": [(4, cls.env.ref("hr_holidays.group_hr_holidays_manager").id)],
        })

        cls.employee = cls.env["hr.employee"].create({
            "name": "LeaveBlock Tester",
            "company_id": cls.company.id,
        })
        cls.card = cls.env["hr.rfid.card"].create({
            "number": "9000000777",
            "card_input_type": "w34",
            "employee_id": cls.employee.id,
            "company_id": cls.company.id,
        })
        # A leave type that approves in a single step and needs no allocation,
        # so the only remaining action is the UI "Approve" click.
        cls.leave_type = cls.env["hr.leave.type"].create({
            "name": "LeaveBlock Paid Off",
            "requires_allocation": False,
            "leave_validation_type": "hr",
            "company_id": cls.company.id,
        })
        cls.leave = cls.env["hr.leave"].create({
            "name": "LeaveBlock holiday",
            "employee_id": cls.employee.id,
            "holiday_status_id": cls.leave_type.id,
            "request_date_from": date(2026, 12, 15),
            "request_date_to": date(2026, 12, 15),
        })
        if cls.leave.state == "draft":
            cls.leave.action_confirm()

    def test_leave_approval_blocks_cards_tour(self):
        """Process: officer approves a leave → cards suspended + block logged."""
        self.assertTrue(self.card.active, "Card starts active")
        self.assertFalse(
            self.env["hr.rfid.leave.block"].search([("leave_id", "=", self.leave.id)]),
            "No block before approval",
        )

        self.start_tour(
            "/odoo/action-hr_holidays.hr_leave_action_action_approve_department/%d"
            % self.leave.id,
            "hr_rfid_leave_block_approve_tour",
            login="admin",
        )

        self.assertEqual(self.leave.state, "validate", "Leave got approved")
        block = self.env["hr.rfid.leave.block"].search([
            ("leave_id", "=", self.leave.id),
        ])
        self.assertEqual(len(block), 1, "Exactly one block recorded")
        self.assertEqual(block.state, "active")
        self.assertIn(
            self.card, block.with_context(active_test=False).blocked_card_ids,
            "The card is in the suspended snapshot",
        )
        self.card.invalidate_recordset(["active"])
        self.assertFalse(self.card.active, "Card was suspended on approval")
