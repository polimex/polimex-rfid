"""What somebody showing the RFID set gets from the demo, and what it never does.

The owner, 12.11.2026: a demo company with data for everything, a scheduled
task that simulates the system at work, and - his hard rule - "the demo
generators must not touch anything once real controllers are attached; they
work only on demo data".
"""

from datetime import timedelta

from freezegun import freeze_time
from pytz import timezone, utc

from odoo import fields
from odoo.tests.common import HttpCase, TransactionCase, tagged

from odoo.addons.hr_attendance_multi_rfid.tests.common import set_public_holidays_aside

from ..models.hr_rfid_demo import ALSO_SIMULATED_UNTIL, SIMULATED_UNTIL

DEMO_LOG = "odoo.addons.hr_rfid_demo.models.hr_rfid_demo"


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

    def _open_a_demo_door(self):
        door = self.env.ref("hr_rfid.demo_ctrl_icon110").door_ids[:1]
        door.open_door()
        return self.env["hr.rfid.command"].search(
            [("webstack_id", "=", self.webstack.id), ("cmd", "=", "DB")],
            order="id desc",
            limit=1,
        )

    def test_a_door_opened_from_the_screen_of_the_demo_opens(self):
        """A visitor tries the Open button: the demo shows a door that opened,
        not one given up because no module took the command within a minute."""
        command = self._open_a_demo_door()

        self.assertEqual(command.status, "Success")
        self.env["hr.rfid.command"]._ws_republish_cron()
        self.assertEqual(command.status, "Success")

    def test_a_door_of_a_real_site_is_not_answered_by_the_demo(self):
        """NEGATIVE: with a real module attached the demo answers nothing -
        the open waits for the hardware like any other."""
        self.env["hr.rfid.webstack"].create(
            {
                "name": "A real module",
                "serial": "777778",
                "company_id": self.env.company.id,
            }
        )

        command = self._open_a_demo_door()

        self.assertEqual(command.status, "Wait")

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

    def test_nobody_comes_in_on_a_public_holiday(self):
        """On an official holiday the demo company is closed, for everybody.

        Whatever schedule a person is on - the day workers and the night
        workers alike. The working day after it is an ordinary one, so the
        empty day is the holiday and not an empty window.
        """
        # The database's own holidays (the demo's, a localisation's) are set
        # aside, so the only one is made here.
        set_public_holidays_aside(self.env)
        holiday = fields.Date.today() + timedelta(days=30)
        while holiday.weekday() > 3:  # a Monday to Thursday, with a working day after
            holiday += timedelta(days=1)
        company = self.env.ref("base.main_company")
        tz = company.resource_calendar_id.tz or "UTC"
        start = fields.Datetime.to_datetime(fields.Date.to_string(holiday))
        self.env["resource.calendar.leaves"].with_company(company).create(
            {
                "name": "Official holiday",
                "company_id": company.id,
                "calendar_id": False,
                "resource_id": False,
                "date_from": self._utc(start, tz),
                "date_to": self._utc(start + timedelta(hours=23, minutes=59), tz),
            }
        )
        moment = fields.Datetime.to_datetime(fields.Date.to_string(holiday))
        days = {
            day: present
            for day, _people, present in self.Demo._demo_days(
                moment, moment + timedelta(days=1)
            )
        }
        self.assertFalse(days[holiday], "somebody came in on the holiday")
        self.assertTrue(
            any(
                passages
                for _employee, _card, passages in days[holiday + timedelta(days=1)]
            ),
            "nobody came in on the day after",
        )

    @staticmethod
    def _utc(local, tz):
        return timezone(tz).localize(local).astimezone(utc).replace(tzinfo=None)


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


