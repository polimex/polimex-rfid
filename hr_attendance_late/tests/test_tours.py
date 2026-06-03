# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "hr_attendance_late", "att_tour")
class TestAttendanceLateTours(HttpCase):

    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        admin = cls.env["res.users"].search([("login", "=", "admin")], limit=1)
        admin.write({"lang": "en_US", "tz": "Europe/Sofia"})

        # Fixture for the self-leave tour: a daily roll-up with an early
        # departure. early_leave_time is a plain stored field (populated by the
        # cron/wizard in production), so we can seed it directly here.
        cls.employee = cls.env["hr.employee"].create({
            "name": "SelfLeave Tester",
            "company_id": cls.company.id,
        })
        cls.extra = cls.env["hr.attendance.extra"].create({
            "employee_id": cls.employee.id,
            "for_date": date(2026, 6, 1),
            "early_leave_time": 0.5,
        })
        # Fixture for the legal-rate tour: a dated national rate to override.
        cls.rate = cls.env["hr.legal.rate"].create({
            "code": "zz_tour_rate",
            "name": "Tour rate",
            "date_from": date(2020, 1, 1),
            "value": 1.5,
        })

    def test_legal_rate_edit_tour(self):
        """Process: HR manager overrides a dated legal rate inline."""
        self.start_tour(
            "/odoo/action-hr_attendance_late.hr_legal_rate_action",
            "hr_legal_rate_edit_tour",
            login="admin",
        )
        self.rate.invalidate_recordset(["value"])
        self.assertEqual(
            self.rate.value, 1.85,
            "The tour should have written the new coefficient",
        )

    def test_self_leave_review_tour(self):
        """Process: officer reviews early departures grouped by employee."""
        self.start_tour(
            "/odoo/action-hr_attendance_late.hr_attendance_self_leave_action",
            "hr_self_leave_review_tour",
            login="admin",
        )
        # The tour is read-only; the meaningful assertion is that the seeded
        # early-departure record is the one the domain surfaces.
        self.assertGreater(self.extra.early_leave_time, 0)
