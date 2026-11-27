"""A demo company whose doors keep being used.

Every passage below is a report of the demo module, handed to the same entry a
real module reaches (hr.rfid.webstack._hw_parse_event, the websocket path's
seam: the queued commands are not answered per event). So the attendance, the
zones, the lateness and the overtime of the demo come out of the code a
customer runs, not out of records written to look like its result. Core makes
the same move for its demo payment provider (payment_demo: the simulated
notification enters through payment.transaction._process).

It works only on the demo hardware of hr_rfid's demo data, found by xml id,
and only while that is all the database has: one module that is not ours, or
ours having ever been reached by a real device, and nothing is simulated.
"""

import logging
import random
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from psycopg2 import errors as pgerrors

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)

#: How far back the first run reaches, so a fresh demo has weeks to show.
BACKFILL_DAYS = 45
#: The moment the simulation has reached (naive UTC, as Odoo stores time).
SIMULATED_UNTIL = "hr_rfid_demo.simulated_until"
#: The same for what joined later: the portal customer and the vending machine.
ALSO_SIMULATED_UNTIL = "hr_rfid_demo.vending_and_portal_simulated_until"
#: The demo module and controllers of hr_rfid's demo data.
DEMO_WEBSTACK = "hr_rfid.demo_module"
ENTRANCE_CTRL = "hr_rfid.demo_ctrl_icon110"
INNER_CTRL = "hr_rfid.demo_ctrl_icon115"
#: Who works in the demo, by their xml ids in hr's demo data. People the leave
#: showcases send on leave (hr.employee_al, hr.employee_qdp) are left out: their
#: badges are suspended there on purpose.
DAY_WORKERS = (
    "hr.employee_admin",
    "hr.employee_ngh",
    "hr.employee_chs",
    "hr.employee_mit",
    "hr.employee_niv",
    "hr.employee_stw",
    "hr.employee_fme",
    "hr.employee_fpi",
    "hr.employee_jth",
    "hr.employee_vad",
    "hr.employee_han",
    "hr.employee_jve",
    "hr.employee_jep",
    "hr.employee_lur",
    "hr.employee_hne",
)
NIGHT_WORKERS = ("hr.employee_jod", "hr.employee_jgo")
SATURDAY_WORKERS = ("hr.employee_han", "hr.employee_jve")
VISITOR_CARD = "hr_rfid.demo_card_2"
#: The customer with a portal login (hr_rfid_portal's demo): what they see
#: under "my events" has to move as well.
PORTAL_GUEST_CARD = "hr_rfid_portal.demo_portal_card"
#: The demo login (rfid_service_portal's demo gives it a service badge) is the
#: customer of the services: the demo sells them this service whenever they
#: have none, so their portal shows one that is running.
SERVICE_CUSTOMER = "base.partner_demo"
SERVICE_BADGE = "rfid_service_portal.demo_portal_service_card"
SERVICE_SOLD = "rfid_service_base.demo_service_gym_combo"
#: The vending machine of hr_rfid_vending's demo, on the demo module.
VENDING_MACHINE = "hr_rfid_vending.demo_ctrl_vending"
SENSOR = "hr_rfid.demo_th_sensor_server_room"
#: Controller event codes (hr_rfid/models/hr_rfid_webstack_hw_events.py).
GRANTED = 3
DENIED = 4
EXIT_BUTTON = 21
DOOR_HELD_OPEN = 25
DOOR_FORCED = 26
POWER_ON = 30
CREDIT_REQUEST = 64
SALE = 47
# How many places the simulated controller numbers its events over before it
# starts again, as a controller's memory does.
EVENT_MEMORY_PLACES = 3000
CREDIT_RETURNED = 49
#: What a report carries when it has nothing of its own to say.
NO_DATA = "00000000000000"
NO_CARD = "0000000000"
#: What a demo person starts with at the machine, and gets again every month
#: through the vending add-on's own refill.
VENDING_STARTING_CREDIT = 30.0
#: Readers of the entrance controller: 1 lets people in, 2 lets them out
#: (hr_attendance_multi_rfid's demo makes it the exit of the attendance zone).
WAY_IN = 1
WAY_OUT = 2
SEED = 20261113


