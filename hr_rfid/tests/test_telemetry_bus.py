# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""A module that stops talking must be noticed, and a quiet one must not be
mistaken for dead.

These are the facts that hold with or without the monitoring screens installed:
what the database records about a module's presence. The screen-facing half -
what actually reaches the dispatcher over the bus - is proven in
hr_rfid_refresh_views/tests/test_telemetry_bus.py, because the broadcast only
exists once that module is installed.
"""
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_presence')
class TestModulePresence(RFIDAppCase):
    """Nobody can send a message on behalf of a device that stopped talking,
    so the server has to notice the silence itself."""

    def _go_silent_since(self, minutes_ago):
        """Put the module in the state a dark one is really in.

        An old timestamp, and a flag still showing green because nothing
        writes while a module is quiet. That stale flag is exactly what the
        scan exists to correct.
        """
        self.test_webstack_10_3_id.write({
            'updated_at': fields.Datetime.subtract(
                fields.Datetime.now(), minutes=minutes_ago),
            'last_update': True,
        })
        self.env.flush_all()

    def _pretend_realtime_connected(self):
        """A module living on the websocket - it never writes updated_at."""
        return patch.object(
            type(self.test_webstack_10_3_id), 'ws_online',
            new_callable=lambda: property(lambda record: True),
        )

    def _scan(self, times=1):
        for _i in range(times):
            self.env['hr.rfid.webstack']._cron_check_presence()

    def test_a_module_gone_dark_is_flagged(self):
        self._go_silent_since(60)
        self.assertTrue(self.test_webstack_10_3_id.last_update,
                        'until the scan runs, the module still looks alive')
        self._scan(3)
        self.assertFalse(self.test_webstack_10_3_id.last_update,
                         'an hour of silence means the module is dark')

    def test_one_missed_check_in_does_not_condemn_a_module(self):
        """Only Odoo-provisioned modules are guaranteed to beat every minute;
        a module behind NAT is set by hand and may report more slowly. Flipping
        it orange on a single miss would make the indicator untrustworthy."""
        self._go_silent_since(60)
        self._scan(2)
        self.assertTrue(
            self.test_webstack_10_3_id.last_update,
            'two misses in a row are still within tolerance')
        self._scan()
        self.assertFalse(self.test_webstack_10_3_id.last_update)

    def test_contact_restores_the_full_tolerance(self):
        """A module that misses, reports, then misses again must get the whole
        allowance the second time - otherwise a flapping link is condemned on
        its first miss."""
        ws = self.test_webstack_10_3_id
        self._go_silent_since(60)
        self._scan(2)
        ws._touch_from_device({'updated_at': fields.Datetime.now()})
        self.assertEqual(ws.presence_misses, 0)
        ws.write({'updated_at': fields.Datetime.subtract(
            fields.Datetime.now(), minutes=60)})
        self._scan(2)
        self.assertTrue(ws.last_update, 'the count restarted, so it is early days')

    def test_a_module_already_dark_costs_nothing_more(self):
        """A site switched off for a week must not cost a write every five
        minutes for the rest of the week."""
        ws = self.test_webstack_10_3_id
        self._go_silent_since(60)
        self._scan(3)
        self.env.flush_all()
        untouched = ws.write_date
        self._scan(5)
        self.env.flush_all()
        self.assertEqual(ws.write_date, untouched,
                         'nothing new to say about a module already reported dark')

    def test_a_module_still_reporting_keeps_its_green_light(self):
        """The negative half: the scan must not call a healthy module dark."""
        self.test_webstack_10_3_id.write({
            'updated_at': fields.Datetime.now(), 'last_update': True})
        self.env['hr.rfid.webstack']._cron_check_presence()
        self.assertTrue(self.test_webstack_10_3_id.last_update)

    def test_a_module_that_never_connected_is_not_nagged_about(self):
        """An unfinished installation is not a communication failure - and the
        daily Todo rides the one-minute cron, so getting this wrong buries the
        installer in alerts within the minute."""
        self.test_webstack_10_3_id.write({'updated_at': False})
        self.env['hr.rfid.webstack']._notify_inactive()
        self.assertFalse(self.test_webstack_10_3_id.activity_ids)

    def test_a_check_in_marks_a_dark_module_alive_again(self):
        """Recovery is owned by the check-in itself, not by the scan: the scan
        would find the module already reachable and have nothing to say."""
        ws = self.test_webstack_10_3_id
        self._go_silent_since(60)
        self._scan(3)
        self.assertFalse(ws.last_update)
        ws._touch_from_device({'updated_at': fields.Datetime.now()})
        self.assertTrue(ws.last_update,
                        'the module is talking again, so it is alive again')

    def test_the_scan_also_catches_a_module_that_recovered_unnoticed(self):
        """Belt and braces: whatever route brought the timestamp forward, the
        next scan must agree with it."""
        ws = self.test_webstack_10_3_id
        self._go_silent_since(60)
        self._scan(3)
        ws.write({'updated_at': fields.Datetime.now()})
        self._scan()
        self.assertTrue(ws.last_update)

    def test_a_real_time_module_is_not_called_dark(self):
        """A module on the websocket never writes updated_at - judging it by
        that column alone would paint the whole real-time fleet orange."""
        self._go_silent_since(600)
        with self._pretend_realtime_connected():
            self.assertTrue(
                self.test_webstack_10_3_id._is_reachable(),
                'presence must follow the transport the module actually uses')
            self._scan(3)
        self.assertTrue(self.test_webstack_10_3_id.last_update)

    def test_the_daily_todo_ignores_a_healthy_real_time_module(self):
        """Same trap, one day later: the 24-hour Todo must not land on a module
        that has been talking over the websocket all along."""
        self._go_silent_since(60 * 30)
        with self._pretend_realtime_connected():
            self.env['hr.rfid.webstack']._notify_inactive()
        self.assertFalse(
            self.test_webstack_10_3_id.activity_ids,
            'a module we are talking to must not raise a "check the link" Todo')

    def test_the_daily_todo_still_fires_for_a_genuinely_silent_module(self):
        """The transport-aware predicate must not swallow the real case."""
        self.test_webstack_10_3_id.message_subscribe(
            partner_ids=[self.env.ref('base.user_admin').partner_id.id])
        self._go_silent_since(60 * 30)
        self.env['hr.rfid.webstack']._notify_inactive()
        self.assertTrue(
            self.test_webstack_10_3_id.activity_ids,
            'a module silent for 30 hours must raise a Todo for its followers')


@tagged('standard', 'at_install', 'rfid', 'rfid_presence')
class TestHeartbeatWritesOnlyWhatChanged(RFIDAppCase):
    """The firmware version is re-reported on every check-in; only a real
    upgrade is news."""

    def _heartbeat_payload(self, firmware):
        return {'convertor': self.test_webstack_10_3_id.serial, 'FW': firmware,
                'key': self.test_webstack_10_3_id.key, 'heartbeat': 1}

    def test_repeating_the_same_firmware_does_not_touch_the_record(self):
        ws = self.test_webstack_10_3_id
        ws.parse_heartbeat(self._heartbeat_payload('1.3400'))
        self.env.flush_all()
        untouched = ws.write_date
        ws.parse_heartbeat(self._heartbeat_payload('1.3400'))
        self.env.flush_all()
        self.assertEqual(ws.write_date, untouched,
                         'a check-in reporting the same firmware is not a change')

    def test_a_long_firmware_string_does_not_defeat_the_guard(self):
        """The field truncates at its size; comparing the stored value against
        an untruncated payload would make the guard permanently true and put
        the flood straight back."""
        ws = self.test_webstack_10_3_id
        ws.parse_heartbeat(self._heartbeat_payload('1.34.00'))
        self.env.flush_all()
        untouched = ws.write_date
        ws.parse_heartbeat(self._heartbeat_payload('1.34.00'))
        self.env.flush_all()
        self.assertEqual(ws.write_date, untouched,
                         'the same long firmware string is still not a change')

    def test_a_firmware_upgrade_is_recorded(self):
        ws = self.test_webstack_10_3_id
        ws.parse_heartbeat(self._heartbeat_payload('1.3400'))
        ws.parse_heartbeat(self._heartbeat_payload('9.9999'))
        self.assertEqual(ws.version, '9.9999',
                         'skipping the unchanged write must never skip a real one')


@tagged('standard', 'at_install', 'rfid', 'rfid_presence')
class TestThePresenceScanIsInstalled(RFIDAppCase):
    """A scan nobody runs is not a feature. Renaming the method or mistyping
    the XML would leave the product inert with a fully green suite."""

    def test_the_scan_runs_by_itself(self):
        cron = self.env.ref('hr_rfid.hr_rfid_check_module_presence_cron')
        self.assertTrue(cron.active, 'the scan must be scheduled, not dormant')
        self.assertEqual(cron.model_id.model, 'hr.rfid.webstack')
        self.assertEqual(cron.interval_type, 'minutes')
        self.assertTrue(
            callable(getattr(self.env[cron.model_id.model], '_cron_check_presence', None)),
            'the scheduled code must resolve to a real method')
