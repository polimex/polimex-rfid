# -*- coding: utf-8 -*-
"""WebSocket (Odoo bus) transport layer of ``hr.rfid.webstack`` - the Access
Control host for the shared secure-WS transport base.

The transport-generic half (the anonymous ``/websocket`` dispatch, the secure
hello with firmware HMAC + anti-replay + TOFU key adoption, per-frame key auth,
presence, the channel lifecycle and the single bus-publish helper) lives ONCE in
``polimex.ws.mixin`` (module ``polimex_ws`` - a neutral shared base, NOT the IoT
app). This file keeps the Access-Control domain layer:

* one-command-in-flight delivery over the socket (``_ws_publish_command`` /
  ``_ws_on_connect_sync`` / ``_ws_publish_next_command``),
* the ``ev`` event-batch consume + ack path (mirrors the HTTP twin),
* the ``rsp`` command-response path,
* HTTP-piggyback provisioning (``_ws_provision_payload``),
* the server-side socket kick on disable/unlink,

plus the small branch hooks the base calls (channel prefix, handler map, hello
capture + command sync, hello_ack ev_batch, system-event sink = the AC
``event.system``, disable = bye + kick).

Wire contract (SSOT): ``docs/odoo-bus/ODOO_BUS_PROTOCOL_SPEC.md`` (proto 3). The
device subscribes to ``hr_rfid#<serial>#<key>``; the credential is the module
``key`` (``server_push_key``). Key rotation is TOFU (SPEC §6.6). hr_rfid and
polimex_iot both depend on ``polimex_ws`` but never on each other.
"""
import logging

from odoo import fields, models
from odoo.addons.bus.websocket import CloseCode, _websocket_instances

from odoo.addons.hr_rfid.models.hr_rfid_webstack import BadTimeException
# The shared secure-WS transport constants live in the neutral polimex_ws base;
# imported here (and thus re-exported from this module's namespace) so the
# existing test imports (tests/test_ws_dispatch.py, tests/test_ws_layer.py) keep
# resolving after the extraction.
from odoo.addons.polimex_ws.models.ws_mixin import (  # noqa: F401  (re-export)
    BYE,
    WS_AUTH_FAIL_THRESHOLD,
    WS_PROTO_VERSION,
)

_logger = logging.getLogger(__name__)

# AC-specific wire constants (the shared ones live in polimex_ws).
# hello_ack advertises the max event-batch size the device may pack.
WS_EV_BATCH_MAX = 20
# Controllers sit on the RS-485 bus at addresses 1..254 (0 = broadcast / no
# controller). An event with an id outside this range is malformed and must
# not create a controller (bounds the tables an authenticated device grows).
WS_CTRL_ID_MIN = 1
WS_CTRL_ID_MAX = 254


