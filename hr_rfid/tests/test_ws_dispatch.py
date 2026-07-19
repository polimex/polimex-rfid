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

    def setUp(self):
        super().setUp()
        # Unit tests exercise the parse / provision / auth-gating flow, not the
        # HMAC crypto itself (that is bench-verified, INTEROP 2026-07-14).
        # Clearing FW_SECRET takes the skip-HMAC path so a hello without a
        # signature is accepted for an already-keyed module.
        self.env['ir.config_parameter'].sudo().set_param(
            'hr_rfid.ws_fw_secret', '')

    def _enable(self):
        ws = self._ws()
        ws.action_ws_enable()
        return ws

    def _msg(self, mtype, ws=None, k=None, v=WS_PROTO_VERSION, **payload):
        ws = ws or self._ws()
        # proto 3: `k` is the module key (server_push_key), the channel
        # credential; defaults to the record's key when the test does not
        # override it with a bad value.
        data = {'v': v, 's': ws.serial, 'k': k or ws.sudo().key, 't': mtype}
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

    def test_bad_key_is_refused_with_nack(self):
        ws = self._enable()
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('hello', k='f' * 32))
        # A wrong key never touches presence or processing...
        self.assertFalse(ws.ws_last_seen, 'auth failure must not touch presence')
        # ...but a hello gets an explicit auth nack (ok:false) so the device
        # falls back to HTTP instead of sitting deaf-mute (SPEC §9.2, v1.1).
        acks = [c for c in sendone.call_args_list
                if c.args[1] == 'hr_rfid.hello_ack']
        self.assertEqual(len(acks), 1, 'a refused hello is nacked')
        self.assertFalse(acks[0].args[2]['ok'])
        self.assertEqual(acks[0].args[2]['err'], 'auth')

    def test_keyless_device_presenting_0000_is_refused(self):
        """A keyless (never-provisioned / re-keyed) module presenting the insecure
        '0000' is NOT adopted and is refused - it needs a real generated key."""
        ws = self._enable()
        ws.action_ws_rekey()   # clear the key -> keyless
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self._dispatch(self._msg('hello', k='0000'))
        self.assertFalse(ws.sudo().key, 'keyless + 0000 -> not adopted, stays keyless')
        self.assertFalse(ws.sudo().ws_last_seen,
                         'a refused unprovisioned hello does not touch presence')

    def test_heal_0000_to_real_key_adopts_onto_same_endpoint(self):
        """G1 heal: a module stored with the insecure '0000' presents a new
        NON-zero key with a VALID HMAC -> the key is adopted (healed) onto the
        SAME endpoint, the serial mapping + advancing watermark are preserved, and
        needs-provisioning clears. Enables the firmware auto-heal with no per-device
        cloud step."""
        import hashlib
        import hmac as _hmac
        ws = self._enable()                      # key='0000' (fixture)
        ws.sudo().ws_last_n = 100
        endpoint_before = ws.sudo().endpoint_id
        secret = 'unit-fw-secret'
        self.env['ir.config_parameter'].sudo().set_param(
            'hr_rfid.ws_fw_secret', secret)
        new_key, n = 'A85F', 200
        auth = _hmac.new(
            secret.encode(),
            ('%s|%s|%s' % (ws.serial, new_key, n)).encode(),
            hashlib.sha256).hexdigest()
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self._dispatch(self._msg('hello', k=new_key, n=n, auth=auth))
        ws.invalidate_recordset()
        self.assertEqual(ws.sudo().key, new_key,
                         'the insecure 0000 was healed to the new real key')
        self.assertEqual(ws.sudo().endpoint_id, endpoint_before,
                         'healed onto the SAME endpoint (mapping preserved)')
        self.assertEqual(ws.sudo().ws_last_n, n, 'anti-replay watermark advanced')
        self.assertFalse(ws.sudo().ws_needs_provisioning,
                         'a real key clears needs-provisioning')

    def test_real_key_is_never_overridden_by_a_different_key(self):
        """A device with a REAL (non-0000) key is NOT healable: a different key,
        even HMAC-valid, is refused (only the insecure 0000 placeholder is soft)."""
        import hashlib
        import hmac as _hmac
        ws = self._enable()
        ws.sudo().key = 'REAL'
        ws.sudo().ws_last_n = 100
        secret = 'unit-fw-secret'
        self.env['ir.config_parameter'].sudo().set_param(
            'hr_rfid.ws_fw_secret', secret)
        other, n = 'BEEF', 200
        auth = _hmac.new(
            secret.encode(), ('%s|%s|%s' % (ws.serial, other, n)).encode(),
            hashlib.sha256).hexdigest()
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('hello', k=other, n=n, auth=auth))
        self.assertEqual(ws.sudo().key, 'REAL', 'a real key is never overridden')
        acks = [c for c in sendone.call_args_list
                if c.args[1] == 'hr_rfid.hello_ack']
        self.assertTrue(acks and not acks[0].args[2]['ok'],
                        'the mismatched hello on a real key is refused')

    def test_auth_flood_raises_one_system_event(self):
        ws = self._enable()
        Sys = self.env['hr.rfid.event.system']
        before = Sys.search_count([('webstack_id', '=', ws.id)])
        for _i in range(WS_AUTH_FAIL_THRESHOLD + 3):
            self._dispatch(self._msg('hb', k='f' * 32))
        after = Sys.search_count([('webstack_id', '=', ws.id)])
        self.assertEqual(after - before, 1,
                         'exactly ONE system event at the flood threshold')

    def test_disabled_module_is_refused_with_nack(self):
        ws = self._ws()  # never enabled -> ws_enabled is False
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('hello'))
        self.assertFalse(ws.ws_last_seen, 'a disabled module is not processed')
        # A disabled module refuses the hello (ok:false) so the device parks
        # on HTTP rather than staying on a dead real-time socket.
        acks = [c for c in sendone.call_args_list
                if c.args[1] == 'hr_rfid.hello_ack']
        self.assertEqual(len(acks), 1)
        self.assertFalse(acks[0].args[2]['ok'])

    def test_unknown_serial_is_safe(self):
        self._dispatch({'v': 3, 's': '999999', 'k': 'a' * 32, 't': 'hello'})
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

    def test_ev_malformed_entry_is_consumed_not_looped(self):
        """A non-dict / unparseable entry is FINAL - consume it (ok:true +
        system event) so a device does not loop re-sending garbage, and
        never let it reach the controller-create path."""
        ws = self._enable()
        Sys = self.env['hr.rfid.event.system']
        before = Sys.search_count([('webstack_id', '=', ws.id)])
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            with self.assertLogs(
                    'odoo.addons.hr_rfid.models.hr_rfid_webstack_ws',
                    level='WARNING'):
                self._dispatch(self._msg('ev', bid=301, ev=['garbage']))
        payload = sendone.call_args_list[-1].args[2]
        self.assertEqual(payload['res'][0], {'i': 0, 'ok': True, 'dup': False},
                         'malformed is final -> consumed, not re-sent forever')
        self.assertEqual(Sys.search_count([('webstack_id', '=', ws.id)]),
                         before + 1, 'operator sees it as a system event')

    def test_ev_out_of_range_controller_id_dropped(self):
        """An event whose controller id is outside the RS-485 range (1..254)
        is dropped (consumed + logged) and creates NO controller - bounds the
        tables an authenticated device can grow (F4)."""
        ws = self._enable()
        for bad_id in (0, 255, 999, 'x'):
            ev = self._event_dict(bos=1)
            ev['id'] = bad_id
            with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
                self._dispatch(self._msg('ev', bid=310, ev=[ev]))
            payload = [c for c in sendone.call_args_list
                       if c.args[1] == 'hr_rfid.ev_ack'][-1].args[2]
            self.assertEqual(payload['res'][0], {'i': 0, 'ok': True, 'dup': False},
                             'bad id %r -> consumed' % bad_id)
        self.assertFalse(
            ws.controllers.filtered(lambda c: c.ctrl_id in (0, 255, 999)),
            'no controller is created from an out-of-range id')

    def test_ev_bad_time_is_consumed(self):
        """A bad controller clock is consumed (ok:true) like the HTTP path's
        status 200, so a permanently-bad-time event does not loop forever."""
        ws = self._enable()
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self._dispatch(self._msg('hello', ctrl=[5]))
        ev = self._event_dict(ctrl_id=5, bos=7)
        ev['time'] = '99:99:99'   # unparseable -> BadTimeException in the core
        Sys = self.env['hr.rfid.event.system']
        before = Sys.search_count([('webstack_id', '=', ws.id)])
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('ev', bid=320, ev=[ev]))
        payload = [c for c in sendone.call_args_list
                   if c.args[1] == 'hr_rfid.ev_ack'][-1].args[2]
        self.assertTrue(payload['res'][0]['ok'], 'bad time -> consume like HTTP 200')
        self.assertEqual(Sys.search_count([('webstack_id', '=', ws.id)]),
                         before + 1)

    def test_malformed_rsp_does_not_escape_to_transport(self):
        """A malformed rsp (missing 'c') must be caught in-dispatch: the HTTP
        twin wraps parse_response, and the WS path must not let it escape to
        the bus frame loop (1011 close + ERROR log). It is logged as a
        warning + system event, and _ws_dispatch returns normally (F2)."""
        ws = self._enable()
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self._dispatch(self._msg('hello', ctrl=[5]))
        Sys = self.env['hr.rfid.event.system']
        before = Sys.search_count([('webstack_id', '=', ws.id)])
        with self.assertLogs(
                # the dispatch-level isolation warning is emitted by the shared
                # transport base (polimex_ws), where _ws_dispatch now lives; the
                # AC event.system record is still written via the branch sink.
                'odoo.addons.polimex_ws.models.ws_mixin',
                level='WARNING'):
            # missing 'c' -> KeyError inside parse_response; must NOT raise out
            self._dispatch(self._msg('rsp', cid=0, r={'id': 5, 'e': 0}))
        self.assertEqual(Sys.search_count([('webstack_id', '=', ws.id)]),
                         before + 1, 'malformed message -> one system event')

    def test_auth_fail_writes_are_bounded(self):
        """Bad-token frames increment the counter only up to the threshold
        (F1): once the single system event has fired, further frames in the
        window do NOT keep writing the row."""
        ws = self._enable()
        for _i in range(WS_AUTH_FAIL_THRESHOLD + 5):
            self._dispatch(self._msg('hb', k='f' * 32))
        self.assertEqual(ws.ws_auth_fail_count, WS_AUTH_FAIL_THRESHOLD,
                         'counter is capped at the threshold, not unbounded')

    def test_poisoned_fw_does_not_break_parsing(self):
        """A non-numeric fw from the device (hello) must not poison the
        version-derived computes/command builders (F5b): the module still
        works and events still parse."""
        ws = self._enable()
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self._dispatch(self._msg('hello', fw='abc', ctrl=[5]))
        self.assertEqual(ws.sudo().version, 'abc')
        # version-derived helpers must not raise on the poisoned value
        self.assertIn(ws.is_10_3(), (True, False))
        self.assertIn(ws.is_100_1(), (True, False))
        self.assertTrue(ws.time_format, 'time_format compute survived')
        # ... and a real event on that module still processes
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('ev', bid=330,
                                     ev=[self._event_dict(ctrl_id=5, bos=1)]))
        payload = [c for c in sendone.call_args_list
                   if c.args[1] == 'hr_rfid.ev_ack'][-1].args[2]
        self.assertEqual(payload['res'][0]['ok'], True)

    # ------------------------------------------------------------------
    # Full round-trip: hello -> F0 response over WS -> ev64 inline command
    # ------------------------------------------------------------------

    def test_f0_rsp_and_inline_command_on_event(self):
        """Full round-trip: hello -> F0 read queued -> F0 response over the WS
        rsp path (the SAME parse_response core as HTTP) closes the command and
        parses the reader count. Then a card event piggybacks the queued
        controller command INLINE in the ev_ack, so the controller timeout is
        honoured (SPEC §6.3) - the same controller-timeout delivery the HTTP
        reply uses."""
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
        # Drain F0's controller-setup batch and queue ONE known command; a card
        # event must then piggyback it INLINE in the ev_ack (SPEC §6.3).
        self.env['hr.rfid.command'].sudo().search([
            ('webstack_id', '=', ws.id),
            ('status', 'in', ('Wait', 'Process'))]).write({'status': 'Success'})
        db_cmd = self.env['hr.rfid.command'].sudo().with_context(
            ws_no_publish=True).create({
                'webstack_id': ws.id, 'controller_id': ctrl.id,
                'cmd': 'DB', 'cmd_data': '400300', 'status': 'Wait'})
        self.assertEqual(db_cmd.status, 'Wait')
        # the hello reported fw 2.01 -> the webstack is new_fw, whose time
        # format is MM.DD.YY (test_date_10_3 is the legacy DD.MM.YY form); the
        # event date must match or the parse raises BadTime and the piggyback
        # never runs.
        ev = self._event_dict(ctrl_id=5, bos=3, event_n=3)
        ev['date'] = '%02d.%02d.%02d' % (
            self.test_now.month, self.test_now.day, self.test_now.year - 2000)
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self._dispatch(self._msg('ev', bid=401, ev=[ev]))
        payload = [c for c in sendone.call_args_list
                   if c.args[1] == 'hr_rfid.ev_ack'][-1].args[2]
        self.assertIn('cmd', payload,
                      'the queued command rides inline in the ev_ack (SPEC §6.3)')
        self.assertEqual(payload['cmd']['cmd']['id'], 5,
                         'the inline command targets this controller')
        self.assertEqual(payload['cmd']['cmd']['c'], 'DB')
        self.assertEqual(payload['cmd']['cid'], db_cmd.id,
                         'inline command carries its exact correlation id')

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
