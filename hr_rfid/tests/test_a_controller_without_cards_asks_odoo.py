from datetime import datetime, time, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import HttpCase, tagged

from .controller import RFIDController

GRANTED = "400300"
DENIED = "400400"
UNUSED_INTERVALS = "0" * 24


def _schedule_data(number, day_rows):
    """The schedule as the editor saves it: the number, eight day rows
    (Monday first, then the holiday row) of four HHMMHHMM intervals, and the
    holiday byte."""
    rows = [day_rows.get(day, "0" * 32) for day in range(8)]
    return "%02X" % number + "".join(rows) + "00"


def _group(case, name, **vals):
    """An access group of the test company."""
    return case.env["hr.rfid.access.group"].create(
        {"name": name, "company_id": case.test_company_id, **vals}
    )


@tagged("standard", "at_install", "rfid", "rfid_events")
class TestAControllerWithoutCardsAsksOdoo(RFIDController, HttpCase):
    """A controller that keeps no cards (external database) asks Odoo about
    every card shown to it. The owner's need (gap analysis of 09.11.2026,
    D1): the answer must follow the same rights Odoo writes to the
    controllers that keep their cards, or a card passes on one door where it
    is stopped on another - after its access has expired, outside its
    working hours, or after its paid visits are used up."""

    _registry_readonly_enabled = False

    def setUp(self):
        super().setUp()
        self._add_iCon110()
        self.ctrl = self.c_110
        self._switch_to_external_db(self.ctrl)
        self.employee_place = self.test_employee_id.hr_rfid_access_group_ids.filtered(
            lambda rel: rel.access_group_id == self.test_ag_employee_1
        )
        self.assertTrue(
            self.employee_place, "the employee is in the group through the department"
        )

    def _asks(self, card):
        """Show the card on reader 1 and return what Odoo told the controller."""
        response = self._make_event(
            self.ctrl, card=card.number, reader=1, event_code=64
        )
        answer = response["cmd"]["d"]
        self.assertEqual(response["cmd"]["c"], "DB")
        self.assertEqual(self._send_cmd_response(response, answer), {})
        return answer

    def _passes(self, card):
        """The controller opened the door for the card and reports the pass."""
        self.assertEqual(
            self._make_event(self.ctrl, card=card.number, reader=1, event_code=3), {}
        )

    def test_a_card_with_its_access_running_passes(self):
        """The employee's group has the door: the card passes."""
        self.test_ag_employee_1.add_doors(self.ctrl.door_ids)
        self.assertEqual(self._asks(self.test_card_employee), GRANTED)

    def test_a_card_with_no_door_in_its_groups_is_stopped(self):
        """No group of the owner holds the door: the card is stopped."""
        self.assertEqual(self._asks(self.test_card_employee), DENIED)

    def test_access_that_has_expired_no_longer_opens(self):
        """The employee's access in the group ended an hour ago: the card is
        stopped, as it is on a controller that keeps cards."""
        self.test_ag_employee_1.add_doors(self.ctrl.door_ids)
        self.employee_place.expiration = fields.Datetime.now() - timedelta(hours=1)
        self.assertEqual(self._asks(self.test_card_employee), DENIED)

    def test_access_that_starts_tomorrow_does_not_open_yet(self):
        """Access given from tomorrow does not open the door today."""
        self.test_ag_employee_1.add_doors(self.ctrl.door_ids)
        self.employee_place.activate_on = fields.Datetime.now() + timedelta(days=1)
        self.assertEqual(self._asks(self.test_card_employee), DENIED)

    def test_a_card_that_was_switched_off_is_stopped(self):
        """A card past its end date is stopped even when its group is valid."""
        self.test_ag_employee_1.add_doors(self.ctrl.door_ids)
        self.test_card_employee.deactivate_on = fields.Datetime.now() - timedelta(
            minutes=5
        )
        self.assertEqual(self._asks(self.test_card_employee), DENIED)

    def test_a_door_of_an_inherited_group_opens(self):
        """The employee's group has no doors of its own but includes a group
        that has this door: the card passes, as the written rights allow."""
        lobby = _group(self, "Lobby")
        lobby.add_doors(self.ctrl.door_ids)
        self.test_ag_employee_1.inherited_ids = [(4, lobby.id)]
        self.assertEqual(self._asks(self.test_card_employee), GRANTED)

    def test_a_card_of_another_type_than_the_door_is_stopped(self):
        """The door takes only visitor badges: an employee card in a group
        that holds the door is stopped, as the written rights never give it
        that door."""
        self.test_ag_employee_1.add_doors(self.ctrl.door_ids)
        badges = self.env["hr.rfid.card.type"].create({"name": "Visitor badge"})
        self.ctrl.door_ids.card_type = badges
        self.assertEqual(self._asks(self.test_card_employee), DENIED)

    def test_the_wait_between_passes_of_an_inherited_group_holds(self):
        """The lobby group asks for a minute between two passes. A member of
        a group that includes the lobby passes once and is stopped right
        after, like a member of the lobby group itself."""
        lobby = _group(self, "Lobby", delay_between_events=60)
        lobby.add_doors(self.ctrl.door_ids)
        self.test_ag_employee_1.inherited_ids = [(4, lobby.id)]
        self.assertEqual(self._asks(self.test_card_employee), GRANTED)
        self._passes(self.test_card_employee)
        self.assertEqual(self._asks(self.test_card_employee), DENIED)

    def test_a_visitor_with_no_visits_left_is_stopped(self):
        """A visitor bought two visits: with one left the card passes, with
        none left it is stopped."""
        self.test_ag_partner_1.add_doors(self.ctrl.door_ids)
        self.test_partner_ag_rel.write(
            {
                "visits_counting": True,
                "permitted_visits": 2,
                "visits_counter": 1,
            }
        )
        self.assertEqual(self._asks(self.test_card_partner), GRANTED)
        self.test_partner_ag_rel.visits_counter = 2
        self.assertEqual(self._asks(self.test_card_partner), DENIED)

    def test_a_day_pass_through_an_included_door_is_used_up(self):
        """A visitor's day pass gives one visit; its group has no doors of its
        own and includes the gym, which holds this door. The first pass is
        let through and counted, the second is stopped."""
        gym = _group(self, "Gym")
        gym.add_doors(self.ctrl.door_ids)
        self.test_ag_partner_1.inherited_ids = [(4, gym.id)]
        self.test_partner_ag_rel.write({"visits_counting": True, "permitted_visits": 1})
        self.assertEqual(self._asks(self.test_card_partner), GRANTED)
        self._passes(self.test_card_partner)
        self.assertEqual(self.test_partner_ag_rel.visits_counter, 1)
        self.assertEqual(self._asks(self.test_card_partner), DENIED)

    def test_a_card_of_someone_who_left_is_stopped(self):
        """The employee's card passes; once the employee is archived on
        leaving, the same card is stopped."""
        self.test_ag_employee_1.add_doors(self.ctrl.door_ids)
        self.assertEqual(self._asks(self.test_card_employee), GRANTED)
        self.test_employee_id.action_archive()
        self.assertEqual(self._asks(self.test_card_employee), DENIED)

    def test_a_visitor_waits_the_time_between_passes(self):
        """The visitors' group asks for a minute between passes: a visitor
        passes, is stopped right after, and passes again once the minute is
        over."""
        self.test_ag_partner_1.delay_between_events = 60
        self.test_ag_partner_1.add_doors(self.ctrl.door_ids)
        self.assertEqual(self._asks(self.test_card_partner), GRANTED)
        self._passes(self.test_card_partner)
        self.assertEqual(self._asks(self.test_card_partner), DENIED)
        later = fields.Datetime.now() + timedelta(seconds=61)
        with patch.object(fields.Datetime, "now", return_value=later):
            self.assertEqual(self._asks(self.test_card_partner), GRANTED)

    def test_the_working_hours_are_those_of_the_controllers_place(self):
        """A controller in Tokyo, working hours Monday 06:00-08:00. When it is
        Monday 07:00 in Tokyo (Sunday 22:00 UTC) the card passes; on Tuesday
        07:00 in Tokyo it is stopped."""
        self.ctrl.webstack_id.tz = "Asia/Tokyo"
        # the new zone sets the controller's clock first
        response = self._hearbeat(self.ctrl.webstack_id)
        self.assertEqual(response["cmd"]["c"], "D7")
        self.assertEqual(self._send_cmd_response(response), {})
        schedule = self._schedule(1)
        schedule.ts_data = _schedule_data(1, {0: "06000800" + UNUSED_INTERVALS})
        self.test_ag_employee_1.with_context(no_hardware_commands=True).add_doors(
            self.ctrl.door_ids, schedule
        )
        for utc, expected in [
            (datetime(2026, 11, 22, 22, 0), GRANTED),
            (datetime(2026, 11, 23, 22, 0), DENIED),
        ]:
            with patch.object(fields.Datetime, "now", return_value=utc):
                self.assertEqual(
                    self._asks(self.test_card_employee), expected, "UTC %s" % utc
                )

    def test_the_card_passes_only_inside_its_working_hours(self):
        """The door is given with working hours 08:00-18:00 every day. At the
        controller's local time the card is stopped at 07:59 and 18:01 and
        passes at 08:00 and at 18:00, the last minute included, as the
        controller itself decides."""
        schedule = self._schedule(1)
        schedule.ts_data = _schedule_data(
            1, {day: "08001800" + UNUSED_INTERVALS for day in range(7)}
        )
        self.test_ag_employee_1.with_context(no_hardware_commands=True).add_doors(
            self.ctrl.door_ids, schedule
        )

        # A day ahead, so the card and its access have long started.
        day = (fields.Datetime.now() + timedelta(days=2)).date()
        offset = self.ctrl.webstack_id._get_tz_offset()
        for local, expected in [
            (time(7, 59), DENIED),
            (time(8, 0), GRANTED),
            (time(18, 0), GRANTED),
            (time(18, 1), DENIED),
        ]:
            server_now = datetime.combine(day, local) - offset
            with patch.object(fields.Datetime, "now", return_value=server_now):
                self.assertEqual(
                    self._asks(self.test_card_employee),
                    expected,
                    "local time %s" % local,
                )