class HrRfidWebstackWs(models.Model):
    # Extend hr.rfid.webstack IN PLACE, mix in polimex.ws.mixin (the shared
    # transport/auth methods) and DELEGATE the credential/presence to the shared
    # per-serial polimex.ws.endpoint. The explicit _name equal to the extended
    # model is REQUIRED with a list _inherit (otherwise Odoo creates a NEW model
    # instead of extending the webstack).
    _name = 'hr.rfid.webstack'
    _inherit = ['hr.rfid.webstack', 'polimex.ws.mixin']
    # key + ws_enabled/ws_proto/ws_last_seen/ws_online/ws_provision_pending/
    # ws_auth_fail_*/ws_last_n now live ONCE on polimex.ws.endpoint (per serial);
    # the module reads/writes them transparently (webstack.key, .ws_online, ...)
    # but a device that is both a module and an IoT gateway shares ONE row - the
    # double-key fix. The get-or-create-by-serial wiring is in polimex.ws.mixin's
    # create/write overrides. The module keeps its own serial (its identity).
    _inherits = {'polimex.ws.endpoint': 'endpoint_id'}
    endpoint_id = fields.Many2one(
        'polimex.ws.endpoint', string='Real-time endpoint',
        required=True, ondelete='restrict', index=True, copy=False)

    # ------------------------------------------------------------------
    # polimex.ws.mixin hooks - the Access-Control branch specifics.
    # ------------------------------------------------------------------
    def _ws_channel_prefix(self):
        return 'hr_rfid'

    def _ws_handlers(self):
        """Shared hello/hb (base) + the AC event-batch and command-response
        frames. Extension seam for inheritors (e.g. vending) via super()."""
        handlers = super()._ws_handlers()
        handlers.update({
            'ev': self._ws_on_event_batch,
            'rsp': self._ws_on_cmd_response,
        })
        return handlers

    def _ws_on_hello_extra(self, data):
        """AC captures the controllers the device pre-provisions on hello."""
        self._provision_detected_controllers(data.get('ctrl'))

    def _ws_after_hello(self):
        """(Re)start command delivery on (re)connect - ONE command in flight
        (sync-on-connect, ARCHITECTURE §3.2)."""
        self._ws_on_connect_sync()

    def _ws_hello_ack_extra(self):
        """The device may pack up to WS_EV_BATCH_MAX events per ev frame."""
        return {'ev_batch': WS_EV_BATCH_MAX}

    def _ws_on_hb_extra(self, data):
        """Mirror the HTTP heartbeat's controller pre-provisioning (commands do
        NOT piggyback here - over WS they travel as their own publishes)."""
        self._provision_detected_controllers(data.get('ctrl'))

    def _ws_sys_ev_record(self, description, post_data):
        """AC's diagnostic sink is its ``event.system`` log (not the chatter)."""
        self.report_sys_ev(description, post_data=post_data)

    def _ws_auth_fail_notify(self, count, mtype):
        """Raise ONE system event when the auth-fail threshold is hit."""
        self.report_sys_ev(
            'Real-time messages with an invalid channel key '
            '(%d in the last minute)' % count,
            post_data={'t': mtype})

    def _ws_before_disable(self):
        """The bye must go out while the channel is still enabled (_ws_send
        refuses on a disabled record). It tells a connected device to close +
        park on HTTP (contract v1.1, OD-Q4-c); the kick in _ws_after_disable
        covers devices that predate the bye handler."""
        self._ws_send(BYE, {'reason': 'disabled'})

    def _ws_after_disable(self):
        self._ws_kick()

    # ------------------------------------------------------------------
    # Socket kick + unlink (AC-specific - reaches live sockets of this process)
    # ------------------------------------------------------------------
    def _ws_kick(self):
        """Actively close this module's open websocket(s) server-side.

        Without the kick a connected device stays DEAF-MUTE after a disable
        or an unlink: its per-message auth fails silently (SPEC §9.2
        anti-flood - no nack), the transport PING/PONG keeps the socket
        alive, so it never falls back to HTTP and never re-provisions
        (live bench finding, INTEROP 2026-07-13). Closing the socket makes
        the device fall back to Mode::HTTP within its hello/ack timeout,
        where the classic flow (auto-register / ``result.ws``) takes over.

        Matches connections by the channel prefix ``hr_rfid#<serial>#`` so
        it works with any token generation (incl. the rotation grace pair).
        NOTE: reaches only sockets of THIS process - correct for the
        threaded server (workers=0); on a prefork/gevent deploy the kick
        must additionally travel via the bus (SPEC follow-up, OD-Q3).
        """
        for rec in self:
            prefix = 'hr_rfid#%s#' % rec.serial
            for ws in list(_websocket_instances):
                try:
                    channels = getattr(ws, '_channels', None) or ()
                    if any(isinstance(ch, tuple) and ch
                           and isinstance(ch[-1], str)
                           and ch[-1].startswith(prefix)
                           for ch in channels):
                        ws._disconnect(CloseCode.CLEAN)
                        _logger.info(
                            'WS: kicked live socket of module %s '
                            '(channel prefix match)', rec.serial)
                except Exception:
                    _logger.warning(
                        'WS: could not kick a socket of module %s',
                        rec.serial, exc_info=True)

    def unlink(self):
        # A deleted module must not keep a live real-time socket. Send the
        # bye (device closes + parks on HTTP, contract v1.1 OD-Q4-c), then
        # kick - both BEFORE the record (and its serial/token) disappears.
        # The kick covers devices that predate the bye handler.
        for rec in self:
            try:
                rec._ws_send(BYE, {'reason': 'deleted'})
            except Exception:
                _logger.warning('WS: could not send bye to module %s on '
                                'unlink', rec.serial, exc_info=True)
        self._ws_kick()
        return super().unlink()

    # -- provisioning over the classic HTTP channel (SPEC §10) ----------

    def _ws_provision_payload(self, result):
        """Attach the real-time provisioning block to an HTTP reply.

        Delivered piggyback on the existing device check-in (heartbeat /
        event / response reply) whenever the settings changed - the device
        stores them and (re)starts its websocket state machine. The legacy
        (10.3) reply encoder strips unknown keys, so only JSON-RPC (ESP32)
        modules ever see the block.

        proto 3: the block carries NO secret. The channel credential is the
        module ``key`` the device already owns (and presents as ``k``), so
        Odoo never sends a token down - it only tells the device where to
        connect (``url``/``db``) and whether the channel is on (``en``).
        """
        self.ensure_one()
        rec = self.sudo()
        if not isinstance(result, dict) or not rec.ws_provision_pending:
            return result
        icp = self.env['ir.config_parameter'].sudo()
        base_url = icp.get_param('hr_rfid.ws_base_url') or icp.get_param(
            'web.base.url')
        result = dict(result)
        result['ws'] = {
            'en': 1 if rec.ws_enabled else 0,
            'url': base_url,
            'db': self.env.cr.dbname,
            'proto': WS_PROTO_VERSION,
        }
        return result

    # -- commands ------------------------------------------------------

    def _ws_publish_command(self, command):
        """Publish one queued command on the device channel (SPEC §6.2).

        Reuses ``send_command()`` - the SAME wire-payload builder the HTTP
        delivery uses (D1/D7/DB specials included), so both transports carry
        byte-identical commands; it also flips the command to Process and
        records the request, exactly like an HTTP delivery does.
        """
        self.ensure_one()
        json_cmd = command.sudo().send_command(200)
        return self._ws_send('hr_rfid.cmd', {
            'cid': command.id,
            'cmd': json_cmd['cmd'],
            'ts': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })

    def _ws_publish_next_command(self):
        """One-command-in-flight chain: once a response closes the command
        in flight, push the OLDEST queued one over the socket. Never more
        than one outstanding command per module (owner rule; the device
        stages at most 4 - overflow answers ``e=24`` NO_QUADRANT, INTEROP
        2026-07-13). Best-effort transport, like every publish: on failure
        the command stays Wait for the republish cron / next connect."""
        self.ensure_one()
        rec = self.sudo()
        if not (rec.ws_enabled and rec.ws_online):
            return
        if rec.in_cmd_execution():
            return  # a command is still in flight - its rsp will chain us
        command = self.env['hr.rfid.command'].sudo().search([
            ('webstack_id', '=', rec.id),
            ('status', '=', 'Wait'),
        ], order='id', limit=1)
        if not command:
            return
        try:
            with self.env.cr.savepoint():
                rec._ws_publish_command(command)
        except Exception:
            _logger.warning(
                'WS: could not publish next command %s (%s) to module %s; '
                'it stays queued.', command.id, command.cmd, rec.serial,
                exc_info=True)

    # -- handlers ------------------------------------------------------

    def _ws_on_connect_sync(self):
        """(Re)start command delivery on device (re)connect - ONE command
        in flight (sync-on-connect, ARCHITECTURE §3.2). The device stages
        at most 4 commands (the ~9-command burst on the first bench connect
        overflowed it: instant ``e=24`` NO_QUADRANT for the tail - INTEROP
        2026-07-13), so on hello we push only the OLDEST pending command;
        each response then chains the next one (``_ws_on_cmd_response`` ->
        ``_ws_publish_next_command``). Idempotent: the device deduplicates
        by ``cid``, so a command already delivered over a previous
        connection is acknowledged, not re-executed."""
        self.ensure_one()
        commands = self.env['hr.rfid.command'].sudo().search([
            ('webstack_id', '=', self.id),
            ('status', 'in', ('Wait', 'Process')),
        ], order='id', limit=1)
        for command in commands:
            # Per-command savepoint: one command with corrupt data (send_command
            # can raise on e.g. an empty pin/rights field) must not abort the
            # whole hello - that would roll back hello_ack and loop the device
            # (F4). It also keeps the publish and its status flip atomic per
            # command: _ws_publish_command sends first and publishes last, so a
            # failure never leaves an orphan hr_rfid.cmd on the wire whose DB
            # flip was rolled back (F12).
            try:
                with self.env.cr.savepoint():
                    self._ws_publish_command(command)
            except Exception:
                _logger.warning(
                    'WS: could not publish command %s (%s) to module %s on '
                    'connect', command.id, command.cmd, self.serial,
                    exc_info=True)

    def _ws_on_event_batch(self, data):
        """Process an ``ev`` batch (SPEC §5.3) and acknowledge it (§6.3).

        Consume semantics MIRROR the HTTP path: the parse core answers with
        a status dict, and only status 200 means "processed" - e.g. an event
        from a brand-new controller answers 400 + the F0 setup command, and
        the event must stay in the controller FIFO for a later re-send.

        - ``ok:true``  -> processed (or already processed: ``dup:true``);
          the device consumes the event (0xDA).
        - ``ok:false`` -> NOT consumed; the device re-sends it later
          (after the inline setup command, after the error clears).

        The dedup table is written only for successfully processed events;
        each event runs in its own savepoint so one poisoned entry never
        breaks the batch.
        """
        self.ensure_one()
        bid = data.get('bid')
        events = data.get('ev')
        if bid is None or not isinstance(events, list):
            return
        rec = self.sudo()
        Dedup = self.env['hr.rfid.ws.dedup']
        Command = self.env['hr.rfid.command'].sudo()
        results = []
        inline_cmd = None
        for i, event in enumerate(events[:WS_EV_BATCH_MAX]):
            entry = {'i': i, 'ok': False, 'dup': False}
            # Validate the controller id BEFORE any DB work: a non-dict entry,
            # an unparseable id, or an id outside the RS-485 range is malformed
            # and final - consume it (ok:true, so a real device does not loop
            # re-sending) but never let it reach the create path.
            ctrl_num = -1
            if isinstance(event, dict):
                try:
                    ctrl_num = int(event.get('id') or 0)
                except (TypeError, ValueError):
                    ctrl_num = -1
            if not (WS_CTRL_ID_MIN <= ctrl_num <= WS_CTRL_ID_MAX):
                _logger.warning(
                    'WS: dropping malformed event %s of batch %s from %s '
                    '(controller id %r)', i, bid, rec.serial,
                    event.get('id') if isinstance(event, dict) else event)
                # Do NOT put the raw entry under an 'event' key - report_sys_ev
                # special-cases that and tries to read a timestamp out of it,
                # which a non-dict/garbage entry does not have.
                self._ws_report_sys_ev(
                    rec, 'Real-time event dropped (bad controller id)',
                    {'bid': bid, 'bad_event': repr(event)[:200]})
                entry['ok'] = True   # final: consume, do not loop
                results.append(entry)
                continue
            try:
                with self.env.cr.savepoint():
                    ev_ts = '%s %s' % (event.get('date') or '', event.get('time') or '')
                    bos = int(event.get('bos') or 0)
                    if Dedup._seen(rec, ctrl_num, bos, ev_ts):
                        entry.update(ok=True, dup=True)
                        results.append(entry)
                        continue
                    # ws_skip_piggyback: run the queued-command piggyback for at
                    # most the FIRST event of the batch (once a command is
                    # captured, later events must not re-flip/retry it - F1).
                    result = rec.with_context(
                        ws_no_publish=True,
                        ws_skip_piggyback=inline_cmd is not None,
                    )._hw_parse_event({'convertor': rec.serial, 'event': event})
                    status = result.get('status') if isinstance(result, dict) else None
                    entry['ok'] = status == 200
                    if entry['ok']:
                        Dedup._claim(rec, ctrl_num, bos, ev_ts)
                    # An event may spawn an immediate command - the ev64
                    # cloud-permission reply (status 200) or the F0 setup of
                    # a new controller (status 400). Carry it inline in the
                    # ack so the controller timeout is honoured (SPEC §6.3).
                    # Correlate the cid to the EXACT command the wire payload
                    # describes (its target controller + command code), never
                    # a "newest Process" guess that could belong to another
                    # command (F2).
                    if (inline_cmd is None and isinstance(result, dict)
                            and result.get('cmd')):
                        wire = result['cmd']
                        cmd_rec = Command.search(
                            [('webstack_id', '=', rec.id),
                             ('controller_id.ctrl_id', '=', wire.get('id')),
                             ('cmd', '=like', (wire.get('c') or '_') + '%'),
                             ('status', '=', 'Process')],
                            order='id desc', limit=1)
                        inline_cmd = {'cid': cmd_rec.id or 0, 'cmd': wire}
            except BadTimeException:
                # Bad controller clock: the HTTP path answers 200 (accept +
                # system event) so the device does not loop - mirror it here,
                # otherwise a permanently-bad-time event re-sends forever.
                _logger.warning(
                    'WS: event %s of batch %s from %s has an invalid date/time',
                    i, bid, rec.serial)
                self._ws_report_sys_ev(
                    rec, 'Controller sent an invalid date or time',
                    {'bid': bid, 'event': event})
                entry['ok'] = True   # consume like HTTP status 200
            except Exception:
                # ok:false -> the device keeps the event and re-sends it
                # later; the failure is visible in the log and as a system
                # event. Same recovery shape as the HTTP path's 500.
                _logger.warning(
                    'WS: event %s of batch %s from %s failed to parse',
                    i, bid, rec.serial, exc_info=True)
                self._ws_report_sys_ev(
                    rec, 'Real-time event could not be processed',
                    {'bid': bid, 'event': event})
                entry['ok'] = False
            results.append(entry)
        ack = {'bid': bid, 'res': results}
        if inline_cmd:
            ack['cmd'] = inline_cmd
        self._ws_send('hr_rfid.ev_ack', ack)

    def _ws_on_cmd_response(self, data):
        """A command response over WS (SPEC §5.4) - same core as HTTP;
        ``direct_cmd=True`` stops the poll-era command piggyback (over WS
        commands travel as their own publishes). The ``cid`` correlation
        targets the exact command, so two identical queued commands can
        never swallow each other's response; an unusable cid falls back to
        the classic (controller, cmd) match."""
        self.ensure_one()
        response = data.get('r')
        if not isinstance(response, dict):
            return
        rec = self.sudo()
        command = None
        cid = data.get('cid')
        if isinstance(cid, int) and cid > 0:
            candidate = self.env['hr.rfid.command'].sudo().browse(cid).exists()
            # Accept the cid pre-match only if it is this webstack's, still in
            # flight, AND its command code matches the response - so a stale /
            # wrong cid cannot attach the answer to another command; otherwise
            # fall back to the classic (controller, cmd) match (F2).
            if (candidate and candidate.webstack_id == rec
                    and candidate.status == 'Process'
                    and candidate.cmd[:2] == str(response.get('c'))):
                command = candidate
        rec.parse_response(
            {'convertor': rec.serial, 'response': response},
            direct_cmd=True, command=command)
        # One-command-in-flight: this response freed the slot - deliver the
        # next queued command (if any) right away instead of waiting for a
        # poll / the republish cron.
        rec._ws_publish_next_command()
