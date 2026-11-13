"""What somebody showing the RFID set gets from the demo, and what it never does.

The owner, 12.11.2026: a demo company with data for everything, a scheduled
task that simulates the system at work, and - his hard rule - "the demo
generators must not touch anything once real controllers are attached; they
work only on demo data".
"""

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from ..models.hr_rfid_demo import SIMULATED_UNTIL


@tagged("post_install", "-at_install", "rfid_demo")
class TestTheDemoKeepsWorking(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.webstack = cls.env.ref("hr_rfid.demo_module", raise_if_not_found=False)
        if not cls.webstack:
            cls.skipTest(cls, "the demo data is not loaded")
        cls.Demo = cls.env["hr.rfid.demo"]
        cls.params = cls.env["ir.config_parameter"].sudo()

    def _passages_since(self, moment):
        return self.env["hr.rfid.event.user"].search_count(
            [("event_time", ">", moment)]
        )

    def test_the_demo_has_weeks_of_attendance_made_at_the_doors(self):
        """A fresh demo shows weeks of attendance, today included, made from passages.

        The dashboards and the attendance report read it, and the lists they
        open for "today" are never empty.
        """
        today = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.assertGreater(self._passages_since(today - timedelta(days=40)), 1000)
        rfid_stays = self.env["hr.attendance"].search([("in_mode", "=", "rfid")])
        self.assertGreater(len(rfid_stays.mapped("employee_id")), 10)
        days = self.env["hr.attendance.extra"].search([])
        for figure in ("late_time", "early_come_time", "early_leave_time", "overtime"):
            self.assertTrue(
                days.filtered(lambda d, f=figure: (d[f] or 0) > 0),
                "no day of the demo shows %s" % figure,
            )
        night = self.env.ref("hr.employee_jod")
        self.assertTrue(
            rfid_stays.filtered(
                lambda a: a.employee_id == night
                and a.check_out
                and a.check_out.date() > a.check_in.date()
            ),
            "the night worker has no night",
        )

    def test_the_task_adds_what_happened_since_its_last_run(self):
        """Every run of the task brings the demo up to now, and a second run adds nothing."""
        two_hours_ago = fields.Datetime.now() - timedelta(hours=26)
        self.params.set_param(SIMULATED_UNTIL, fields.Datetime.to_string(two_hours_ago))
        self.env["hr.rfid.event.user"].search(
            [("event_time", ">", two_hours_ago)]
        ).unlink()

        self.Demo._cron_simulate()
        added = self._passages_since(two_hours_ago)
        self.assertGreater(added, 0)

        self.Demo._cron_simulate()
        self.assertEqual(self._passages_since(two_hours_ago), added)

    def test_a_real_module_stops_the_demo(self):
        """NEGATIVE: once a real module is attached, the demo writes nothing."""
        since = fields.Datetime.now() - timedelta(hours=26)
        self.params.set_param(SIMULATED_UNTIL, fields.Datetime.to_string(since))
        self.env["hr.rfid.event.user"].search([("event_time", ">", since)]).unlink()
        self.env["hr.rfid.webstack"].create(
            {
                "name": "A real module",
                "serial": "777777",
                "company_id": self.env.company.id,
            }
        )

        self.assertFalse(self.Demo._demo_hardware())
        self.Demo._cron_simulate()

        self.assertEqual(self._passages_since(since), 0)

    def test_the_demo_module_reached_by_a_device_stops_the_demo(self):
        """NEGATIVE: the demo module itself, once a device talked to it, is no longer demo."""
        self.webstack.sudo().write({"last_ip": "192.168.0.10"})

        self.assertFalse(self.Demo._demo_hardware())

    def test_nobody_outside_the_demo_is_touched(self):
        """NEGATIVE: a person of the company who is not in the demo gets no passage and no cost."""
        outsider = self.env["hr.employee"].create({"name": "Real Colleague"})
        card = self.env["hr.rfid.card"].create(
            {
                "number": "4242424242",
                "employee_id": outsider.id,
                "company_id": self.env.company.id,
            }
        )
        since = fields.Datetime.now() - timedelta(hours=26)
        self.params.set_param(SIMULATED_UNTIL, fields.Datetime.to_string(since))

        self.Demo._cron_simulate()

        self.assertFalse(
            self.env["hr.rfid.event.user"].search_count([("card_id", "=", card.id)])
        )
        self.assertFalse(outsider.hourly_cost)

    def test_a_day_comes_out_the_same_whichever_run_reaches_it(self):
        """The same person on the same day walks the same way in two runs."""
        employee = self.env.ref("hr.employee_mit")
        entrance = self.env.ref("hr_rfid.demo_ctrl_icon110")
        inner = self.env.ref("hr_rfid.demo_ctrl_icon115")
        day = fields.Date.today() - timedelta(days=3)
        first = self.Demo._demo_day(employee, "day", day, entrance, inner)
        second = self.Demo._demo_day(employee, "day", day, entrance, inner)
        self.assertEqual(first, second)
