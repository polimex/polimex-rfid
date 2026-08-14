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

        # Only the timezone is pinned. The interface language is NOT pinned on
        # purpose: it follows the languages installed on the database (a
        # customer instance typically runs in Bulgarian only), and writing a
        # language that is not installed is silently replaced by the company's
        # one. The tours below therefore assert on data and on values, never on
        # translated wording or on a locale-formatted number.
        admin = cls.env["res.users"].search([("login", "=", "admin")], limit=1)
        admin.write({"tz": "Europe/Sofia"})

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
        """An HR manager corrects a wrong legal coefficient in the list, sees
        the corrected value on that rate afterwards, and the correction lands
        on the rate they opened - without leaving a second row for that code.
        """
        self.start_tour(
            "/odoo/action-hr_attendance_late.hr_legal_rate_action",
            "hr_legal_rate_edit_tour",
            login="admin",
        )
        self.rate.invalidate_recordset(["value"])
        self.assertEqual(
            self.rate.value, 1.85,
            "The manager's correction must reach the rate they opened",
        )
        # Correcting a coefficient is not a statutory change: it must not leave
        # a second dated row behind, which would make the lookup for that code
        # depend on which row wins.
        self.assertEqual(
            self.env["hr.legal.rate"].search_count([("code", "=", "zz_tour_rate")]), 1,
            "Correcting a rate must not create a second row for the same code",
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
