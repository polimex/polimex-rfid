"""What somebody showing the RFID set gets from the demo, and what it never does.

The owner, 12.11.2026: a demo company with data for everything, a scheduled
task that simulates the system at work, and - his hard rule - "the demo
generators must not touch anything once real controllers are attached; they
work only on demo data".
"""

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from ..models.hr_rfid_demo import ALSO_SIMULATED_UNTIL, SIMULATED_UNTIL


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

    def test_the_demo_hardware_answers_what_it_is_asked(self):
        """The list of commands of the demo shows hardware that answers, not a queue that only grows."""
        self.env.ref("hr_rfid.demo_ctrl_icon110").synchronize_clock_cmd()
        since = fields.Datetime.now() - timedelta(hours=26)
        self.params.set_param(SIMULATED_UNTIL, fields.Datetime.to_string(since))

        self.Demo._cron_simulate()

        self.assertFalse(
            self.env["hr.rfid.command"].search(
                [
                    ("webstack_id", "=", self.webstack.id),
                    ("status", "in", ("Wait", "Process")),
                ]
            )
        )

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


@tagged("post_install", "-at_install", "rfid_demo", "rfid_demo_vending")
class TestTheDemoShowsTheVendingMachine(TransactionCase):
    """The demo has a vending machine people buy from.

    The owner, looking at the demo server (16.11.2026): "I see no demo events
    for the vending. Why do we have none?" - and, when the machine was
    promised: "think of the portal user as well, there is functionality there
    we have to show".
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.machine = cls.env.ref(
            "hr_rfid_vending.demo_ctrl_vending", raise_if_not_found=False
        )
        if not cls.machine or not cls.env.ref(
            "hr_rfid.demo_module", raise_if_not_found=False
        ):
            cls.skipTest(cls, "the vending add-on's demo is not loaded")
        cls.Demo = cls.env["hr.rfid.demo"]
        cls.params = cls.env["ir.config_parameter"].sudo()
        cls.weeks_ago = fields.Datetime.now() - timedelta(days=40)

    def _sales(self, since, extra=()):
        """The sales the machine reported - not the handful the vending add-on's
        own demo data writes down as records."""
        written_down = (
            self.env["ir.model.data"]
            .sudo()
            .search(
                [
                    ("model", "=", "hr.rfid.vending.event"),
                    ("module", "=", "hr_rfid_vending"),
                ]
            )
            .mapped("res_id")
        )
        return self.env["hr.rfid.vending.event"].search(
            [
                ("controller_id", "=", self.machine.id),
                ("event_action", "=", "47"),
                ("event_time", ">", since),
                ("id", "not in", written_down),
                *extra,
            ]
        )

    def _simulate_the_last_day_again(self):
        since = fields.Datetime.now() - timedelta(hours=26)
        for mark in (SIMULATED_UNTIL, ALSO_SIMULATED_UNTIL):
            self.params.set_param(mark, fields.Datetime.to_string(since))
        self._sales(since).unlink()
        self.Demo._cron_simulate()
        return since

    def test_the_last_day_simulated_again_has_sales(self):
        """The premise of the negatives below: a day simulated again does sell."""
        since = self._simulate_the_last_day_again()

        if fields.Datetime.now().weekday() < 5 and since.weekday() < 5:
            self.assertTrue(self._sales(since))

    def test_a_demo_already_running_gets_the_machines_weeks_at_its_next_run(self):
        """A demo installed before it had a machine: the next run fills the machine's weeks in.

        The doors' days are not walked again - nobody passes a door twice
        because the machine arrived.
        """
        an_hour_ago = fields.Datetime.now() - timedelta(hours=1)
        self.params.set_param(SIMULATED_UNTIL, fields.Datetime.to_string(an_hour_ago))
        self.params.search([("key", "=", ALSO_SIMULATED_UNTIL)]).unlink()
        self._sales(self.weeks_ago).unlink()
        staff_passages = [
            ("employee_id", "!=", False),
            ("event_time", "<", an_hour_ago),
        ]
        at_the_doors = self.env["hr.rfid.event.user"].search_count(staff_passages)

        self.Demo._cron_simulate()

        self.assertGreater(
            len(self._sales(self.weeks_ago, [("event_time", "<", an_hour_ago)])), 50
        )
        self.assertEqual(
            self.env["hr.rfid.event.user"].search_count(staff_passages), at_the_doors
        )

    def test_people_buy_at_the_machine_and_their_credit_goes_down(self):
        """Weeks of sales, each with what was bought and by whom, paid from the buyer's credit."""
        by_card = self._sales(self.weeks_ago, [("employee_id", "!=", False)])

        self.assertGreater(len(by_card), 50)
        self.assertGreater(len(by_card.mapped("employee_id")), 5)
        self.assertFalse(
            by_card.filtered(lambda sale: not sale.item_sold_id),
            "a sale that does not say what was bought",
        )
        paid = self.env["hr.rfid.vending.balance.history"].search(
            [("vending_event_id", "in", by_card.ids)]
        )
        self.assertEqual(len(paid), len(by_card), "every card sale is paid for")
        self.assertFalse(paid.filtered(lambda line: line.balance_change >= 0))

    def test_the_list_of_the_last_days_is_never_empty(self):
        """Whoever opens the vending events finds sales of the last working days."""
        self.assertTrue(self._sales(fields.Datetime.now() - timedelta(days=4)))

    def test_coins_end_up_in_the_machine(self):
        """Sales without a card are paid in coins, and the machine's cash says so."""
        in_coins = self._sales(self.weeks_ago, [("employee_id", "=", False)])

        self.assertTrue(in_coins)
        self.assertGreater(
            self.machine.cash_contained,
            sum(in_coins.mapped("transaction_price")) - 0.01,
        )

    def test_nobody_buys_on_credit_they_do_not_have(self):
        """NEGATIVE: somebody with nothing left at the machine is sold nothing."""
        people = [employee for employee, _card, _kind in self.Demo._demo_people()]
        for employee in people:
            employee.sudo().write(
                {
                    "hr_rfid_vending_balance": 0,
                    "hr_rfid_vending_recharge_balance": 0,
                    "hr_rfid_vending_negative_balance": False,
                }
            )

        since = self._simulate_the_last_day_again()

        self.assertFalse(self._sales(since, [("employee_id", "!=", False)]))

    def test_a_real_module_stops_the_machine_too(self):
        """NEGATIVE: once a real module is attached, the demo machine sells nothing."""
        self.env["hr.rfid.webstack"].create(
            {
                "name": "A real module",
                "serial": "777778",
                "company_id": self.env.company.id,
            }
        )

        since = self._simulate_the_last_day_again()

        self.assertFalse(self._sales(since))

    def test_a_machine_moved_to_real_hardware_is_left_alone(self):
        """NEGATIVE: the demo machine, once it is no longer on the demo module, is not the demo's."""
        elsewhere = self.env["hr.rfid.ctrl"].search(
            [("id", "!=", self.machine.id)], limit=1
        )
        self.assertFalse(
            self.Demo._demo_vending_machine(elsewhere.webstack_id.browse()),
            "no demo module, no demo machine",
        )

    def test_the_customer_with_a_portal_login_has_passages_of_their_own(self):
        """What the portal shows under "my events" moves: the customer came by in the last weeks.

        Asked of a demo that was running before this visitor existed, so the
        passages are the ones the next run of the task makes.
        """
        customer = self.env.ref("base.partner_demo_portal", raise_if_not_found=False)
        card = self.env.ref("hr_rfid_portal.demo_portal_card", raise_if_not_found=False)
        if not customer or not card:
            self.skipTest("the portal add-on's demo is not loaded")
        theirs = [("contact_id", "=", customer.id), ("event_time", ">", self.weeks_ago)]
        self.env["hr.rfid.event.user"].search(theirs).unlink()
        self.params.search([("key", "=", ALSO_SIMULATED_UNTIL)]).unlink()

        self.Demo._cron_simulate()

        passages = self.env["hr.rfid.event.user"].search(theirs)
        self.assertGreater(len(passages), 10)
        self.assertEqual(passages.mapped("card_id"), card)
        self.assertTrue(
            passages.filtered(
                lambda event: event.event_time
                > fields.Datetime.now() - timedelta(days=8)
            ),
            "nothing of the last week",
        )