class _TheDemoLoginIsACustomerOfTheServices:
    """What the demo login's portal has, on a demo that was installed long ago."""

    @classmethod
    def _find_the_customer(cls):
        cls.customer = cls.env.ref("base.partner_demo", raise_if_not_found=False)
        cls.badge = cls.env.ref(
            "rfid_service_portal.demo_portal_service_card", raise_if_not_found=False
        )
        cls.service = cls.env.ref(
            "rfid_service_base.demo_service_gym_combo", raise_if_not_found=False
        )
        if not (
            cls.customer
            and cls.badge
            and cls.service
            and cls.env.ref("hr_rfid.demo_module", raise_if_not_found=False)
        ):
            cls.skipTest(cls, "the services add-on's demo is not loaded")
        cls.Demo = cls.env["hr.rfid.demo"]
        cls.params = cls.env["ir.config_parameter"].sudo()
        cls.Sale = cls.env["rfid.service.sale"].sudo()

    @classmethod
    def _long_after_the_install(cls):
        """Everything the customer ever had is long over.

        The demo sale of the services add-on lasts four hours from the
        install. Whatever the demo itself has sold them since - at the install
        or at any run of the task on this database - is put in the past with
        it: the services, the access behind each, the badge and its passages.
        """
        long_ago = fields.Datetime.now() - timedelta(days=100)
        services = cls.Sale.search([("partner_id", "=", cls.customer.id)], order="id")
        for days, service in enumerate(services):
            # A day apart: one service per customer and period.
            start = long_ago + timedelta(days=days)
            end = start + timedelta(hours=4)
            service.access_group_contact_rel.write(
                {"activate_on": start, "expiration": end}
            )
            service.write({"start_date": start, "end_date": end})
        cls.env["hr.rfid.event.user"].search([("card_id", "=", cls.badge.id)]).unlink()
        cls.badge.write(
            {"activate_on": long_ago, "deactivate_on": long_ago + timedelta(hours=4)}
        )
        cls._the_card_task_runs()

    @classmethod
    def _the_card_task_runs(cls):
        """What the system's own task does every minute: badges wake and go to sleep by their period."""
        cls.env["hr.rfid.card"]._update_cards()

    def _the_task_runs_again(self):
        """The next run of the task, a while later.

        Two runs within the same second are one run to the task (it has
        nothing new to simulate and stops at once), so the mark of the last
        run is put back as far as the task's own interval.
        """
        earlier = fields.Datetime.now() - timedelta(minutes=15)
        for mark in (SIMULATED_UNTIL, ALSO_SIMULATED_UNTIL):
            self.params.set_param(mark, fields.Datetime.to_string(earlier))
        self.Demo._cron_simulate()

    def _next_sale_number(self):
        """The number the till gives the next sale. A sale that is tried and
        refused uses one up all the same."""
        numbering = (
            self.env["ir.sequence"].sudo().search([("code", "=", "base.rfid.service")])
        )
        self.assertEqual(len(numbering), 1)
        return numbering.number_next_actual

    def _in_the_portal(self):
        """The services the portal lists for the demo login (/my/rfid_services)."""
        return self.Sale.search([("partner_id", "=", self.customer.id)])

    def _running(self):
        return self._in_the_portal().filtered(lambda sale: sale.state == "progress")

    def _as_if_sold_days_ago(self, days, badge_awake=True):
        """The running service, as the task would have sold it that many days ago
        and then not run since."""
        service = self._running()
        back = timedelta(days=days)
        access = service.access_group_contact_rel
        service.write({"start_date": service.start_date - back})
        access.write({"activate_on": access.activate_on - back})
        self.badge.write({"activate_on": self.badge.activate_on - back})
        if badge_awake:
            self._the_card_task_runs()
        since = fields.Datetime.now() - back - timedelta(days=5)
        for mark in (SIMULATED_UNTIL, ALSO_SIMULATED_UNTIL):
            self.params.set_param(mark, fields.Datetime.to_string(since))
        return service, since

    def _passages(self, since, way=None):
        passages = self.env["hr.rfid.event.user"].search(
            [("card_id", "=", self.badge.id), ("event_time", ">", since)]
        )
        if way is None:
            return passages
        return passages.filtered(lambda event: event.reader_id.reader_type == way)


