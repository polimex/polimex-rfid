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
    def setUp(self):
        super().setUp()
        # Unit tests exercise the parse / provision / auth-gating flow, not the
        # HMAC crypto itself (that is bench-verified, INTEROP 2026-07-14).
        # Clearing FW_SECRET takes the skip-HMAC path so a hello without a
        # signature is accepted for an already-keyed module.
        self.env['ir.config_parameter'].sudo().set_param(
            'hr_rfid.ws_fw_secret', '')


    def _ws(self):
        return self.test_webstack_10_3_id

    def _go_online(self, ws):
        ws.action_ws_enable()
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 3, 's': ws.serial, 'k': ws.sudo().key, 't': 'hello',
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
                'v': 3, 's': ws.serial, 'k': ws.sudo().key, 't': 'ev',
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
                'v': 3, 's': ws.serial, 'k': ws.sudo().key, 't': 'ev',
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
        # one-command-in-flight publishes only the oldest; force both to
        # Process to exercise the cid vs (controller, code) fallback in isolation.
        (db_cmd | d7_cmd).write({'status': 'Process'})
        self.assertEqual((db_cmd.status, d7_cmd.status), ('Process', 'Process'))
        # device answers a D7 result but (wrongly) tags it with the DB cid
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 3, 's': ws.serial, 'k': ws.sudo().key, 't': 'rsp',
                'cid': db_cmd.id,
                'r': {'id': ctrl.ctrl_id, 'c': 'D7', 'e': 0, 'd': ''}})
        self.assertEqual(d7_cmd.status, 'Success',
                         'the D7 answer resolves to the D7 command by code')
        self.assertEqual(db_cmd.status, 'Process',
                         'the mismatched-cid DB command is left untouched')

    def test_poison_command_does_not_abort_sync_on_connect(self):
        """F4/F12: the OLDEST queued command raising in send_command must not
        abort the whole hello - the hello_ack still goes out and the poison is
        left queued (not burned), so the next sync / HTTP retries it. With
        one-command-in-flight only the oldest is attempted per connect, so a
        second command simply waits behind it."""
        ws = self._ws()
        ctrl = self._go_online(ws)
        # a D1 (add-card) with empty numeric fields raises int('') in
        # send_command; it is the OLDEST queued command
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
                'v': 3, 's': ws.serial, 'k': ws.sudo().key, 't': 'hello'})
        types = [t for t, _ in sent]
        self.assertIn('hr_rfid.hello_ack', types,
                      'hello_ack must still be sent despite the poison command')
        self.assertNotEqual(poison.status, 'Failure',
                            'the poison command is left queued, not burned')
        self.assertEqual(healthy.status, 'Wait',
                         'the second command waits behind the in-flight one')

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
                'v': 3, 's': ws.serial, 'k': ws.sudo().key, 't': 'hello'})
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
        self.assertEqual(cmd.error, '30', 'closed for "no response from the module"')

    def test_a_command_given_up_over_real_time_lets_the_next_one_go(self):
        """A command nobody answers over the real-time connection must not hold the rest.

        Only an answer, a new command or a reconnect started the next command
        in the queue. A command that was given up produces none of those, so
        everything behind it waited for an answer that was never coming.
        """
        ws = self._ws()
        ctrl = self._go_online(ws)
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            dead = self._mk_cmd(ctrl, cmd='D1', card_number='0012340001',
                                pin_code='0000', ts_code='00000000',
                                rights_data='3', rights_mask='3')
            waiting = self._mk_cmd(ctrl, cmd='D1', card_number='0012340002',
                                   pin_code='0000', ts_code='00000000',
                                   rights_data='3', rights_mask='3')
        self.assertEqual((dead.status, waiting.status), ('Process', 'Wait'))
        dead.retries = WS_CMD_MAX_RETRIES
        self.env.flush_all()
        self.env.cr.execute(
            'UPDATE hr_rfid_command SET write_date=%s WHERE id=%s',
            (fields.Datetime.now() - timedelta(seconds=WS_CMD_REPUBLISH_TIMEOUT_S + 5), dead.id))
        dead.invalidate_recordset(['write_date'])

        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self.env['hr.rfid.command']._ws_republish_cron()

        self.assertEqual((dead.status, dead.error), ('Failure', '30'))
        self.assertEqual(waiting.status, 'Process')
        self.assertEqual(
            [c.args[2]['cid'] for c in sendone.call_args_list if c.args[1] == 'hr_rfid.cmd'],
            [waiting.id])
        self.assertTrue(
            self.env['hr.rfid.event.system'].search([
                ('controller_id', '=', ctrl.id),
                ('error_description', 'like', '0012340001'),
            ]), 'the operator is told which card was not written')

    def test_rsp_cid_targets_exact_command(self):
        ws = self._ws()
        ctrl = self._go_online(ws)
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            first = self._mk_cmd(ctrl, cmd='D7', cmd_data='')
            second = self._mk_cmd(ctrl, cmd='D7', cmd_data='')
        # one-command-in-flight publishes only the oldest, so force both to
        # Process to exercise the rsp cid-correlation logic in isolation.
        (first | second).write({'status': 'Process'})
        self.assertEqual((first.status, second.status), ('Process', 'Process'))
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 3, 's': ws.serial, 'k': ws.sudo().key, 't': 'rsp',
                'cid': second.id,
                'r': {'id': 5, 'c': 'D7', 'e': 0, 'd': ''}})
        self.assertEqual(second.status, 'Success',
                         'cid correlation targets the exact command')
        self.assertEqual(first.status, 'Process',
                         'the other identical command is untouched')

    # -- answers of the moment, and a silent controller, over real time ----

    def _hello(self, ws):
        """The module (re)connects. Returns the ids of the commands it is handed."""
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 3, 's': ws.serial, 'k': ws.sudo().key, 't': 'hello'})
        return [c.args[2]['cid'] for c in sendone.call_args_list
                if c.args[1] == 'hr_rfid.cmd']

    def _door_answer(self, ctrl):
        """The answer to a card shown at a door, out to the module."""
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            answer = self._mk_cmd(ctrl, single_attempt=True)
        self.assertEqual(answer.status, 'Process')
        return answer

    def _past_its_time(self, command):
        stale = fields.Datetime.now() - timedelta(
            seconds=WS_CMD_REPUBLISH_TIMEOUT_S + 5)
        command.sent_at = stale
        self.env.flush_all()
        self.env.cr.execute(
            'UPDATE hr_rfid_command SET write_date=%s WHERE id=%s',
            (stale, command.id))
        command.invalidate_recordset(['write_date'])

    def test_a_door_answer_is_not_republished_over_real_time(self):
        """NEGATIVE: the answer to a card shown at a door is closed when its time is up, never published again."""
        ws = self._ws()
        ctrl = self._go_online(ws)
        answer = self._door_answer(ctrl)
        self._past_its_time(answer)

        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self.env['hr.rfid.command']._ws_republish_cron()

        self.assertFalse([c for c in sendone.call_args_list
                          if c.args[1] == 'hr_rfid.cmd'])
        self.assertEqual((answer.status, answer.error, answer.retries),
                         ('Failure', '30', 0))

    def test_a_reconnect_does_not_bring_back_an_old_door_answer(self):
        """NEGATIVE: a module that comes back is not handed the door answer it missed.

        The command that was out when the connection dropped goes first on
        reconnect. For the answer to a card that would release a door for
        somebody who walked away minutes ago.
        """
        ws = self._ws()
        ctrl = self._go_online(ws)
        answer = self._door_answer(ctrl)
        self._past_its_time(answer)
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            waiting = self._mk_cmd(ctrl, cmd='D7', cmd_data='')
        self.assertEqual(waiting.status, 'Wait')

        handed = self._hello(ws)

        self.assertEqual(answer.status, 'Failure')
        self.assertEqual(handed, [waiting.id], 'the queue moves on instead')

    def test_a_reconnect_within_the_moment_leaves_the_door_answer_out(self):
        """A reconnect seconds after a card was shown hands over nothing new: the answer may still arrive."""
        ws = self._ws()
        ctrl = self._go_online(ws)
        answer = self._door_answer(ctrl)
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            waiting = self._mk_cmd(ctrl, cmd='D7', cmd_data='')

        handed = self._hello(ws)

        self.assertEqual(handed, [])
        self.assertEqual((answer.status, waiting.status), ('Process', 'Wait'))

    def _answers(self, ws, command, error):
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 3, 's': ws.serial, 'k': ws.sudo().key, 't': 'rsp',
                'cid': command.id,
                'r': {'id': 5, 'c': command.cmd[:2], 'e': error, 'd': ''}})
        return [c.args[2]['cid'] for c in sendone.call_args_list
                if c.args[1] == 'hr_rfid.cmd']

    def test_a_silent_controller_over_real_time_is_tried_again_and_then_given_up(self):
        """ "The controller is silent" puts the command back in the queue; after its attempts it is closed as that.

        Handing it over in place - the way a reply to a report does - marked
        it sent while nothing went out, and the queue waited for an answer to
        nothing.
        """
        ws = self._ws()
        ctrl = self._go_online(ws)
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            command = self._mk_cmd(ctrl, cmd='D7', cmd_data='', single_attempt=False)
        self.assertEqual(command.status, 'Process')

        published = self._answers(ws, command, 20)

        self.assertEqual(published, [command.id], 'it really goes out again')
        self.assertEqual((command.status, command.retries), ('Process', 1))

        command.retries = WS_CMD_MAX_RETRIES
        published = self._answers(ws, command, 20)

        self.assertEqual(published, [])
        self.assertEqual((command.status, command.error), ('Failure', '20'))

    def test_a_door_answer_met_with_silence_over_real_time_is_closed(self):
        """NEGATIVE: "the controller is silent" does not publish the answer to a card a second time."""
        ws = self._ws()
        ctrl = self._go_online(ws)
        answer = self._door_answer(ctrl)

        published = self._answers(ws, answer, 20)

        self.assertEqual(published, [])
        self.assertEqual((answer.status, answer.error, answer.retries),
                         ('Failure', '20', 0))

    def test_an_event_that_fails_over_real_time_keeps_what_was_sent(self):
        """A passage that could not be handled over real time is written down with what went wrong.

        Also on a site that does not keep its communication: the record of a
        failure is not a debugging aid.
        """
        self.env['ir.config_parameter'].sudo().set_param(
            'hr_rfid.save_webstack_communications', 'false')
        ws = self._ws()
        ctrl = self._go_online(ws)
        with patch.object(type(ws), '_hw_parse_event',
                          side_effect=ValueError('it could not be placed')):
            self._dispatch_ev(ws, 31, [self._event(ctrl, 7)])

        kept = self.env['hr.rfid.event.system'].search([
            ('webstack_id', '=', ws.id),
            ('error_description', '=', 'Real-time event could not be processed'),
        ], order='id desc', limit=1)
        self.assertTrue(kept)
        self.assertIn(self.test_card_employee.number, kept.input_js or '')
        self.assertIn('it could not be placed', kept.input_js or '')