@tagged("standard", "at_install", "rfid", "rfid_events")
class TestARelayControllerOpensOnlyTheDoorsGivenNow(RFIDController, HttpCase):
    """A relay controller answers one card with several doors at once. It
    must release only the doors the card opens now, not every door the
    owner was ever given."""

    _registry_readonly_enabled = False

    def test_a_door_from_expired_access_stays_closed(self):
        """The employee has two doors through a valid group and a third
        through access that ended yesterday: only the first two open."""
        self._add_RelayController()
        ctrl = self.c_Relay
        self._switch_to_external_db(ctrl)
        reader = ctrl.reader_ids.filtered(lambda r: r.number == 1)
        doors = reader.door_ids.sorted("number")
        self.assertGreaterEqual(len(doors), 3, "the reader serves several relay doors")
        given, expired = doors[:2], doors[2]

        self.test_ag_employee_1.add_doors(given)
        storage = _group(self, "Storage")
        storage.add_doors(expired)
        self.test_department_id.hr_rfid_allowed_access_groups = [(4, storage.id)]
        now = fields.Datetime.now()
        self.env["hr.rfid.access.group.employee.rel"].create(
            {
                "access_group_id": storage.id,
                "employee_id": self.test_employee_id.id,
                "activate_on": now - timedelta(days=10),
                "expiration": now - timedelta(days=1),
            }
        )

        response = self._make_event(
            ctrl, card=self.test_card_employee.number, reader=1, event_code=64
        )
        opened = sum(1 << (door.number - 1) for door in given)
        self.assertEqual(
            response["cmd"]["d"],
            "4000" + ctrl.convert_int_to_cmd_data_for_output_control(opened),
        )
        self.assertEqual(self._send_cmd_response(response, response["cmd"]["d"]), {})

    def test_a_relay_opened_from_the_screen_does_not_move_other_outputs(self):
        """The operator releases relay 1 from the screen. The controller's
        answer names the reader and the relays, not an output number, so the
        outputs shown on the controller stay as they were."""
        self._add_RelayController()
        ctrl = self.c_Relay
        ctrl.output_states = 5
        ctrl.change_output_state(1, 1, 3)
        response = self._hearbeat(ctrl.webstack_id)
        self.assertEqual(response["cmd"]["c"], "DB")
        self.assertTrue(response["cmd"]["d"].startswith("1F"))
        self.assertEqual(self._send_cmd_response(response, response["cmd"]["d"]), {})
        self.assertEqual(ctrl.output_states, 5)


