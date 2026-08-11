# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""What the monitoring screens are told, and what they are spared.

Business facts under test (owner-approved spec, 2026-08-11):

1. A module reporting normally tells the dispatcher nothing new, so a routine
   check-in must not reach the screens. Derived from the live fleet, that noise
   is 92% of everything this suite puts on the bus - and the same shape of
   traffic is what ran a sister product's websocket workers out of memory.
2. The module must still count as reachable while it reports quietly: silence
   on the bus is not silence on the wire.
3. Real news still arrives at once - a badge at a door, a refused command, a
   zone in alarm, an operator's own edit, a module that went dark or came back.

Everything is driven through the REAL device endpoint. The model-level fix alone
would have looked complete while the controller kept broadcasting on every
request, which is exactly how the sister product shipped its flood twice.
"""
from unittest.mock import patch

from odoo import fields
from odoo.tests import HttpCase
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.models.hr_rfid_webstack import PRESENCE_MISSES_BEFORE_DARK
from odoo.addons.hr_rfid.tests.controller import RFIDController

import logging

_logger = logging.getLogger(__name__)


class BusWatchCase(RFIDController, HttpCase):
    """A fleet whose company actually watches the screens."""

    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The broadcast is opt-in per company; without it send_notice returns
        # early and every assertion below would pass for the wrong reason.
        cls.env['res.company'].browse(cls.test_company_id).realtime_refresh = True

    def _patch_bus(self):
        return patch.object(type(self.env['bus.bus']), '_sendone')

    def _refresh_calls(self, mock_send, model):
        return [
            call for call in mock_send.call_args_list
            if call.args and call.args[0] == 'polimex.%s' % model
        ]

    def _poll_status(self, ctrl, data):
        """Drive one real status poll to the controller and answer it."""
        ctrl.read_status()
        response = self._hearbeat(ctrl.webstack_id)
        while response and response.get('cmd', {}).get('c') != 'B3':
            response = self._send_cmd_response(response)
        self.assertTrue(response, 'the controller must have been asked for its status')
        return self._send_cmd_response(response, data)


@tagged('post_install', '-at_install', 'rfid_refresh_views', 'rfid_telemetry_bus')
class TestHeartbeatIsQuiet(BusWatchCase):
    """A module that is merely reporting must not repaint the screens."""

    def test_idle_heartbeat_is_silent_but_the_module_stays_reachable(self):
        """The dispatcher learns nothing from a routine check-in - but the
        module must still count as alive, or the presence scan would call it
        dark while it is talking to us every minute."""
        self._hearbeat(self.test_webstack_10_3_id)  # arrival may legitimately differ
        with self._patch_bus() as send:
            self._hearbeat(self.test_webstack_10_3_id)
        self.assertEqual(
            self._refresh_calls(send, 'hr.rfid.webstack'), [],
            'a check-in that changed nothing must not reach the screens')
        # The write itself must still have happened - the record was written in
        # the HTTP worker's cursor, so drop the test's cached copy first.
        self.test_webstack_10_3_id.invalidate_recordset(['updated_at', 'last_update'])
        self.assertTrue(
            self.test_webstack_10_3_id._is_reachable(),
            'the module keeps reporting, so it stays reachable')

    def test_a_hundred_check_ins_stay_completely_quiet(self):
        """Not 'quieter' - quiet. The incident was a backlog that never
        drained, so any per-heartbeat residue is a regression."""
        self._hearbeat(self.test_webstack_10_3_id)
        with self._patch_bus() as send:
            for _i in range(100):
                self._hearbeat(self.test_webstack_10_3_id)
        self.assertEqual(self._refresh_calls(send, 'hr.rfid.webstack'), [])

    def test_a_module_coming_back_is_announced_on_its_very_first_check_in(self):
        """The recovery half, driven the way production produces it: the module
        is dark, then it simply talks again. Nothing else touches the record -
        so if this check-in does not announce it, the screen stays orange for a
        module that has been reporting for hours."""
        self.test_webstack_10_3_id.last_update = False
        self.env.flush_all()
        with self._patch_bus() as send:
            self._hearbeat(self.test_webstack_10_3_id)
        self.assertTrue(
            self._refresh_calls(send, 'hr.rfid.webstack'),
            'a module coming back must reach the dispatcher at once')
        self.test_webstack_10_3_id.invalidate_recordset(['last_update'])
        self.assertTrue(self.test_webstack_10_3_id.last_update)

    def test_an_operator_edit_still_broadcasts(self):
        """Regression guard: the gate covers device telemetry, nothing else."""
        with self._patch_bus() as send:
            self.test_webstack_10_3_id.write({'name': 'Renamed by the operator'})
        self.assertEqual(len(self._refresh_calls(send, 'hr.rfid.webstack')), 1)


@tagged('post_install', '-at_install', 'rfid_refresh_views', 'rfid_telemetry_bus')
class TestControllerStatusPoll(BusWatchCase):
    """The 5-minute status poll speaks only when the state moved."""

    def test_repeated_status_polls_do_not_repaint_the_screens(self):
        """Supply voltage drifts on every read; that is not something an
        operator acts on. The poll that first establishes the state IS news;
        an identical one five minutes later is not."""
        self._add_iCon110()
        # A state the setup has not already established, so the first poll is a
        # genuine change - without that positive control a poll that crashed
        # before writing anything would be indistinguishable from a silent one.
        status = self.default_B3[6]
        moved = status[:24] + 'ff' + status[26:]
        with self._patch_bus() as send:
            self._poll_status(self.c_110, moved)
        self.assertTrue(
            self._refresh_calls(send, 'hr.rfid.ctrl'),
            'the poll that established the state must reach the screens')
        with self._patch_bus() as send:
            self._poll_status(self.c_110, moved)
        self.assertEqual(
            self._refresh_calls(send, 'hr.rfid.ctrl'), [],
            'a status poll that found no change must not repaint the screens')

    def test_a_zone_going_into_alarm_reaches_the_dispatcher(self):
        """Two polls, identical except for the alarm byte: exactly one refresh,
        and it is the second one. This is the whole reason the screens exist."""
        self._add_iCon110()
        status = self.default_B3[6]
        self._poll_status(self.c_110, status)
        alarmed = status[:24] + 'aa' + status[26:]
        with self._patch_bus() as send:
            self._poll_status(self.c_110, alarmed)
        self.assertEqual(
            len(self._refresh_calls(send, 'hr.rfid.ctrl')), 1,
            'a zone in alarm must reach the dispatcher on the poll that saw it')

    def test_a_temperature_reading_is_not_news(self):
        """The sensor mirror is telemetry too - and both readings must still be
        stored, silence is not the same as a skipped write."""
        self._add_iCon110()
        with self._patch_bus() as send:
            self.c_110.update_th(sensor_number=0, data_dict={'t': 21.5, 'h': 44.0})
        self.assertEqual(self._refresh_calls(send, 'hr.rfid.ctrl'), [])
        self.assertEqual(self.c_110.temperature, 21.5)
        self.assertEqual(self.c_110.humidity, 44.0)


@tagged('post_install', '-at_install', 'rfid_refresh_views', 'rfid_telemetry_bus')
class TestRealNewsStillArrives(BusWatchCase):
    """The negative half of an ignore-list: everything NOT listed still speaks."""

    def test_a_badge_at_a_door_appears_on_the_screen(self):
        """The primary thing a monitoring screen exists to show."""
        self._add_iCon110()
        with self._patch_bus() as send:
            self._make_event(self.c_110, reader=1, event_code=3)
        self.assertTrue(
            self._refresh_calls(send, 'hr.rfid.event.user'),
            'a badge presented at a door must appear without pressing refresh')

    def test_a_refused_command_reaches_the_dispatcher(self):
        """A command the controller refused is the one thing an operator must
        not have to go looking for."""
        self._add_iCon110()
        self.c_110.read_status()
        response = self._hearbeat(self.c_110.webstack_id)
        while response and response.get('cmd', {}).get('c') != 'B3':
            response = self._send_cmd_response(response)
        with self._patch_bus() as send:
            self._send_cmd(({
                'convertor': self.c_110.webstack_id.serial,
                'response': {'id': response['cmd']['id'], 'c': 'B3', 'e': 5, 'd': ''},
                'key': self.c_110.webstack_id.key,
            }))
        self.assertTrue(
            self._refresh_calls(send, 'hr.rfid.command'),
            'a failed command must still reach the dispatcher')


@tagged('post_install', '-at_install', 'rfid_refresh_views', 'rfid_telemetry_bus')
class TestPresenceReachesTheDispatcher(BusWatchCase):
    """Going dark must arrive on the screens - and cost nothing while it does
    not happen."""

    def _go_silent_since(self, minutes_ago):
        """The state a dark module is really in: an old timestamp and a flag
        still showing green, because nothing writes while a module is quiet."""
        self.test_webstack_10_3_id.write({
            'updated_at': fields.Datetime.subtract(fields.Datetime.now(), minutes=minutes_ago),
            'last_update': True,
        })
        self.env.flush_all()

    def test_going_dark_is_announced(self):
        self._go_silent_since(60)
        with self._patch_bus() as send:
            for _i in range(PRESENCE_MISSES_BEFORE_DARK - 1):
                self.env['hr.rfid.webstack']._cron_check_presence()
        self.assertEqual(
            self._refresh_calls(send, 'hr.rfid.webstack'), [],
            'counting misses is the scan talking to itself, not to the operator')
        with self._patch_bus() as send:
            self.env['hr.rfid.webstack']._cron_check_presence()
        self.assertTrue(
            self._refresh_calls(send, 'hr.rfid.webstack'),
            'the operator must be told, not left looking at a green dot')
        self.assertFalse(self.test_webstack_10_3_id.last_update)

    def test_a_healthy_fleet_costs_nothing(self):
        """The scan runs every 5 minutes forever; on a healthy fleet it must
        write nothing and say nothing."""
        self.test_webstack_10_3_id.write({
            'updated_at': fields.Datetime.now(), 'last_update': True})
        with self._patch_bus() as send:
            self.env['hr.rfid.webstack']._cron_check_presence()
            self.env['hr.rfid.webstack']._cron_check_presence()
        self.assertEqual(self._refresh_calls(send, 'hr.rfid.webstack'), [])

    def test_one_broken_module_does_not_stop_the_scan(self):
        """A fleet-wide scan must not be hostage to a single bad record, or the
        screens silently freeze for everyone else."""
        other = self.env['hr.rfid.webstack'].create({
            'name': 'Second module', 'serial': '888111',
            'company_id': self.test_company_id, 'available': 'a',
            'tz': 'Europe/Sofia', 'active': True,
            'updated_at': fields.Datetime.subtract(fields.Datetime.now(), minutes=60),
            'last_update': True,
        })
        self._go_silent_since(60)
        real_is_reachable = type(self.test_webstack_10_3_id)._is_reachable

        def explode(module, *args, **kwargs):
            if module.id == self.test_webstack_10_3_id.id:
                raise ValueError('this module cannot be judged')
            return real_is_reachable(module, *args, **kwargs)

        with patch.object(type(self.test_webstack_10_3_id), '_is_reachable', explode):
            for _i in range(PRESENCE_MISSES_BEFORE_DARK):
                self.env['hr.rfid.webstack']._cron_check_presence()
        self.assertFalse(other.last_update,
                         'the rest of the fleet must still be checked')
