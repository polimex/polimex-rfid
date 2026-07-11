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

    def _event(self, ctrl, bos, event_n=4):
        return {'id': ctrl.ctrl_id, 'event_n': event_n, 'bos': bos, 'tos': bos,
                'card': self.test_card_employee.number, 'cmd': 'FA', 'err': 0,
                'reader': 1, 'dt': '00000000000000',
                'date': self.test_date_10_3, 'time': self.test_time_10_3,
                'day': self.test_dow_10_3}

    def _dispatch_ev(self, ws, bid, events):
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 1, 's': ws.serial, 'k': ws.ws_token, 't': 'ev',
                'bid': bid, 'ev': events})

    def test_event_batch_does_not_burn_command_retries(self):
        """F1: a multi-event batch must run the queued-command piggyback for
        at most the FIRST event - it must NOT re-flip/retry a pending command
        once per event and burn it to a false Failure (the device cannot
        answer between events of one batch)."""
        ws = self._ws()
        ctrl = self._go_online(ws)
        cmd = self._mk_cmd(ctrl)   # Wait, published + drained by _go_online...
        cmd.write({'status': 'Wait', 'retries': 0})  # ... reset to a clean Wait
        # a batch of 6 distinct card events (> the 5-retry give-up limit)
        events = [self._event(ctrl, bos=b) for b in range(1, 7)]
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 1, 's': ws.serial, 'k': ws.ws_token, 't': 'ev',
                'bid': 500, 'ev': events})
        self.assertNotEqual(cmd.status, 'Failure',
                            'the command must not be burned to Failure by a batch')
        self.assertLessEqual(cmd.retries, 1,
                             'at most one attempt per batch, not one per event')

    def test_rsp_wrong_cid_falls_back_to_code_match(self):
        """F2: a cid that points at a command whose code does not match the
        response is rejected - the answer attaches to the correct command via
        the classic (controller, code) match, never to the wrong one."""
        ws = self._ws()
        ctrl = self._go_online(ws)
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            db_cmd = self._mk_cmd(ctrl, cmd='DB', cmd_data='400300')
            d7_cmd = self._mk_cmd(ctrl, cmd='D7', cmd_data='')
        self.assertEqual((db_cmd.status, d7_cmd.status), ('Process', 'Process'))
        # device answers a D7 result but (wrongly) tags it with the DB cid
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 1, 's': ws.serial, 'k': ws.ws_token, 't': 'rsp',
                'cid': db_cmd.id,
                'r': {'id': ctrl.ctrl_id, 'c': 'D7', 'e': 0, 'd': ''}})
        self.assertEqual(d7_cmd.status, 'Success',
                         'the D7 answer resolves to the D7 command by code')
        self.assertEqual(db_cmd.status, 'Process',
                         'the mismatched-cid DB command is left untouched')

    def test_poison_command_does_not_abort_sync_on_connect(self):
        """F4/F12: one command that raises in send_command must not abort the
        whole hello - the hello_ack still goes out and the healthy command is
        still delivered."""
        ws = self._ws()
        ctrl = self._go_online(ws)
        # a D1 (add-card) with empty numeric fields raises int('') in
        # send_command; a healthy DB queued alongside it
        poison = self._mk_cmd(ctrl, cmd='D1', cmd_data='', card_number='',
                              pin_code='', ts_code='0', rights_data='',
                              rights_mask='')
        poison.write({'status': 'Wait'})
        healthy = self._mk_cmd(ctrl, cmd='DB', cmd_data='400300')
        healthy.write({'status': 'Wait'})
        sent = []
        with patch.object(type(self.env['bus.bus']), '_sendone',
                          side_effect=lambda ch, t, p: sent.append((t, p))):
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 1, 's': ws.serial, 'k': ws.ws_token, 't': 'hello'})
        types = [t for t, _ in sent]
        self.assertIn('hr_rfid.hello_ack', types,
                      'hello_ack must still be sent despite the poison command')
        self.assertTrue(
            any(t == 'hr_rfid.cmd' and p['cid'] == healthy.id for t, p in sent),
            'the healthy command is still delivered')

    def test_republish_cron_climbs_to_giveup_on_poison(self):
        """F5: a command that keeps failing to publish still climbs its retry
        count toward the give-up limit (the increment survives the failed
        publish savepoint) - it does not starve the cron forever."""
        ws = self._ws()
        ctrl = self._go_online(ws)
        cmd = self._mk_cmd(ctrl, cmd='DB', cmd_data='400300')
        cmd.write({'status': 'Process', 'retries': 0})
        Command = self.env['hr.rfid.command']
        stale = fields.Datetime.now() - timedelta(
            seconds=WS_CMD_REPUBLISH_TIMEOUT_S + 5)

        def age():
            self.env.flush_all()
            self.env.cr.execute(
                'UPDATE hr_rfid_command SET write_date=%s WHERE id=%s',
                (stale, cmd.id))
            cmd.invalidate_recordset(['write_date'])

        # make the publish raise; the retry must still increment
        with patch.object(type(ws), '_ws_publish_command',
                          side_effect=ValueError('boom')):
            age()
            Command._ws_republish_cron()
        self.assertEqual(cmd.retries, 1,
                         'the attempt is counted even though the publish failed')

    def test_create_publish_failure_does_not_break_creation(self):
        """F6: a publish failure at create-time must never break the business
        transaction - the command is still created and stays queued for the
        classic delivery."""
        ws = self._ws()
        ctrl = self._go_online(ws)
        with patch.object(type(ws), '_ws_publish_command',
                          side_effect=ValueError('boom')):
            cmd = self._mk_cmd(ctrl, cmd='DB', cmd_data='400300')
        self.assertTrue(cmd.exists(), 'the command is created despite the failure')
        self.assertEqual(cmd.status, 'Wait',
                         'it stays queued for the HTTP / next-sync delivery')

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