@tagged("post_install", "-at_install", "rfid_demo")
class TestTheDemoLoginHasAServiceRunning(
    _TheDemoLoginIsACustomerOfTheServices, TransactionCase
):
    """Whoever logs in to the demo finds a service that is running in their portal.

    The owner, when the vending machine was promised (16.11.2026): "think of
    the portal user as well, there is functionality there we have to show".
    On the demo server the only service of the demo login had ended in the
    summer, four hours after the install.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._find_the_customer()
        cls._long_after_the_install()

    def test_the_demo_login_has_a_service_that_runs_now(self):
        """The portal lists a service running today, next to the one that ended long ago."""
        ended = self._in_the_portal()
        self.assertTrue(ended)
        self.assertFalse(self._running(), "the starting point: nothing is running")

        self.Demo._cron_simulate()

        running = self._running()
        now = fields.Datetime.now()
        self.assertEqual(len(running), 1)
        self.assertEqual(running.service_id, self.service)
        self.assertEqual(running.card_id, self.badge)
        self.assertLessEqual(running.start_date, now)
        self.assertGreater(running.end_date, now + timedelta(days=20))
        self.assertEqual(self._in_the_portal(), ended | running)
        self.assertEqual(set(ended.mapped("state")), {"finished"}, "history stays")

    def test_the_badge_in_the_portal_is_valid_again(self):
        """The barcode the portal shows for the service opens the door: the badge is valid for the whole period."""
        self.assertFalse(self.badge.active, "the starting point: the badge ran out")

        self.Demo._cron_simulate()
        self._the_card_task_runs()

        self.assertTrue(self.badge.active)
        self.assertGreaterEqual(self.badge.deactivate_on, self._running().end_date)

    def test_a_badge_made_permanent_still_gets_its_service(self):
        """Somebody trying the demo makes the badge a card that never expires.
        The customer is sold the service all the same, and the badge keeps no
        end date."""
        self.badge.write({"deactivate_on": False, "active": True})

        self.Demo._cron_simulate()

        self.assertEqual(len(self._running()), 1)
        self.assertFalse(self.badge.deactivate_on)

    def test_a_running_service_is_not_sold_twice(self):
        """NEGATIVE: the task runs every quarter of an hour and the customer still
        has one service - and the till's sale numbers are not used up on tries."""
        self.Demo._cron_simulate()
        listed = self._in_the_portal()
        self._the_card_task_runs()
        number = self._next_sale_number()

        self._the_task_runs_again()

        self.assertEqual(self._in_the_portal(), listed)
        self.assertEqual(len(self._running()), 1)
        self.assertEqual(self._next_sale_number(), number, "the till was not asked")

    def test_nobody_else_is_sold_anything(self):
        """NEGATIVE: only the demo login buys, and their phone and e-mail stay as they were."""
        others = [("partner_id", "!=", self.customer.id)]
        sold_to_others = self.Sale.search(others)
        contact = (self.customer.phone, self.customer.email)

        self.Demo._cron_simulate()

        self.assertEqual(self.Sale.search(others), sold_to_others)
        self.assertEqual((self.customer.phone, self.customer.email), contact)

    def test_the_customer_comes_and_every_entry_is_a_visit(self):
        """The service is used: the customer comes in on some evenings and the visits are counted."""
        self.Demo._cron_simulate()
        service, since = self._as_if_sold_days_ago(12)

        self.Demo._cron_simulate()

        entries = self._passages(since, way="0")
        self.assertTrue(entries, "nobody came in twelve days")
        self.assertEqual(service.access_group_contact_rel.visits_counter, len(entries))
        self.assertEqual(
            service.visits,
            service.access_group_contact_rel.permitted_visits - len(entries),
            "the visits left",
        )
        self.assertIn(
            len(self._passages(since, way="1")),
            (len(entries), len(entries) - 1),
            "whoever came in leaves, unless they are still inside",
        )
        self.assertEqual(set(self._passages(since).mapped("event_action")), {"1"})

    def test_nobody_gets_in_without_a_service(self):
        """NEGATIVE: in the days before the service was sold the badge opens nothing."""
        self.Demo._cron_simulate()
        service, since = self._as_if_sold_days_ago(12)

        self.Demo._cron_simulate()

        self.assertFalse(
            self._passages(since).filtered(
                lambda event: event.event_time < service.start_date
            )
        )

    def test_a_badge_that_is_asleep_opens_nothing(self):
        """NEGATIVE: until the system has woken the badge for the new period, the
        customer does not come - no passage, and no "unknown card" at the door."""
        self.Demo._cron_simulate()
        _service, since = self._as_if_sold_days_ago(12, badge_awake=False)
        self.assertFalse(self.badge.active)

        self.Demo._cron_simulate()

        self.assertFalse(self._passages(since))
        self.assertFalse(
            self.env["hr.rfid.event.system"].search_count(
                [
                    ("card_number", "=", self.badge.number),
                    ("timestamp", ">", since),
                ]
            )
        )

    def test_a_service_that_starts_later_is_not_sold_again(self):
        """NEGATIVE: a service bought for later is the customer's service - the
        task does not sell another one every quarter of an hour until it starts."""
        self.Demo._cron_simulate()
        ahead = self._running()
        later = fields.Datetime.now() + timedelta(hours=2)
        ahead.write({"start_date": later})
        ahead.access_group_contact_rel.write({"activate_on": later})
        self.assertEqual(ahead.state, "registered")
        listed = self._in_the_portal()
        number = self._next_sale_number()

        self._the_task_runs_again()

        self.assertEqual(self._in_the_portal(), listed)
        self.assertEqual(self._next_sale_number(), number, "the till was not asked")

    def test_the_last_visit_closes_the_service(self):
        """NEGATIVE: once the visits are used up the service is over and nobody gets in on it."""
        self.Demo._cron_simulate()
        service, since = self._as_if_sold_days_ago(20)
        access = service.access_group_contact_rel
        access.visits_counter = access.permitted_visits - 1

        self.Demo._cron_simulate()

        self.assertEqual(len(self._passages(since, way="0")), 1, "one visit was left")
        self.assertEqual(len(self._passages(since, way="1")), 1, "and they left")
        self.assertEqual(service.state, "finished")
        self.assertFalse(self._running())

    def test_a_used_up_service_is_followed_by_a_new_one(self):
        """The service that ran out stays in the list as finished and the next run sells a new one."""
        self.Demo._cron_simulate()
        used_up, _since = self._as_if_sold_days_ago(3)
        access = used_up.access_group_contact_rel
        access.visits_counter = access.permitted_visits
        self.assertEqual(used_up.state, "finished", "the system closes it itself")

        self._the_task_runs_again()

        running = self._running()
        self.assertEqual(len(running), 1)
        self.assertNotEqual(running, used_up)
        self.assertIn(used_up, self._in_the_portal())

    def test_a_real_module_stops_the_sales_too(self):
        """NEGATIVE: once a real module is attached, the demo sells nothing."""
        self.env["hr.rfid.webstack"].create(
            {
                "name": "A real module",
                "serial": "777779",
                "company_id": self.env.company.id,
            }
        )
        listed = self._in_the_portal()

        self.Demo._cron_simulate()

        self.assertEqual(self._in_the_portal(), listed)

    def test_a_badge_handed_to_somebody_else_is_left_alone(self):
        """NEGATIVE: the badge, once it belongs to another contact, is not the demo's - nobody is sold anything."""
        somebody = self.env["res.partner"].create({"name": "A real customer"})
        self.badge.contact_id = somebody
        sold = self.Sale.search([])

        self.Demo._cron_simulate()

        self.assertEqual(self.Sale.search([]), sold)

    def test_the_till_refusing_does_not_stop_the_demo(self):
        """Somebody trying the demo gives the customer permanent access; the till
        then sells them no service - and the doors of the demo go on working."""
        self.env["hr.rfid.access.group.contact.rel"].create(
            {
                "access_group_id": self.service.access_group_id.id,
                "contact_id": self.customer.id,
            }
        )
        listed = self._in_the_portal()
        since = fields.Datetime.now() - timedelta(hours=26)
        self.params.set_param(SIMULATED_UNTIL, fields.Datetime.to_string(since))
        staff = [("employee_id", "!=", False), ("event_time", ">", since)]
        self.env["hr.rfid.event.user"].search(staff).unlink()

        with self.assertLogs(DEMO_LOG, level="WARNING") as said:
            self.Demo._cron_simulate()

        self.assertIn("was not sold to the demo customer", said.output[0])
        self.assertEqual(self._in_the_portal(), listed, "the till refused")
        self.assertTrue(self.env["hr.rfid.event.user"].search_count(staff))
        self.assertGreater(
            fields.Datetime.to_datetime(self.params.get_param(SIMULATED_UNTIL)), since
        )

    def test_a_service_for_the_very_same_period_does_not_stop_the_demo(self):
        """Somebody trying the demo cancels the service the moment it is sold. The
        system keeps one service per customer and period, so the same one cannot
        be sold again - and the doors of the demo go on working."""
        with freeze_time(fields.Datetime.now()):
            self.Demo._cron_simulate()
            self._running().cancel_sale()
            listed = self._in_the_portal()
            self.assertFalse(self._running())

            with self.assertLogs(DEMO_LOG, level="WARNING") as said:
                self._the_task_runs_again()

            self.assertIn("was not sold to the demo customer", said.output[0])
            self.assertEqual(self._in_the_portal(), listed, "the same period again")
            self.assertEqual(
                fields.Datetime.to_datetime(self.params.get_param(SIMULATED_UNTIL)),
                fields.Datetime.now(),
                "the task went on to its end",
            )


@tagged("post_install", "-at_install", "rfid_demo")
class TestTheDemoLoginSeesTheServiceInThePortal(
    _TheDemoLoginIsACustomerOfTheServices, HttpCase
):
    """The page itself, as the person who logs in to the demo gets it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._find_the_customer()
        cls._long_after_the_install()

    def test_the_services_page_of_the_demo_login_lists_the_running_service(self):
        """Logged in as demo, "RFID Services" in the portal shows the service sold today."""
        self.Demo._cron_simulate()
        running = self._running()
        self.assertEqual(len(running), 1)

        self.authenticate("demo", "demo")
        page = self.url_open("/my/rfid_services")

        self.assertEqual(page.status_code, 200)
        self.assertIn(running.name, page.text)
        self.assertIn(self.service.name, page.text)
