# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Command delivery over the websocket channel (package A stage 4 of
docs/odoo-bus/ODOO_BUS_ODOO_PLAN.md §1.6; SPEC §6.2/§5.4). The command
queue itself (Wait/Process + HTTP piggyback) must stay untouched - both
transports coexist."""
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.models.hr_rfid_command_ws import (
    WS_CMD_MAX_RETRIES,
    WS_CMD_REPUBLISH_TIMEOUT_S,
)
from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_ws')
class TestWsCommands(RFIDAppCase):

    def _ws(self):
        return self.test_webstack_10_3_id

    def _go_online(self, ws):
        ws.action_ws_enable()
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 1, 's': ws.serial, 'k': ws.ws_token, 't': 'hello',
                'ctrl': [5]})
        ctrl = ws.controllers.filtered(lambda c: c.ctrl_id == 5)
        # drain the F0 setup command the hello provisioning queued+published,
        # so each test asserts only its own traffic
        self.env['hr.rfid.command'].sudo().search([
            ('webstack_id', '=', ws.id),
            ('status', 'in', ('Wait', 'Process'))]).write({'status': 'Success'})
        return ctrl

    def _mk_cmd(self, ctrl, **vals):
        base = {'webstack_id': ctrl.webstack_id.id, 'controller_id': ctrl.id,
                'cmd': 'DB', 'cmd_data': '400300'}
        base.update(vals)
        return self.env['hr.rfid.command'].sudo().create(base)

    # ------------------------------------------------------------------

    def test_create_publishes_when_online(self):
        ws = self._ws()
        ctrl = self._go_online(ws)
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            cmd = self._mk_cmd(ctrl)
        publishes = [c for c in sendone.call_args_list
                     if c.args[1] == 'hr_rfid.cmd']
        self.assertEqual(len(publishes), 1)
        payload = publishes[0].args[2]
        self.assertEqual(payload['cid'], cmd.id)
        self.assertEqual(payload['cmd'],
                         {'id': 5, 'c': 'DB', 'd': '400300'},
                         'same wire payload as the HTTP delivery')
        self.assertEqual(cmd.status, 'Process',
                         'published = in delivery, same as an HTTP send')

    def test_create_offline_stays_wait_for_http(self):
        ws = self._ws()
        ctrl = self._go_online(ws)
        ws.sudo().ws_last_seen = fields.Datetime.now() - timedelta(hours=1)
        ws.invalidate_recordset(['ws_online'])
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            cmd = self._mk_cmd(ctrl)
        self.assertFalse([c for c in sendone.call_args_list
                          if c.args[1] == 'hr_rfid.cmd'])
        self.assertEqual(cmd.status, 'Wait')
        # ... and the classic HTTP piggyback still delivers it
        result = ws.check_for_unsent_cmd(200)
        self.assertEqual(result['cmd']['id'], 5)
        self.assertEqual(cmd.status, 'Process')

    def test_connect_sync_republishes_pending(self):
        ws = self._ws()
        ctrl = self._go_online(ws)
        ws.sudo().ws_last_seen = fields.Datetime.now() - timedelta(hours=1)
        ws.invalidate_recordset(['ws_online'])
        cmd = self._mk_cmd(ctrl)               # offline -> Wait, no publish
        self.assertEqual(cmd.status, 'Wait')
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 1, 's': ws.serial, 'k': ws.ws_token, 't': 'hello'})
        publishes = [c for c in sendone.call_args_list
                     if c.args[1] == 'hr_rfid.cmd']
        self.assertEqual(len(publishes), 1, 'sync-on-connect delivers it')
        self.assertEqual(publishes[0].args[2]['cid'], cmd.id)
        self.assertEqual(cmd.status, 'Process')

    def test_republish_cron_retries_then_fails(self):
        ws = self._ws()
        ctrl = self._go_online(ws)
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            cmd = self._mk_cmd(ctrl)
        self.assertEqual(cmd.status, 'Process')
        Command = self.env['hr.rfid.command']
        stale = fields.Datetime.now() - timedelta(
            seconds=WS_CMD_REPUBLISH_TIMEOUT_S + 5)

        def age(record):
            self.env.flush_all()   # materialise pending writes first, else
            # the later ORM flush would bump write_date back to now()
            self.env.cr.execute(
                'UPDATE hr_rfid_command SET write_date=%s WHERE id=%s',
                (stale, record.id))
            record.invalidate_recordset(['write_date'])

        age(cmd)
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            Command._ws_republish_cron()
        self.assertEqual(
            len([c for c in sendone.call_args_list
                 if c.args[1] == 'hr_rfid.cmd']), 1, 'stale -> re-published')
        self.assertEqual(cmd.retries, 1)
        # exhaust the retry budget -> Failure, no more publishes
        cmd.retries = WS_CMD_MAX_RETRIES
        age(cmd)
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            Command._ws_republish_cron()
        self.assertFalse([c for c in sendone.call_args_list
                          if c.args[1] == 'hr_rfid.cmd'])
        self.assertEqual(cmd.status, 'Failure')

    def test_rsp_cid_targets_exact_command(self):
        ws = self._ws()
        ctrl = self._go_online(ws)
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            first = self._mk_cmd(ctrl, cmd='D7', cmd_data='')
            second = self._mk_cmd(ctrl, cmd='D7', cmd_data='')
        self.assertEqual((first.status, second.status), ('Process', 'Process'))
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 1, 's': ws.serial, 'k': ws.ws_token, 't': 'rsp',
                'cid': second.id,
                'r': {'id': 5, 'c': 'D7', 'e': 0, 'd': ''}})
        self.assertEqual(second.status, 'Success',
                         'cid correlation targets the exact command')
        self.assertEqual(first.status, 'Process',
                         'the other identical command is untouched')