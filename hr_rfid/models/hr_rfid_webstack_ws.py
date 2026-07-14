# -*- coding: utf-8 -*-
"""WebSocket (Odoo bus) transport layer of ``hr.rfid.webstack``.

Package A of the Odoo Bus real-time channel - see
``docs/odoo-bus/ODOO_BUS_ODOO_PLAN.md`` (esp32 repo) for the task and
``docs/odoo-bus/ODOO_BUS_PROTOCOL_SPEC.md`` for the wire contract (SSOT).

The module (iCON1XX 100.1) subscribes to ONE string channel per device:
``hr_rfid#<serial>#<key>`` (WIRE CONTRACT v3, proto 3, owner 2026-07-14). The
credential is the module ``key`` (``server_push_key``) - the SAME secret the
classic HTTP heartbeat authenticates with (``_authenticate_webstack``); the
device already holds it and never receives it from Odoo. proto 3 REMOVED the
separate 128-bit ``ws_token`` (it duplicated the key). The channel binds the
socket to the webstack at connect; the hello proves firmware authenticity with
an HMAC over ``s|k|n`` (``FW_SECRET``), so guessing the short key alone does
not let a network attacker drive a controller. The classic HTTP channel runs
over TLS in production (owner: HTTPS), so the key is not exposed on the wire -
the same trust model the HTTP POST always used.

Every server->device publish goes through :meth:`_ws_send` - the channel
naming lives in exactly one place. Key rotation is TOFU (SPEC §6.6): an admin
clears the stored ``key`` in Odoo and the next hello's ``k`` is adopted; there
is no server-issued token to rotate and no grace window.
"""
import hashlib
import hmac
import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.http import request
from odoo.tools import consteq
from odoo.addons.bus.websocket import CloseCode, _websocket_instances

from odoo.addons.hr_rfid.models.hr_rfid_webstack import BadTimeException

_logger = logging.getLogger(__name__)

# Wire-contract constants (docs/odoo-bus/ODOO_BUS_PROTOCOL_SPEC.md)
# proto 3 (owner 2026-07-14) = the secure hello WITHOUT ws_token: the channel
# credential IS the module `key` (`k` in every frame), and the hello proves
# firmware authenticity with an HMAC (`auth`) over `s|k|n` plus an anti-replay
# counter (`n`). The signature is checked ONCE at connect (hello), not per
# message. proto 2 (separate ws_token) is retired - its channel no longer
# exists, so an un-migrated device falls back to HTTP (auto-provision) rather
# than being half-served on a dead channel.
WS_PROTO_VERSION = 3
WS_PROTO_SUPPORTED = (3,)
# HMAC secret shared with the firmware build (out-of-band; NOT in any spec).
# Missing parameter = the authenticity check is skipped with a loud WARNING
# (resilience over fleet lockout at a forgotten deploy step).
WS_FW_SECRET_PARAM = 'hr_rfid.ws_fw_secret'
# Default heartbeat interval the server advertises in hello_ack (SPEC §6.1);
# tunable per install via the system parameter below.
WS_HB_INTERVAL_DEFAULT_S = 60
WS_HB_INTERVAL_PARAM = 'hr_rfid.ws_hb_interval'
# hello_ack settings advertised to the device (SPEC §6.1)
WS_ACK_TIMEOUT_S = 10
WS_EV_BATCH_MAX = 20
WS_RL = {'rate': 5, 'burst': 8}
# Anti-flood on invalid tokens (SPEC §9.2): after this many failures within
# the window, ONE system event is raised for the operator.
WS_AUTH_FAIL_THRESHOLD = 5
WS_AUTH_FAIL_WINDOW_S = 60
# Controllers sit on the RS-485 bus at addresses 1..254 (0 = broadcast / no
# controller). An event with an id outside this range is malformed and must
# not create a controller (bounds the tables an authenticated device grows).
WS_CTRL_ID_MIN = 1
WS_CTRL_ID_MAX = 254