class HrRfidDemo(models.AbstractModel):
    _name = "hr.rfid.demo"
    _description = "RFID demo simulation"

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------
    @api.model
    def _demo_backfill(self):
        """At install: the weeks before today, so the demo has a history."""
        self._demo_simulate_until(fields.Datetime.now())

    @api.model
    def _cron_simulate(self):
        """The scheduled task: everything that happened since the last run."""
        self._demo_simulate_until(fields.Datetime.now())

    # ------------------------------------------------------------------
    # The guard
    # ------------------------------------------------------------------
    @api.model
    def _demo_hardware(self):
        """The demo module, or nothing when the database has real hardware.

        Real hardware is any module that is not the demo one, and the demo one
        once a device has reached it (it then has an address and a time).
        """
        webstack = self.env.ref(DEMO_WEBSTACK, raise_if_not_found=False)
        if not webstack:
            return self.env["hr.rfid.webstack"]
        others = (
            self.env["hr.rfid.webstack"]
            .sudo()
            .with_context(active_test=False)
            .search_count([("id", "!=", webstack.id)])
        )
        if others or webstack.updated_at or webstack.last_ip or not webstack.active:
            return self.env["hr.rfid.webstack"]
        return webstack.sudo()

    # ------------------------------------------------------------------
    # The simulation
    # ------------------------------------------------------------------
    @api.model
    def _demo_simulate_until(self, until):
        webstack = self._demo_hardware()
        if not webstack:
            _logger.info(
                "RFID demo: not simulating - the database has hardware that is "
                "not the demo module, or the demo module was reached by a device."
            )
            return 0
        params = self.env["ir.config_parameter"].sudo()
        since = self._demo_simulated_until(SIMULATED_UNTIL, until)
        # The vending machine and the portal customer joined the demo after
        # the doors. They keep a mark of their own, so a demo that was already
        # running gets their weeks of history at its next run instead of none.
        also_since = self._demo_simulated_until(ALSO_SIMULATED_UNTIL, until)
        if since >= until and also_since >= until:
            return 0
        machine = self._demo_vending_machine(webstack)
        self._demo_vending_credit(machine)
        badge = self._demo_service_badge()
        self._demo_keep_a_service_running(badge)
        reports = self._demo_passages(since, until)
        reports += self._demo_also(also_since, until, machine, badge)
        reports.sort(key=lambda report: report[0])
        reported = 0
        for moment, ctrl, reader, card, event_n, *data in reports:
            if event_n == SALE and card and not self._demo_can_pay(card, ctrl, *data):
                # The machine sells on the credit it was told. Out of credit,
                # the person's request is all that is left of the visit.
                continue
            if (
                badge
                and card == badge
                and not self._demo_may_pass(badge, reader, moment)
            ):
                # No service running at that moment, no visit.
                continue
            self._demo_report(
                webstack,
                ctrl,
                reader,
                card,
                moment,
                event_n,
                *data,
                place=reported % EVENT_MEMORY_PLACES + 1,
            )
            reported += 1
        readings = self._demo_environment_readings(since, until)
        self._demo_hourly_costs()
        self._demo_answer_commands(webstack)
        for mark in (SIMULATED_UNTIL, ALSO_SIMULATED_UNTIL):
            params.set_param(mark, fields.Datetime.to_string(until))
        _logger.info(
            "RFID demo: %d reports and %d sensor readings simulated from %s to %s",
            reported,
            readings,
            min(since, also_since),
            until,
        )
        return reported

    @api.model
    def _demo_simulated_until(self, mark, until):
        """Where a part of the demo has got to; its first run starts weeks back."""
        reached = self.env["ir.config_parameter"].sudo().get_param(mark)
        if reached:
            return fields.Datetime.to_datetime(reached)
        return until - timedelta(days=BACKFILL_DAYS)

    @api.model
    def _demo_answer_commands(self, webstack):
        """Close what the system asked of the demo module, as hardware would.

        Passages, schedules and changes of access queue commands for the
        controllers - the clock, the status reading, the cards. A real module
        carries each out and answers; the demo one has nobody behind it, so
        they would pile up for ever and the list of commands would show a
        site whose hardware never answers.
        """
        commands = (
            self.env["hr.rfid.command"]
            .sudo()
            .search(
                [
                    ("webstack_id", "=", webstack.id),
                    ("status", "in", ("Wait", "Process")),
                ]
            )
        )
        commands.write({"status": "Success", "ex_timestamp": fields.Datetime.now()})
        return len(commands)

    @api.model
    def _demo_environment_readings(self, since, until):
        """The server-room sensor of the demo reports every two hours.

        Through write_log, the method the controller's temperature events
        reach. Coolest before dawn, warmest mid-afternoon, plus noise.
        """
        sensor = self.env.ref(SENSOR, raise_if_not_found=False)
        if not sensor:
            return 0
        readings = 0
        stamp = datetime.combine(since.date(), time(0, 0))
        while stamp <= until:
            if stamp > since:
                rng = random.Random("%s-th-%s" % (SEED, stamp.isoformat()))
                swing = 1.6 * (1 - abs(stamp.hour - 15) / 12.0)
                temperature = round(21.5 + swing + rng.uniform(-0.4, 0.4), 1)
                humidity = round(43.0 - swing * 2 + rng.uniform(-1.5, 1.5), 1)
                sensor.sudo().write_log(stamp, {"t": temperature, "h": humidity})
                readings += 1
            stamp += timedelta(hours=2)
        return readings

    @api.model
    def _demo_hourly_costs(self):
        """The demo people get an hourly cost, so the labour cost has figures.

        Only the people of the demo, and only those who still have none: an
        hourly cost somebody entered is theirs.
        """
        employees = self.env["hr.employee"]
        for xmlid in DAY_WORKERS + NIGHT_WORKERS:
            employees |= self.env.ref(xmlid, raise_if_not_found=False) or employees
        for index, employee in enumerate(employees.sorted("id")):
            if not employee.hourly_cost:
                # 7.50 to 13.75 an hour, so the cost by person and department
                # differs visibly.
                employee.sudo().hourly_cost = 7.5 + (index % 6) * 1.25
        self.env["hr.attendance.extra"].sudo().search(
            [("employee_id", "in", employees.ids)]
        )._compute_actual_work_time_cost()

    @api.model
    def _demo_report(
        self, webstack, ctrl, reader, card, moment, event_n, data=NO_DATA, place=1
    ):
        """One report of the demo module, as the device sends it.

        The device speaks its own local time; the webstack turns it back into
        UTC with the same offset (hr.rfid.webstack.get_ws_time).

        :param data: what the report says besides who and when - a vending
                     machine names the item and the price there
        :param place: where the event sits in the controller's memory. A
                      device gives every event its own place, and a sale is
                      told from its repeat by the place and the time: two
                      sales of one second must not look like one sale
        """
        local = moment + webstack._get_tz_offset()
        date_format, time_format = webstack.time_format.split(" ")
        webstack.with_context(ws_skip_piggyback=True)._hw_parse_event(
            {
                "convertor": webstack.serial,
                "event": {
                    "bos": place,
                    "tos": place,
                    "card": card.number if card else NO_CARD,
                    "cmd": "FA",
                    "date": local.strftime(date_format),
                    "time": local.strftime(time_format),
                    "day": local.isoweekday() % 7,
                    "dt": data,
                    "err": 0,
                    "event_n": event_n,
                    "id": ctrl.ctrl_id,
                    "reader": reader,
                },
            }
        )

    @api.model
    def _demo_days(self, since, until):
        """The days of a window, each with who is in on it.

        Each person's day is drawn from a seed of the person and the day, so a
        day comes out the same whichever run reaches it first, and whoever
        asks for it.

        :return: [(day, people, present)] - people as _demo_people gives them,
                 present as (employee, card, that person's day at the doors)
        """
        entrance = self.env.ref(ENTRANCE_CTRL, raise_if_not_found=False)
        inner = self.env.ref(INNER_CTRL, raise_if_not_found=False)
        if not entrance:
            return []
        people = self._demo_people()
        # A day somebody already has attendance the doors did not make (the
        # showcases of the other modules enter some by hand) is theirs: the
        # doors stay quiet for that person that day, so no day gets two
        # overlapping stays.
        handwritten = {
            (stay.employee_id.id, stay.check_in.date())
            for stay in self.env["hr.attendance"]
            .sudo()
            .search(
                [
                    ("employee_id", "in", [p[0].id for p in people]),
                    ("in_mode", "!=", "rfid"),
                    ("check_in", ">=", since - timedelta(days=2)),
                ]
            )
        }
        days = []
        day = since.date() - timedelta(days=1)
        while day <= until.date():
            present = [
                (employee, card, self._demo_day(employee, kind, day, entrance, inner))
                for employee, card, kind in people
                if (employee.id, day) not in handwritten
                and not employee._demo_is_away(day)
            ]
            days.append((day, people, present))
            day += timedelta(days=1)
        return days

    @api.model
    def _demo_passages(self, since, until):
        """Every passage of the window, in the order the doors saw them.

        :return: [(moment, controller, reader, card, event)]
        """
        entrance = self.env.ref(ENTRANCE_CTRL, raise_if_not_found=False)
        inner = self.env.ref(INNER_CTRL, raise_if_not_found=False)
        passages = []
        for day, people, present in self._demo_days(since, until):
            for _employee, card, at_the_doors in present:
                passages += [
                    (moment, ctrl, reader, card, event_n)
                    for moment, ctrl, reader, event_n in at_the_doors
                ]
            passages += self._demo_day_extras(day, entrance, inner, people)
        return sorted(
            (p for p in passages if since < p[0] <= until), key=lambda p: p[0]
        )

    @api.model
    def _demo_also(self, since, until, machine, badge):
        """What joined the demo after the doors.

        The portal customer, the vending machine and the customer of the
        services.

        :param machine: the demo vending machine, when there is one
        :param badge: the badge of the service customer, when there is one
        :return: [(moment, controller, reader, card, event)], with the
                 report's data as a sixth item where the machine speaks
        """
        entrance = self.env.ref(ENTRANCE_CTRL, raise_if_not_found=False)
        inner = self.env.ref(INNER_CTRL, raise_if_not_found=False)
        reports = []
        for day, _people, present in self._demo_days(since, until):
            reports += self._demo_portal_guest(day, entrance, inner)
            reports += self._demo_service_customer(day, entrance, badge)
            if not machine:
                continue
            for employee, card, at_the_doors in present:
                reports += self._demo_at_the_machine(
                    employee, card, day, at_the_doors, machine
                )
            reports += self._demo_machine_extras(day, machine)
        return [report for report in reports if since < report[0] <= until]

    @api.model
    def _demo_people(self):
        """(employee, card, 'day' | 'night' | 'saturday') for who has a badge."""
        Card = self.env["hr.rfid.card"].sudo()
        people = []
        for xmlid in DAY_WORKERS + NIGHT_WORKERS:
            employee = self.env.ref(xmlid, raise_if_not_found=False)
            if not employee or not employee.active:
                continue
            card = Card.search(
                [("employee_id", "=", employee.id), ("active", "=", True)], limit=1
            )
            if not card:
                continue
            kind = (
                "night"
                if xmlid in NIGHT_WORKERS
                else "saturday"
                if xmlid in SATURDAY_WORKERS
                else "day"
            )
            people.append((employee, card, kind))
        return people

    @api.model
    def _demo_day(self, employee, kind, day, entrance, inner):
        """The passages of one person on one day: (utc moment, ctrl, reader, code)."""
        rng = random.Random("%s-%s-%s" % (SEED, employee.id, day.isoformat()))
        tz = ZoneInfo(employee._local_tz())

        def at(hour, minute=0, on=day):
            local = datetime.combine(on, time(0, 0), tzinfo=tz) + timedelta(
                hours=hour, minutes=minute
            )
            return local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

        weekday = day.weekday()
        if kind == "night":
            return self._demo_night(rng, at, weekday, entrance)
        if weekday == 5:
            if kind != "saturday" or day.isocalendar()[1] % 2:
                return []
            return [
                (at(8, rng.randint(50, 70)), entrance, WAY_IN, GRANTED),
                (at(14, rng.randint(0, 20)), entrance, WAY_OUT, GRANTED),
            ]
        return self._demo_working_day(rng, at, employee, weekday, entrance, inner)

    @api.model
    def _demo_night(self, rng, at, weekday, entrance):
        """Monday to Friday nights, from ten in the evening to six."""
        if weekday > 4 or rng.random() < 0.05:
            return []
        start = at(21, rng.randint(40, 59))
        end = at(30, rng.randint(0, 25))
        if rng.random() < 0.15:
            end = at(31, rng.randint(0, 50))  # stayed on after the shift
        return [
            (start, entrance, WAY_IN, GRANTED),
            (end, entrance, WAY_OUT, GRANTED),
        ]

    @api.model
    def _demo_working_day(self, rng, at, employee, weekday, entrance, inner):
        """A day by the person's own schedule, with its usual deviations."""
        # The person's own working hours that day: when it begins, the break,
        # when it ends. A day the schedule does not have is a day off.
        lines = employee.resource_calendar_id.attendance_ids.filtered(
            lambda line: line.dayofweek == str(weekday) and not line.week_type
        )
        work = lines.filtered(lambda line: line.day_period != "lunch")
        if not work:
            return []
        start = min(work.mapped("hour_from"))
        end = max(work.mapped("hour_to"))
        breaks = lines.filtered(lambda line: line.day_period == "lunch")
        if rng.random() < 0.04:
            return []  # did not come in: core's absence detection has its day
        # An ordinary day stays inside the thresholds a department ignores
        # (hr_attendance_late: 5 minutes late, 10 early, 15 of overtime), so
        # the days that do show lateness or overtime are the ones meant to.
        draw = rng.random()
        if draw < 0.15:
            arrival = at(start, rng.randint(10, 75))  # late
        elif draw < 0.27:
            arrival = at(start, -rng.randint(35, 80))  # early
        else:
            arrival = at(start, rng.randint(-8, 4))
        draw = rng.random()
        if draw < 0.09:
            leaving = at(end, -rng.randint(30, 120))  # left early
        elif draw < 0.23:
            leaving = at(end, rng.randint(60, 150))  # overtime
        else:
            leaving = at(end, rng.randint(0, 10))
        passages = [(arrival, entrance, WAY_IN, GRANTED)]
        if breaks and rng.random() < 0.5:
            lunch = at(breaks[0].hour_from, rng.randint(0, 15))
            passages += [
                (lunch, entrance, WAY_OUT, GRANTED),
                (
                    lunch + timedelta(minutes=rng.randint(40, 58)),
                    entrance,
                    WAY_IN,
                    GRANTED,
                ),
            ]
        if inner:
            passages += self._demo_moving_about(rng, arrival, leaving, inner)
        if rng.random() < 0.03:
            return passages  # forgot to badge out
        passages.append((leaving, entrance, WAY_OUT, GRANTED))
        return passages

    @api.model
    def _demo_moving_about(self, rng, arrival, leaving, inner):
        """Moving about inside: the inner doors, in and back out again."""
        passages = []
        moment = arrival + timedelta(minutes=rng.randint(10, 40))
        for _visit in range(rng.randint(2, 6)):
            if moment >= leaving - timedelta(minutes=30):
                break
            passages.append((moment, inner, 1, GRANTED))
            moment += timedelta(minutes=rng.randint(5, 90))
            passages.append((moment, inner, 2, GRANTED))
            moment += timedelta(minutes=rng.randint(20, 120))
        return passages

    @api.model
    def _demo_day_extras(self, day, entrance, inner, people):
        """What the doors see besides people at work: refusals, a visitor, alarms."""
        rng = random.Random("%s-extras-%s" % (SEED, day.isoformat()))
        extras = []
        if day.weekday() > 4 or not people:
            return extras
        noon = datetime.combine(day, time(9, 0))
        for _refusal in range(rng.randint(0, 3)):
            _employee, card, _kind = rng.choice(people)
            extras.append(
                (
                    noon + timedelta(minutes=rng.randint(0, 480)),
                    inner or entrance,
                    1,
                    card,
                    DENIED,
                )
            )
        visitor = self.env.ref(VISITOR_CARD, raise_if_not_found=False)
        if visitor and visitor.active and rng.random() < 0.4:
            come = noon + timedelta(minutes=rng.randint(60, 300))
            extras += [
                (come, entrance, WAY_IN, visitor, GRANTED),
                (
                    come + timedelta(minutes=rng.randint(20, 90)),
                    entrance,
                    WAY_OUT,
                    visitor,
                    GRANTED,
                ),
            ]
        if rng.random() < 0.6:
            extras.append(
                (
                    noon + timedelta(minutes=rng.randint(0, 480)),
                    inner or entrance,
                    1,
                    None,
                    DOOR_HELD_OPEN,
                )
            )
        if rng.random() < 0.15:
            extras.append(
                (
                    noon + timedelta(minutes=rng.randint(0, 600)),
                    inner or entrance,
                    2,
                    None,
                    DOOR_FORCED,
                )
            )
        for _press in range(rng.randint(0, 2)):
            extras.append(
                (
                    noon + timedelta(minutes=rng.randint(0, 480)),
                    entrance,
                    1,
                    None,
                    EXIT_BUTTON,
                )
            )
        if day.weekday() == 0:
            # The Monday morning power-up after the weekend maintenance.
            extras.append(
                (
                    datetime.combine(day, time(4, rng.randint(0, 50))),
                    inner or entrance,
                    0,
                    None,
                    POWER_ON,
                )
            )
        return extras

    @api.model
    def _demo_portal_guest(self, day, entrance, inner):
        """The customer with a portal login drops by on some days.

        Drawn from a seed of its own, so the rest of the day's extras come out
        as they did before this visitor existed.
        """
        guest = self.env.ref(PORTAL_GUEST_CARD, raise_if_not_found=False)
        if not guest or not guest.active:
            return []
        rng = random.Random("%s-portal-%s" % (SEED, day.isoformat()))
        if rng.random() >= 0.45:
            return []
        come = datetime.combine(day, time(9, 30)) + timedelta(
            minutes=rng.randint(0, 300)
        )
        visit = [
            (come, entrance, WAY_IN, guest, GRANTED),
            (
                come + timedelta(minutes=rng.randint(25, 110)),
                entrance,
                WAY_OUT,
                guest,
                GRANTED,
            ),
        ]
        if inner and rng.random() < 0.3:
            # Tries a door that is not for visitors.
            visit.append(
                (come + timedelta(minutes=rng.randint(5, 20)), inner, 1, guest, DENIED)
            )
        return visit

    # ------------------------------------------------------------------
    # The customer of the services
    # ------------------------------------------------------------------
    @api.model
    def _demo_service_badge(self):
        """The badge of the demo's service customer, or nothing.

        Nothing where the services add-on or its portal demo is not installed,
        and for a badge that has been handed to somebody else since.
        """
        Card = self.env["hr.rfid.card"]
        if "rfid.service.sale.wiz" not in self.env:
            return Card
        badge = self.env.ref(SERVICE_BADGE, raise_if_not_found=False)
        customer = self.env.ref(SERVICE_CUSTOMER, raise_if_not_found=False)
        if not badge or not customer or badge.contact_id != customer:
            return Card
        return badge.sudo()

    @api.model
    def _demo_services_not_over(self, badge):
        """The services of the badge's owner that run now or are still ahead."""
        return (
            self.env["rfid.service.sale"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", badge.contact_id.id),
                    ("state", "in", ("registered", "progress")),
                    ("end_date", ">=", fields.Datetime.now()),
                ]
            )
        )

    @api.model
    def _demo_keep_a_service_running(self, badge):
        """Sell the service customer a service once they have none.

        The services add-on's own demo sale lasts a few hours from the
        install; after that the portal of the demo login shows a service that
        ended long ago. So it is sold again here, the way the till sells it
        (rfid.service.sale.wiz, the button the cashier presses): the sale, the
        access and the badge's period are what a real sale leaves.

        The sale may be refused - somebody trying the demo gave the customer
        permanent access or took the doors out of the access group (the till
        says no), or the customer already has this service for the very same
        period, cancelled (the database keeps one per period). Nothing is sold
        then and the reason is logged; the rest of the demo goes on. While
        the refusal lasts every run asks the till again, and each asking uses
        up one of its sale numbers - hence the warning, every time.
        """
        if not badge or self._demo_services_not_over(badge):
            return
        service = self.env.ref(SERVICE_SOLD, raise_if_not_found=False)
        if not service or not service.active:
            _logger.info(
                "RFID demo: the service the demo sells is archived or gone, "
                "so the demo customer is sold none."
            )
            return
        customer = badge.contact_id
        # What is still waiting to be written goes first: if that fails, it is
        # not this sale that was refused.
        self.env.flush_all()
        try:
            with self.env.cr.savepoint(), mute_logger("odoo.sql_db"):
                self.env["rfid.service.sale.wiz"].sudo().create(
                    {
                        "service_id": service.id,
                        "partner_id": customer.id,
                        # The form fills these from the customer; left empty,
                        # the sale would empty them on the customer too.
                        "mobile": customer.phone,
                        "email": customer.email,
                        "card_number": badge.number,
                    }
                ).write_card()
        except (UserError, pgerrors.UniqueViolation) as refusal:
            _logger.warning(
                "RFID demo: %s was not sold to the demo customer (%s): %s",
                service.display_name,
                type(refusal).__name__,
                refusal,
            )

    @api.model
    def _demo_service_customer(self, day, entrance, badge):
        """The customer of the services comes to use what they bought.

        In and out through the entrance on some evenings. Whether a passage
        happens is settled when its turn comes (_demo_may_pass): the service
        may have been sold, used up or sold again by then. Drawn from a seed
        of its own.
        """
        if not badge:
            return []
        rng = random.Random("%s-service-%s" % (SEED, day.isoformat()))
        if rng.random() >= 0.6:
            return []
        come = datetime.combine(day, time(16, 0)) + timedelta(
            minutes=rng.randint(0, 150)
        )
        leave = come + timedelta(minutes=rng.randint(45, 100))
        return [
            (come, entrance, WAY_IN, badge, GRANTED),
            (leave, entrance, WAY_OUT, badge, GRANTED),
        ]

    @api.model
    def _demo_may_pass(self, badge, way, moment):
        """Whether a passage of the service customer happens.

        In: with a badge that is valid, while a service of theirs runs at that
        moment - every entry is a visit the system counts, and it closes the
        service itself when the visits are used up. Out: whenever they are in.
        """
        if way == WAY_OUT:
            last = (
                self.env["hr.rfid.event.user"]
                .sudo()
                .search(
                    [("card_id", "=", badge.id)],
                    order="event_time desc, id desc",
                    limit=1,
                )
            )
            return last.event_action == "1" and last.reader_id.reader_type == "0"
        return badge.active and any(
            service.state == "progress" and service.start_date <= moment
            for service in self._demo_services_not_over(badge)
        )

    # ------------------------------------------------------------------
    # The vending machine
    # ------------------------------------------------------------------
    @api.model
    def _demo_vending_machine(self, webstack):
        """The demo vending machine, or nothing.

        Nothing where the vending add-on is not installed, where its demo
        machine is gone or was moved off the demo module, and for a machine
        that keeps its own prices - there the simulation has nothing to sell.
        """
        if "hr.rfid.vending.event" not in self.env:
            return self.env["hr.rfid.ctrl"]
        machine = self.env.ref(VENDING_MACHINE, raise_if_not_found=False)
        if (
            not machine
            or machine.webstack_id != webstack
            or not machine._vending_has_price_table()
            or not self._demo_on_sale(machine)
        ):
            return self.env["hr.rfid.ctrl"]
        return machine.sudo()

    @api.model
    def _demo_on_sale(self, machine):
        """What the machine sells: (item number, price in the machine's units).

        The item number is the one the buyer presses (four to a row); the
        price is the product's own, in the units the machine counts in. A
        price the machine cannot count is left out.
        """
        scale = machine.scale_factor or 0
        if not scale:
            return []
        on_sale = []
        rows = (
            self.env["hr.rfid.ctrl.vending.row"]
            .sudo()
            .search([("controller_id", "=", machine.id)], order="row_num")
        )
        for row in rows:
            for position in (1, 2, 3, 4):
                item = row["item%d" % position]
                units = round(item.list_price * 100 / scale) if item else 0
                if 0 < units <= 0xFF:
                    on_sale.append(((row.row_num - 1) * 4 + position, units))
        return on_sale

    @api.model
    def _demo_sale_data(self, item_number, units):
        """A completed sale as the machine words it: the item, then its price."""
        price = "%02x" % units
        return "0000%02x0%s0%s0000" % (item_number, price[0], price[1])

    @api.model
    def _demo_vending_credit(self, machine):
        """The demo people get credit at the machine, once.

        Only those who have nothing there and are on no refill yet: credit
        somebody entered is theirs. From then on the vending add-on's own
        monthly refill keeps them going.
        """
        if not machine:
            return
        for employee, _card, _kind in self._demo_people():
            employee = employee.sudo()
            if (
                employee.hr_rfid_vending_auto_refill
                or employee.hr_rfid_vending_balance
                or employee.hr_rfid_vending_recharge_balance
            ):
                continue
            employee.write(
                {
                    "hr_rfid_vending_auto_refill": True,
                    "hr_rfid_vending_refill_type": "fixed",
                    "hr_rfid_vending_refill_amount": VENDING_STARTING_CREDIT,
                }
            )
            employee.hr_rfid_vending_add_to_balance(VENDING_STARTING_CREDIT)

    @api.model
    def _demo_can_pay(self, card, machine, data=NO_DATA):
        """Whether the card holder has the credit for the sale a report names."""
        units = int(data[6:8], 16) * 0x10 + int(data[8:10], 16)
        price = units * machine.scale_factor / 100
        _as_sent, credit = card.employee_id.sudo().get_employee_balance(machine)
        return credit >= price

    @api.model
    def _demo_at_the_machine(self, employee, card, day, at_the_doors, machine):
        """What one person does at the vending machine on a day they are in.

        A card shown and an item bought, once or twice on some days, between
        coming in and going home. Drawn from a seed of its own: the person's
        day at the doors comes out as it did before the machine existed.
        """
        if len(at_the_doors) < 2:
            return []
        arrival = min(moment for moment, *_rest in at_the_doors)
        leaving = max(moment for moment, *_rest in at_the_doors)
        if leaving - arrival < timedelta(hours=3):
            return []
        on_sale = self._demo_on_sale(machine)
        rng = random.Random("%s-vending-%s-%s" % (SEED, employee.id, day.isoformat()))
        draw = rng.random()
        visits = 0 if draw < 0.35 else 1 if draw < 0.8 else 2
        reports = []
        free = int((leaving - arrival).total_seconds() // 60) - 75
        for _visit in range(visits):
            shown = arrival + timedelta(minutes=45 + rng.randint(0, max(free, 1)))
            item_number, units = rng.choice(on_sale)
            reports.append((shown, machine, 1, card, CREDIT_REQUEST, NO_DATA))
            reports.append(
                (
                    shown + timedelta(seconds=rng.randint(15, 50)),
                    machine,
                    1,
                    card,
                    SALE,
                    self._demo_sale_data(item_number, units),
                )
            )
        return reports

    @api.model
    def _demo_machine_extras(self, day, machine):
        """What the machine sees besides the staff: coins, and second thoughts."""
        if day.weekday() > 4:
            return []
        rng = random.Random("%s-machine-%s" % (SEED, day.isoformat()))
        on_sale = self._demo_on_sale(machine)
        opening = datetime.combine(day, time(7, 0))
        extras = []
        for _coins in range(rng.randint(0, 3)):
            item_number, units = rng.choice(on_sale)
            extras.append(
                (
                    opening + timedelta(minutes=rng.randint(0, 600)),
                    machine,
                    1,
                    None,
                    SALE,
                    self._demo_sale_data(item_number, units),
                )
            )
        if rng.random() < 0.12:
            # Somebody put credit on the machine and chose nothing: it went
            # back, and the machine says so.
            extras.append(
                (
                    opening + timedelta(minutes=rng.randint(0, 600)),
                    machine,
                    1,
                    None,
                    CREDIT_RETURNED,
                    NO_DATA,
                )
            )
        return extras


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _demo_is_away(self, day):
        """On approved leave that day, or the day is a public holiday of the
        company where the person works: nobody comes in then."""
        self.ensure_one()
        if self._demo_is_public_holiday(day):
            return True
        if "hr.leave" not in self.env:
            return False
        return bool(
            self.env["hr.leave"]
            .sudo()
            .search_count(
                [
                    ("employee_id", "=", self.id),
                    ("state", "=", "validate"),
                    ("request_date_from", "<=", day),
                    ("request_date_to", ">=", day),
                ]
            )
        )

    def _demo_is_public_holiday(self, day):
        """A public holiday of the company falls on the person's own day.

        Read the way core reads it for this person: the holidays of the company
        for everybody or for the person's schedule
        (resource/models/resource_calendar.py, _leave_intervals), in the
        person's own zone.
        """
        calendar = self.resource_calendar_id or self.company_id.resource_calendar_id
        if not calendar:
            return False
        tz = ZoneInfo(self._local_tz())
        start = datetime.combine(day, time.min, tzinfo=tz)
        stop = datetime.combine(day, time.max, tzinfo=tz)
        holidays = calendar.sudo()._leave_intervals(
            start,
            stop,
            self.resource_id,
            domain=[("time_type", "=", "leave"), ("resource_id", "=", False)],
        )
        return bool(holidays)


class HrRfidCommand(models.Model):
    _inherit = "hr.rfid.command"

    @api.model_create_multi
    def create(self, vals_list):
        """A door opened from the screen of the demo is answered at once.

        The demo module has nobody behind it. What the system asks of it is
        answered when the demo next runs (_demo_answer_commands), which is
        soon enough for the clock and the cards. A door opened from the
        screen is given up after a minute without a module to take it, so a
        visitor trying the button would be shown a door that does not open.
        A module in touch takes it within seconds; the demo one does too.
        """
        commands = super().create(vals_list)
        of_the_moment = commands.filtered(
            lambda command: command.status == "Wait" and command._meant_for_the_moment()
        )
        if of_the_moment:
            demo_module = self.env["hr.rfid.demo"]._demo_hardware()
            of_the_moment.filtered(
                lambda command: command.webstack_id == demo_module
            ).write({"status": "Success", "ex_timestamp": fields.Datetime.now()})
        return commands
