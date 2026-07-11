# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Websocket ingress tests: ir.websocket hook -> _ws_dispatch -> the SAME
hardware parse core as the HTTP route (package A stage 3 of
docs/odoo-bus/ODOO_BUS_ODOO_PLAN.md; wire contract ODOO_BUS_PROTOCOL_SPEC.md)."""
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.models.hr_rfid_webstack_ws import (
    WS_AUTH_FAIL_THRESHOLD,
    WS_PROTO_VERSION,
)
from odoo.addons.hr_rfid.models.hr_rfid_ws_dedup import WS_DEDUP_RETENTION_DAYS
from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)

# Verified iCON110 F0 payload (2 readers) - same vector the HTTP tests use
# (tests/common.py _get_F0_response for c_110).
F0_ICON110 = '0006000400000704000000030000030201050208000200010502060003000506'


@tagged('standard', 'at_install', 'rfid', 'rfid_ws')
class TestWsDispatch(RFIDAppCase):

    def _ws(self):
        return self.test_webstack_10_3_id

    def _enable(self):
        ws = self._ws()
        ws.action_ws_enable()
        return ws

    def _msg(self, mtype, ws=None, token=None, v=WS_PROTO_VERSION, **payload):
        ws = ws or self._ws()
        data = {'v': v, 's': ws.serial, 'k': token or ws.ws_token, 't': mtype}
        data.update(payload)
        return data

    def _dispatch(self, data):
        # through the real entry point (the ir.websocket extension)
        self.env['ir.websocket']._serve_ir_websocket('hr_rfid', data)

    def _event_dict(self, ctrl_id=5, bos=1, card=None, event_n=4, reader=1):
        return {
            'id': ctrl_id, 'event_n': event_n, 'bos': bos, 'tos': bos,
            'card': card or self.test_card_employee.number,
            'cmd': 'FA', 'err': 0, 'reader': reader,
            'dt': '00000000000000',
            'date': self.test_date_10_3, 'time': self.test_time_10_3,
            'day': self.test_dow_10_3,
        }

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def test_bad_token_is_ignored(self):
        ws = self._enable()
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('hello', token='f' * 32))
        sendone.assert_not_called()
        self.assertFalse(ws.ws_last_seen, 'auth failure must not touch presence')

    def test_auth_flood_raises_one_system_event(self):
        ws = self._enable()
        Sys = self.env['hr.rfid.event.system']
        before = Sys.search_count([('webstack_id', '=', ws.id)])
        for _i in range(WS_AUTH_FAIL_THRESHOLD + 3):
            self._dispatch(self._msg('hb', token='f' * 32))
        after = Sys.search_count([('webstack_id', '=', ws.id)])
        self.assertEqual(after - before, 1,
                         'exactly ONE system event at the flood threshold')

    def test_disabled_module_is_ignored(self):
        ws = self._ws()
        ws.sudo().ws_token = 'a' * 32  # token present but channel disabled
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('hello'))
        sendone.assert_not_called()

    def test_unknown_serial_is_safe(self):
        self._dispatch({'v': 1, 's': '999999', 'k': 'a' * 32, 't': 'hello'})
        # nothing to assert beyond "no exception, no records"
        self.assertFalse(self.env['hr.rfid.webstack'].search(
            [('serial', '=', '999999')]))

    # ------------------------------------------------------------------
    # hello / hb
    # ------------------------------------------------------------------

    def test_hello_acks_and_updates(self):
        ws = self._enable()
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('hello', fw='2.01', ctrl=[7]))
        self.assertTrue(ws.ws_last_seen)
        self.assertEqual(ws.sudo().version, '2.01')
        self.assertEqual(ws.ws_proto, WS_PROTO_VERSION)
        self.assertFalse(ws.ws_provision_pending)
        self.assertTrue(ws.controllers.filtered(lambda c: c.ctrl_id == 7),
                        'hello ctrl list pre-provisions controllers')
        acks = [c for c in sendone.call_args_list
                if c.args[1] == 'hr_rfid.hello_ack']
        self.assertEqual(len(acks), 1)
        payload = acks[0].args[2]
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['proto'], WS_PROTO_VERSION)
        self.assertGreater(payload['hb_interval'], 0)
        self.assertIn('rl', payload)

    def test_hello_proto_mismatch(self):
        ws = self._enable()
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('hello', v=99))
        channel, mtype, payload = sendone.call_args.args
        self.assertEqual(mtype, 'hr_rfid.hello_ack')
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['err'], 'proto')
        self.assertTrue(ws.ws_last_seen, 'valid token still updates presence')

    def test_hb_provisions_controllers(self):
        ws = self._enable()
        self._dispatch(self._msg('hb', n=5, ctrl=[9]))
        self.assertTrue(ws.controllers.filtered(lambda c: c.ctrl_id == 9))
        self.assertTrue(ws.ws_online)

    # ------------------------------------------------------------------
    # ev batch: same core, dedup, ack
    # ------------------------------------------------------------------

    def test_ev_from_new_controller_not_consumed(self):
        """An event from an unknown controller mirrors the HTTP 400 path:
        the controller is provisioned, the F0 setup rides inline in the ack,
        and the event itself is NOT consumed (ok:false -> the device keeps
        it in the FIFO and re-sends after the setup)."""
        ws = self._enable()
        Sys = self.env['hr.rfid.event.system']
        before = Sys.search_count([('webstack_id', '=', ws.id)])
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('ev', bid=101, ev=[self._event_dict()]))
        self.assertTrue(ws.controllers.filtered(lambda c: c.ctrl_id == 5),
                        'the unknown controller is auto-provisioned')
        self.assertEqual(Sys.search_count([('webstack_id', '=', ws.id)]), before)
        acks = [c for c in sendone.call_args_list
                if c.args[1] == 'hr_rfid.ev_ack']
        self.assertEqual(len(acks), 1)
        payload = acks[0].args[2]
        self.assertEqual(payload['bid'], 101)
        self.assertEqual(payload['res'], [{'i': 0, 'ok': False, 'dup': False}],
                         'not consumed - the device must re-send it')
        self.assertEqual(payload['cmd']['cmd']['c'], 'F0',
                         'the setup command rides inline in the ack')

    def test_ev_batch_processes_and_acks(self):
        """On a known controller the same core as HTTP processes the event
        (here: reader-less controller -> system event, status 200 -> ok)."""
        ws = self._enable()
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self._dispatch(self._msg('hello', ctrl=[5]))   # provision ctrl 5
        Sys = self.env['hr.rfid.event.system']
        before = Sys.search_count([('webstack_id', '=', ws.id)])
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('ev', bid=102, ev=[self._event_dict()]))
        self.assertGreater(Sys.search_count([('webstack_id', '=', ws.id)]),
                           before, 'processed by the same core as HTTP')
        payload = [c for c in sendone.call_args_list
                   if c.args[1] == 'hr_rfid.ev_ack'][-1].args[2]
        self.assertEqual(payload['bid'], 102)
        self.assertEqual(payload['res'], [{'i': 0, 'ok': True, 'dup': False}])

    def test_ev_resend_is_deduplicated(self):
        ws = self._enable()
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self._dispatch(self._msg('hello', ctrl=[5]))   # provision ctrl 5
        event = self._event_dict(bos=2)
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self._dispatch(self._msg('ev', bid=201, ev=[event]))
        Sys = self.env['hr.rfid.event.system']
        count_after_first = Sys.search_count([('webstack_id', '=', ws.id)])
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('ev', bid=201, ev=[event]))
        self.assertEqual(
            Sys.search_count([('webstack_id', '=', ws.id)]), count_after_first,
            'a re-sent batch must not create duplicate records')
        payload = sendone.call_args_list[-1].args[2]
        self.assertEqual(payload['res'], [{'i': 0, 'ok': True, 'dup': True}])

    def test_ev_malformed_entry_is_logged_and_acked(self):
        ws = self._enable()
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            with self.assertLogs(
                    'odoo.addons.hr_rfid.models.hr_rfid_webstack_ws',
                    level='WARNING'):
                self._dispatch(self._msg('ev', bid=301, ev=['garbage']))
        payload = sendone.call_args_list[-1].args[2]
        self.assertEqual(payload['res'][0]['ok'], False,
                         'delivered-and-logged: acked with ok=false')

    # ------------------------------------------------------------------
    # Full round-trip: hello -> F0 response over WS -> ev64 inline command
    # ------------------------------------------------------------------

    def test_f0_rsp_and_ev64_inline_command(self):
        ws = self._enable()
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self._dispatch(self._msg('hello', fw='2.01', ctrl=[5]))
        ctrl = ws.controllers.filtered(lambda c: c.ctrl_id == 5)
        self.assertTrue(ctrl)
        # the hello provisioning queued an F0 (read info) command; deliver
        # its response over the WS rsp path (same parse_response core)
        cmd = self.env['hr.rfid.command'].sudo().search(
            [('webstack_id', '=', ws.id), ('controller_id', '=', ctrl.id),
             ('cmd', '=', 'F0')], limit=1)
        self.assertTrue(cmd, 'hello provisioning queues the F0 read')
        cmd.status = 'Process'
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self._dispatch(self._msg('rsp', cid=cmd.id,
                                     r={'id': 5, 'c': 'F0', 'e': 0,
                                        'd': F0_ICON110}))
        self.assertEqual(cmd.status, 'Success', 'rsp closes the command')
        self.assertEqual(ctrl.readers, 2, 'F0 parsed: iCON110 has 2 readers')
        # ev64 (cloud permission) now has a reader; the deny/grant command
        # must ride INLINE in the ev_ack (controller timeout, SPEC §6.3)
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg(
                'ev', bid=401,
                ev=[self._event_dict(ctrl_id=5, bos=3, event_n=64)]))
        payload = [c for c in sendone.call_args_list
                   if c.args[1] == 'hr_rfid.ev_ack'][-1].args[2]
        self.assertEqual(payload['res'][0], {'i': 0, 'ok': True, 'dup': False})
        self.assertIn('cmd', payload, 'ev64 reply rides inline in the ack')
        self.assertEqual(payload['cmd']['cmd']['id'], 5)
        self.assertEqual(payload['cmd']['cmd']['c'], 'DB')
        self.assertGreater(payload['cmd']['cid'], 0,
                           'inline command carries its correlation id')

    # ------------------------------------------------------------------
    # Dedup GC
    # ------------------------------------------------------------------

    def test_dedup_gc(self):
        ws = self._enable()
        Dedup = self.env['hr.rfid.ws.dedup']
        self.assertTrue(Dedup._claim(ws, 1, 1, 'x'))
        old = Dedup.sudo().search([('webstack_id', '=', ws.id)], limit=1)
        old.create_date = fields.Datetime.now() - timedelta(
            days=WS_DEDUP_RETENTION_DAYS + 1)
        done, has_more = Dedup._gc_ws_dedup()
        self.assertGreaterEqual(done, 1)
        self.assertFalse(Dedup.sudo().search(
            [('webstack_id', '=', ws.id), ('ev_ts', '=', 'x')]))