class HrRfidWebstackWs(models.Model):
    _inherit = 'hr.rfid.webstack'

    ws_enabled = fields.Boolean(
        string='Real-time Channel',
        help='Enable the permanent real-time connection for this module. '
             'Commands reach the module within seconds instead of waiting '
             'for its next check-in. The module keeps working the classic '
             'way whenever the real-time connection is not available.',
        default=False,
        tracking=True,
    )
    ws_proto = fields.Integer(
        string='Protocol Version',
        readonly=True,
        copy=False,
        help='Real-time protocol version the module negotiated on its last '
             'connection.',
    )
    ws_last_seen = fields.Datetime(
        string='Last Real-time Activity',
        readonly=True,
        copy=False,
        help='Last time the module sent anything over the real-time '
             'connection.',
    )
    ws_online = fields.Boolean(
        string='Real-time Online',
        compute='_compute_ws_online',
        search='_search_ws_online',
        help='The module is currently connected in real time (it reported '
             'activity within the last two heartbeat intervals).',
    )
    ws_provision_pending = fields.Boolean(
        string='Settings Pending Delivery',
        copy=False,
        help='The real-time settings changed and will be delivered to the '
             'module on its next check-in.',
    )
    ws_auth_fail_count = fields.Integer(copy=False)
    ws_auth_fail_since = fields.Datetime(copy=False)
    # Anti-replay watermark for the secure hello: the highest `n`
    # (boot_count*65536 + seq) this module has proven; a hello with
    # n <= ws_last_n is a replay and is refused. int4 ceiling note: the
    # counter overflows Odoo's Integer only after ~32k device boots
    # (INTEROP 2026-07-13) - acceptable; revisit before a production fleet.
    ws_last_n = fields.Integer(copy=False, default=0)

    # ------------------------------------------------------------------
    # Presence
    # ------------------------------------------------------------------

    @api.model
    def _ws_hb_interval(self):
        """Heartbeat interval (seconds) advertised to devices (SPEC §6.1)."""
        param = self.env['ir.config_parameter'].sudo().get_param(
            WS_HB_INTERVAL_PARAM, WS_HB_INTERVAL_DEFAULT_S)
        try:
            return max(10, int(param))
        except (TypeError, ValueError):
            return WS_HB_INTERVAL_DEFAULT_S

    def _ws_online_threshold(self):
        """A device is online if seen within 2 heartbeat intervals
        (ARCHITECTURE §5.2 presence model - timestamp based, no connection
        tracking)."""
        return fields.Datetime.now() - timedelta(seconds=2 * self._ws_hb_interval())

    @api.depends('ws_enabled', 'ws_last_seen')
    def _compute_ws_online(self):
        threshold = self._ws_online_threshold()
        for rec in self:
            rec.ws_online = bool(
                rec.ws_enabled and rec.ws_last_seen and rec.ws_last_seen >= threshold)

    def _search_ws_online(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return NotImplemented
        online = (operator == '=') == value
        threshold = self._ws_online_threshold()
        if online:
            return ['&', ('ws_enabled', '=', True), ('ws_last_seen', '>=', threshold)]
        return ['|', ('ws_enabled', '=', False), '|',
                ('ws_last_seen', '=', False), ('ws_last_seen', '<', threshold)]

    def _ws_touch(self):
        """Record upstream activity (any device message updates presence)."""
        self.sudo().write({'ws_last_seen': fields.Datetime.now()})

    # ------------------------------------------------------------------
    # Token lifecycle
    # ------------------------------------------------------------------

    def action_ws_enable(self):
        """Enable the real-time channel.

        proto 3 has no server-issued token: the channel credential is the
        module ``key`` the device already holds, so there is no secret to mint
        here. A module with no key yet (never contacted us) adopts its key on
        the first authenticated hello (TOFU, :meth:`_ws_check_hello`).
        """
        for rec in self:
            rec.sudo().write({'ws_enabled': True, 'ws_provision_pending': True})
            rec.message_post(body=_('Real-time channel enabled.'))
        return True

    def action_ws_disable(self):
        for rec in self:
            # The bye must go out while the channel is still enabled
            # (_ws_send refuses on a disabled record). It tells a connected
            # device to close + park on HTTP (contract v1.1, OD-Q4-c); the
            # kick below covers devices that predate the bye handler.
            rec._ws_send('hr_rfid.bye', {'reason': 'disabled'})
            rec.sudo().write({'ws_enabled': False, 'ws_provision_pending': True})
            rec.message_post(body=_('Real-time channel disabled.'))
        self._ws_kick()
        return True

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
                rec._ws_send('hr_rfid.bye', {'reason': 'deleted'})
            except Exception:
                _logger.warning('WS: could not send bye to module %s on '
                                'unlink', rec.serial, exc_info=True)
        self._ws_kick()
        return super().unlink()

    def action_ws_rekey(self):
        """Re-key the real-time channel by TOFU (SPEC §6.6, owner 2026-07-14).

        proto 3 has no server-issued token to rotate: the credential is the
        module ``key`` the device owns. To accept a NEW key (e.g. after the
        key was changed on the device), clear the stored key here - the next
        authenticated hello then presents the device's current ``k`` and Odoo
        adopts it (:meth:`_ws_check_hello`). If the device is still online with
        the OLD key, its next hello simply re-adopts that same key (a no-op),
        so re-keying only takes effect once the device actually presents a
        different key - exactly the intended trust-on-first-use behaviour.
        """
        for rec in self:
            rec.sudo().write({'key': False, 'ws_provision_pending': True})
            rec.message_post(body=_(
                'Real-time channel re-key armed: the next module check-in '
                'sets the new key.'))
        return True

    # ------------------------------------------------------------------
    # Publish helper - the ONLY place that knows the channel name
    # ------------------------------------------------------------------

    def _ws_channel(self):
        """The device's bus channel: ``hr_rfid#<serial>#<key>`` (proto 3).

        The credential in the channel name is the module ``key`` - the same
        secret the device presents in every frame's ``k`` and in the HTTP
        heartbeat. Lives in exactly ONE place so the naming never drifts.
        """
        self.ensure_one()
        rec = self.sudo()
        return 'hr_rfid#%s#%s' % (rec.serial, rec.key or '')

    def _ws_send(self, mtype, payload):
        """Publish ``mtype``/``payload`` on this device's bus channel.

        Returns True when a publish happened. sudo() is deliberate and narrow:
        reading the group-protected key to build the channel name is a system
        operation performed on behalf of whatever flow produced the message
        (command queue, ack path); the payload itself never contains the key.
        """
        self.ensure_one()
        rec = self.sudo()
        if not (rec.ws_enabled and rec.key):
            return False
        # bus.bus._sendone defers the row insert to a precommit callback that
        # always runs sudo().create(); no create right is needed here, so no
        # sudo on the call itself.
        self.env['bus.bus']._sendone(self._ws_channel(), mtype, payload)
        return True

    # ------------------------------------------------------------------
    # Inbound dispatch (device -> Odoo over the websocket)
    # ------------------------------------------------------------------

    @api.model
    def _ws_dispatch(self, data):
        """Entry point for device websocket messages (SPEC §4.1).

        Called by the ``ir.websocket`` extension for every
        ``{"event_name": "hr_rfid", "data": {...}}`` frame. Every message
        carries the channel token and is re-authenticated with a
        constant-time compare - the connection itself is anonymous
        (public user), the token IS the device identity.
        """
        if not isinstance(data, dict):
            return
        serial, k, mtype = data.get('s'), data.get('k'), data.get('t')
        if not (serial and k and isinstance(mtype, str)):
            _logger.debug('WS: malformed frame (missing s/k/t): %r', data)
            return
        webstack = self.sudo().with_context(active_test=False).search(
            [('serial', '=', str(serial))], limit=1)
        # proto 3 auth: the channel credential is the module `key` (`k`). Every
        # frame must key-match the stored key, EXCEPT a hello from a keyless
        # module (never-contacted or re-keyed) - a TOFU candidate whose key is
        # adopted inside _ws_check_hello, but ONLY after the firmware HMAC over
        # s|k|n verifies (so a network peer cannot seed a key without FW_SECRET).
        key_ok = (webstack and webstack.key
                  and consteq(webstack.key.upper(), str(k).upper()))
        tofu_hello = bool(mtype == 'hello' and webstack and not webstack.key)
        if (not webstack or not webstack.active or not webstack.ws_enabled
                or not (key_ok or tofu_hello)):
            self._ws_auth_failed(webstack, mtype)
            if mtype == 'hello':
                self._ws_nack_hello(serial, k, webstack)
            return
        webstack._ws_touch()
        proto = data.get('v')
        if proto not in WS_PROTO_SUPPORTED:
            # Unsupported protocol: answer only a hello (SPEC §9.2), drop
            # anything else silently.
            if mtype == 'hello':
                webstack._ws_send('hr_rfid.hello_ack', {
                    'ok': False, 'err': 'proto', 'proto': WS_PROTO_VERSION})
            return
        if mtype == 'hello' and not webstack._ws_check_hello(data):
            # The secure-hello identity (firmware HMAC + counter, + key adoption
            # on TOFU) did not hold - same refusal shape as a bad key (OD-Q4-b).
            self._ws_auth_failed(webstack, mtype)
            self._ws_nack_hello(serial, k, webstack)
            return
        handler = self._ws_handlers(webstack).get(mtype)
        if handler is None:
            _logger.debug('WS: unknown message type %r from %s', mtype, serial)
            return
        # Isolate the transport from malformed device input. A parse error in
        # a handler (e.g. a missing key in an ``rsp`` payload reaching
        # parse_response) must NOT escape to the bus frame loop: there it
        # would close the socket with 1011 SERVER_ERROR and log a full
        # traceback, letting a device with a valid token churn connections
        # and flood the ERROR log. Mirror the HTTP twin
        # (controllers/main.py::post_event): roll the partial work back in a
        # savepoint, log a warning, record a system event. SPEC §9.2.
        try:
            with self.env.cr.savepoint():
                handler(data)
        except Exception:
            _logger.warning(
                'WS: handler %r from module %s failed to process',
                mtype, serial, exc_info=True)
            self._ws_report_sys_ev(
                webstack, 'Real-time message could not be processed',
                {'t': mtype})

    @api.model
    def _ws_handlers(self, webstack):
        """Message-type -> bound-handler map for inbound device messages.

        Extension seam: inheritor modules (e.g. the IoT tunnel drivers) add
        their own message types by overriding this with super() and updating
        the returned dict, so they never re-implement the auth/isolation
        wrapper around dispatch (SPEC §4.1).
        """
        return {
            'hello': webstack._ws_on_hello,
            'hb': webstack._ws_on_hb,
            'ev': webstack._ws_on_event_batch,
            'rsp': webstack._ws_on_cmd_response,
        }

    def _ws_check_hello(self, data):
        """Secure-hello identity for proto 3 (SPEC §5.1, owner 2026-07-14).

        The channel credential ``k`` IS the module key (``server_push_key``) -
        there is no separate ``key`` field and no ws_token. The hello proves:

        - ``auth`` - firmware authenticity:
          ``lowercase_hex(HMAC_SHA256(FW_SECRET, s|k|n))`` over the wire values
          verbatim (``k`` is the key). Binds the connection to a genuine
          firmware build: a peer that guessed the short key still cannot forge
          ``auth`` without FW_SECRET.
        - ``n`` - strictly monotonic anti-replay counter
          (boot_count*65536 + seq); anything <= the stored watermark is a replay.

        TOFU key adoption: a module with no stored key (never contacted us, or
        re-keyed via :meth:`action_ws_rekey`) that presents an HMAC-verified
        hello has its ``k`` ADOPTED as the module key. This is the ONLY way a
        keyless module comes online, and it is gated by the HMAC, so it is not
        a network-triggerable key seed.

        Returns True when the hello is authentic. A missing FW_SECRET parameter
        skips only the HMAC with a loud WARNING (resilience over fleet lockout);
        adoption is then NOT performed - a keyless module cannot pass without a
        proof to trust.
        """
        self.ensure_one()
        rec = self.sudo()
        wire_s = str(data.get('s'))
        wire_k = str(data.get('k'))
        secret = self.env['ir.config_parameter'].sudo().get_param(
            WS_FW_SECRET_PARAM)
        if not secret:
            _logger.warning(
                'WS: %s is not set - accepting hello from %s WITHOUT the '
                'firmware authenticity check. Set the parameter in '
                'production.', WS_FW_SECRET_PARAM, rec.serial)
            # No proof: an already-keyed module passes (its key matched in the
            # dispatcher); a keyless module cannot be adopted without a proof.
            return bool(rec.key)
        try:
            n = int(data.get('n'))
        except (TypeError, ValueError):
            _logger.info('WS: hello from %s with a malformed counter %r',
                         rec.serial, data.get('n'))
            return False
        if n <= rec.ws_last_n:
            _logger.info('WS: hello replay from %s (n=%s <= last %s)',
                         rec.serial, n, rec.ws_last_n)
            return False
        expected = hmac.new(
            secret.encode(),
            ('%s|%s|%s' % (wire_s, wire_k, n)).encode(),
            hashlib.sha256).hexdigest()
        auth = data.get('auth')
        if not (auth and hmac.compare_digest(expected, str(auth).lower())):
            _logger.info('WS: firmware authenticity check did not pass for '
                         'hello from %s', rec.serial)
            return False
        if not rec.key:
            # TOFU: adopt the HMAC-proven key for a keyless / re-keyed module.
            rec.key = wire_k
            _logger.info('WS: adopted key for module %s on an authenticated '
                         'hello (TOFU re-key)', rec.serial)
        rec.ws_last_n = n
        return True

    @api.model
    def _ws_nack_hello(self, serial, k, webstack):
        """Explicit auth refusal for a hello - and ONLY a hello (contract
        v1.1, INTEROP OD-Q4-b 2026-07-13). Without it a refused device sits
        deaf-mute on a live socket (its messages silently dropped, transport
        PING/PONG keeps it alive) and never falls back to HTTP. The nack
        goes to the CLAIMED channel (serial+key exactly as presented) - the
        only channel the refused peer is subscribed to.

        Rate limit: known serial -> only while the auth-fail window counter
        is below the threshold (shares :meth:`_ws_auth_failed`'s window);
        unknown serial (e.g. a deleted module) -> every hello, because a
        hello costs the sender a full TCP+websocket upgrade per attempt, so
        flooding is bounded at the connection level, not per message.
        """
        if webstack and webstack.sudo().ws_auth_fail_count >= WS_AUTH_FAIL_THRESHOLD:
            return
        self.env['bus.bus']._sendone(
            'hr_rfid#%s#%s' % (serial, k), 'hr_rfid.hello_ack',
            {'ok': False, 'err': 'auth', 'proto': WS_PROTO_VERSION})

    @api.model
    def _ws_report_sys_ev(self, webstack, description, post_data):
        """``report_sys_ev`` that never raises into the caller - the websocket
        paths must stay isolated even from a logging failure."""
        try:
            webstack.report_sys_ev(description, post_data=post_data)
        except Exception:
            _logger.exception('WS: could not record system event: %s', description)

    @api.model
    def _ws_auth_failed(self, webstack, mtype):
        """Count invalid-token messages; raise ONE system event at the
        threshold (SPEC §9.2 anti-flood - never a system event per message)."""
        if not webstack:
            _logger.debug('WS: message for unknown module (type %r)', mtype)
            return
        rec = webstack.sudo()
        now = fields.Datetime.now()
        window_start = now - timedelta(seconds=WS_AUTH_FAIL_WINDOW_S)
        if not rec.ws_auth_fail_since or rec.ws_auth_fail_since < window_start:
            rec.write({'ws_auth_fail_count': 1, 'ws_auth_fail_since': now})
            return
        # Bound the pre-auth writes. The serial is enumerable (not secret), so
        # an attacker who guessed a valid one could otherwise force one UPDATE
        # on that row for EVERY frame. Once the window's single system event
        # has fired, stop counting: writes are capped at THRESHOLD per window
        # per serial (a per-IP connection cap on /websocket is a deployment
        # requirement - nginx limit_conn/limit_req; see ODOO_PLAN §8).
        if rec.ws_auth_fail_count >= WS_AUTH_FAIL_THRESHOLD:
            return
        rec.ws_auth_fail_count += 1
        if rec.ws_auth_fail_count == WS_AUTH_FAIL_THRESHOLD:
            rec.report_sys_ev(
                'Real-time messages with an invalid channel key '
                '(%d in the last minute)' % rec.ws_auth_fail_count,
                post_data={'t': mtype})

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

    def _ws_on_hello(self, data):
        self.ensure_one()
        rec = self.sudo()
        if data.get('fw'):
            rec.version = str(data['fw'])[:6]
        if data.get('hw'):
            # The hello carries the hardware model (e.g. "100.1") - for an
            # auto-registered module this is the ONLY source: the classic
            # writer is the UDP discovery flow, which never ran for it, and
            # the HTTP heartbeat does not carry the hardware version at all.
            rec.hw_version = str(data['hw'])[:6]
        rec.ws_proto = data.get('v') or WS_PROTO_VERSION
        rec._provision_detected_controllers(data.get('ctrl'))
        rec.ws_provision_pending = False
        self._ws_on_connect_sync()
        self._ws_send('hr_rfid.hello_ack', {
            'ok': True,
            'proto': WS_PROTO_VERSION,
            'srv_ts': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hb_interval': self._ws_hb_interval(),
            'ack_timeout': WS_ACK_TIMEOUT_S,
            'ev_batch': WS_EV_BATCH_MAX,
            'rl': dict(WS_RL),
            'err': None,
        })

    def _ws_on_hb(self, data):
        self.ensure_one()
        # Presence is already updated by the dispatcher; mirror the HTTP
        # heartbeat's controller pre-provisioning (commands do NOT piggyback
        # here - over WS they travel as their own publishes).
        self.sudo()._provision_detected_controllers(data.get('ctrl'))

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