@tagged("standard", "at_install", "rfid", "rfid_events")
class TestTheSirenShowsWhatWasSwitched(RFIDController, HttpCase):
    """The operator switches the siren from the controller's screen; the
    screen shows it the way it was switched, and other outputs keep theirs."""

    _registry_readonly_enabled = False

    def test_the_siren_switched_on_shows_on_and_off_shows_off(self):
        self._add_iCon110()
        ctrl = self.c_110.with_context(no_output=True)
        siren_bit = 1 << ((ctrl.alarm_lines == 1 and 4 or 10) - 1)
        ctrl.output_states = 0
        ctrl.siren_state = True
        self.assertEqual(
            ctrl.output_states, siren_bit, "the siren goes on on a quiet controller"
        )
        ctrl.siren_state = False
        ctrl.output_states = 1  # output 1 is on
        ctrl.siren_state = True
        self.assertTrue(ctrl.siren_state)
        self.assertEqual(ctrl.output_states, 1 | siren_bit)
        ctrl.siren_state = False
        self.assertFalse(ctrl.siren_state)
        self.assertEqual(ctrl.output_states, 1, "the other output keeps its state")
        ctrl.siren_state = False
        self.assertEqual(
            ctrl.output_states, 1, "switching off again takes nothing more away"
        )


