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

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

#: How far back the first run reaches, so a fresh demo has weeks to show.
BACKFILL_DAYS = 45
#: The moment the simulation has reached (naive UTC, as Odoo stores time).
SIMULATED_UNTIL = "hr_rfid_demo.simulated_until"
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
SENSOR = "hr_rfid.demo_th_sensor_server_room"
#: Controller event codes (hr_rfid/models/hr_rfid_webstack_hw_events.py).
GRANTED = 3
DENIED = 4
EXIT_BUTTON = 21
DOOR_HELD_OPEN = 25
DOOR_FORCED = 26
POWER_ON = 30
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
        since = params.get_param(SIMULATED_UNTIL)
        since = (
            fields.Datetime.to_datetime(since)
            if since
            else until - timedelta(days=BACKFILL_DAYS)
        )
        if since >= until:
            return 0
        passages = self._demo_passages(since, until)
        for moment, ctrl, reader, card, event_n in passages:
            self._demo_report(webstack, ctrl, reader, card, moment, event_n)
        readings = self._demo_environment_readings(since, until)
        self._demo_hourly_costs()
        params.set_param(SIMULATED_UNTIL, fields.Datetime.to_string(until))
        _logger.info(
            "RFID demo: %d passages and %d sensor readings simulated from %s to %s",
            len(passages),
            readings,
            since,
            until,
        )
        return len(passages)

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
    def _demo_report(self, webstack, ctrl, reader, card, moment, event_n):
        """One report of the demo module, as the device sends it.

        The device speaks its own local time; the webstack turns it back into
        UTC with the same offset (hr.rfid.webstack.get_ws_time).
        """
        local = moment + webstack._get_tz_offset()
        date_format, time_format = webstack.time_format.split(" ")
        webstack.with_context(ws_skip_piggyback=True)._hw_parse_event(
            {
                "convertor": webstack.serial,
                "event": {
                    "bos": 1,
                    "tos": 1,
                    "card": card.number if card else "0000000000",
                    "cmd": "FA",
                    "date": local.strftime(date_format),
                    "time": local.strftime(time_format),
                    "day": local.isoweekday() % 7,
                    "dt": "00000000000000",
                    "err": 0,
                    "event_n": event_n,
                    "id": ctrl.ctrl_id,
                    "reader": reader,
                },
            }
        )

    @api.model
    def _demo_passages(self, since, until):
        """Every passage of the window, in the order the doors saw them.

        Each person's day is drawn from a seed of the person and the day, so a
        day comes out the same whichever run reaches it first.
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
        passages = []
        day = since.date() - timedelta(days=1)
        while day <= until.date():
            for employee, card, kind in people:
                if (employee.id, day) in handwritten or employee._demo_is_away(day):
                    continue
                for moment, ctrl, reader, event_n in self._demo_day(
                    employee, kind, day, entrance, inner
                ):
                    if since < moment <= until:
                        passages.append((moment, ctrl, reader, card, event_n))
            passages.extend(
                p
                for p in self._demo_day_extras(day, entrance, inner, people)
                if since < p[0] <= until
            )
            day += timedelta(days=1)
        passages.sort(key=lambda p: p[0])
        return passages

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


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _demo_is_away(self, day):
        """On approved leave that day: a person on leave does not come in."""
        self.ensure_one()
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