@tagged("standard", "at_install", "rfid", "rfid_time_schedules")
class TestAWorkingTimeIsReadAsWritten(RFIDController):
    """The working time the operator saves is what the doors follow."""

    def setUp(self):
        super().setUp()
        self.schedule = self._schedule(2)

    def test_the_fourth_period_of_a_day_keeps_its_end(self):
        """A day with four periods, the last one 20:00-22:30: the editor
        reads 22:30 back, not 22:03."""
        self.schedule.ts_data = _schedule_data(
            2,
            {
                0: "0700080009001000110012002000" + "2230",
            },
        )
        self.assertEqual(self.schedule._get_interval_from_day_tuple(0, 3), (20.0, 22.5))

    def test_a_weekday_schedule_does_not_open_on_sunday(self):
        """Working hours set for Monday only: Monday 09:00 passes, Sunday
        09:00 and Tuesday 09:00 do not."""
        self.schedule.ts_data = _schedule_data(2, {0: "08001800" + UNUSED_INTERVALS})
        monday = datetime(2026, 11, 16, 9, 0)
        self.assertEqual(monday.weekday(), 0)
        self.assertTrue(self.schedule._lets_in_at(monday))
        self.assertFalse(self.schedule._lets_in_at(monday + timedelta(days=1)))
        self.assertFalse(self.schedule._lets_in_at(monday + timedelta(days=6)))

    def test_no_working_time_means_any_time(self):
        """A door given with "Not using TS" opens at any hour."""
        no_schedule = self._schedule(0)
        self.assertTrue(no_schedule._lets_in_at(datetime(2026, 11, 22, 3, 0)))

    def test_an_empty_working_time_never_opens(self):
        """A working time with no periods at all lets nobody in."""
        self.schedule.ts_data = _schedule_data(2, {})
        self.assertFalse(self.schedule._lets_in_at(datetime(2026, 11, 16, 0, 0)))
        self.assertFalse(self.schedule._lets_in_at(datetime(2026, 11, 16, 12, 0)))

    def test_saving_the_working_time_unchanged_keeps_every_minute(self):
        """The operator opens the working time with 07:05-12:10 and
        13:20-17:20 on Monday and 22:30 as the end of a fourth period, and
        saves it without a change: every minute stays as it was."""
        self.schedule.ts_data = _schedule_data(
            2, {0: "07051210" + "13201720" + "00000000" + "20002230"}
        )
        before = self.schedule.ts_data[:258]
        wizard = (
            self.env["hr.rfid.ctrl.ts.week.wiz"]
            .with_context(active_id=self.schedule.id)
            .create({"ts_id": self.schedule.id})
        )
        wizard.save_ts()
        self.assertEqual(self.schedule.ts_data, before)
