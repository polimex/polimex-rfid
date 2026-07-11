# -*- coding: utf-8 -*-
"""WebSocket (Odoo bus) transport layer of ``hr.rfid.webstack``.

Package A of the Odoo Bus real-time channel - see
``docs/odoo-bus/ODOO_BUS_ODOO_PLAN.md`` (esp32 repo) for the task and
``docs/odoo-bus/ODOO_BUS_PROTOCOL_SPEC.md`` for the wire contract (SSOT).

The module (iCON1XX 100.1) subscribes to ONE unguessable string channel per
device: ``hr_rfid#<serial>#<ws_token>``. Security of a string bus channel IS
its unguessable name (``bus/models/bus.py`` ``_sendone`` docstring; in-tree
precedent: ``hr_rfid_vertical_elections`` ``display#{access_token}``), so the
token is a 128-bit secret, restricted to RFID officers at field level and
sent to the device only through the provisioning payload (SPEC §10).

Every server->device publish goes through :meth:`_ws_send` - the channel
naming lives in exactly one place. During a token rotation grace window the
publish is mirrored on the OLD channel so the device never misses a message
mid-switch (SPEC §6.6).
"""
import logging
import secrets
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.tools import consteq

_logger = logging.getLogger(__name__)

# Wire-contract constants (docs/odoo-bus/ODOO_BUS_PROTOCOL_SPEC.md)
WS_PROTO_VERSION = 1
# Token rotation: how long the old channel keeps receiving mirrored
# publishes after a rotation (SPEC §6.6 "grace_s").
WS_TOKEN_ROTATE_GRACE_S = 300
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
    ws_token = fields.Char(
        string='Channel Token',
        size=32,
        copy=False,
        groups='hr_rfid.hr_rfid_group_officer',
        help='Secret token of the real-time channel. It is generated '
             'automatically and delivered to the module on its next '
             'check-in. Use "Rotate token" if you suspect it leaked.',
    )
    ws_token_old = fields.Char(
        size=32,
        copy=False,
        groups='hr_rfid.hr_rfid_group_officer',
        help='Previous channel token, kept only during the short rotation '
             'grace window so the module never misses a message while '
             'switching channels.',
    )
    ws_token_rotated_at = fields.Datetime(
        readonly=True,
        copy=False,
        help='When the channel token was last rotated.',
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
        """Enable the real-time channel; generate the secret on first use."""
        for rec in self:
            rec_su = rec.sudo()
            if not rec_su.ws_token:
                rec_su.ws_token = secrets.token_hex(16)
            rec_su.write({'ws_enabled': True, 'ws_provision_pending': True})
            rec.message_post(body=_('Real-time channel enabled.'))
        return True

    def action_ws_disable(self):
        for rec in self:
            rec.sudo().write({'ws_enabled': False, 'ws_provision_pending': True})
            rec.message_post(body=_('Real-time channel disabled.'))
        return True

    def action_ws_rotate_token(self):
        """Issue a new channel token (SPEC §6.6).

        The rotation notice travels on the OLD channel; during the grace
        window :meth:`_ws_send` mirrors every publish on both channels, so a
        device that has not switched yet keeps receiving its messages.
        """
        for rec in self:
            rec_su = rec.sudo()
            if not (rec_su.ws_enabled and rec_su.ws_token):
                continue
            old_token = rec_su.ws_token
            rec_su.write({
                'ws_token_old': old_token,
                'ws_token_rotated_at': fields.Datetime.now(),
                'ws_token': secrets.token_hex(16),
                'ws_provision_pending': True,
            })
            self.env['bus.bus']._sendone(
                rec._ws_channel(token=old_token), 'hr_rfid.token', {
                    'new_token': rec_su.ws_token,
                    'grace_s': WS_TOKEN_ROTATE_GRACE_S,
                })
            rec.message_post(body=_('Real-time channel token rotated.'))
        return True

    # ------------------------------------------------------------------
    # Publish helper - the ONLY place that knows the channel name
    # ------------------------------------------------------------------

    def _ws_channel(self, token=None):
        self.ensure_one()
        rec = self.sudo()
        return 'hr_rfid#%s#%s' % (rec.serial, token or rec.ws_token)

    def _ws_grace_active(self):
        self.ensure_one()
        rec = self.sudo()
        return bool(
            rec.ws_token_old and rec.ws_token_rotated_at and
            fields.Datetime.now() < rec.ws_token_rotated_at
            + timedelta(seconds=WS_TOKEN_ROTATE_GRACE_S))

    def _ws_send(self, mtype, payload):
        """Publish ``mtype``/``payload`` on this device's bus channel.

        Returns True when a publish happened. sudo() is deliberate and
        narrow: reading the group-protected token to build the channel name
        is a system operation performed on behalf of whatever flow produced
        the message (command queue, ack path); the payload itself never
        contains the token.
        """
        self.ensure_one()
        rec = self.sudo()
        if not (rec.ws_enabled and rec.ws_token):
            return False
        bus = self.env['bus.bus'].sudo()
        bus._sendone(self._ws_channel(), mtype, payload)
        if self._ws_grace_active():
            bus._sendone(self._ws_channel(token=rec.ws_token_old), mtype, payload)
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
        serial, token, mtype = data.get('s'), data.get('k'), data.get('t')
        if not (serial and token and isinstance(mtype, str)):
            return
        webstack = self.sudo().with_context(active_test=False).search(
            [('serial', '=', str(serial))], limit=1)
        if (not webstack or not webstack.active or not webstack.ws_enabled
                or not webstack.ws_token
                or not consteq(webstack.ws_token, str(token))):
            self._ws_auth_failed(webstack, mtype)
            return
        webstack._ws_touch()
        if data.get('v') != WS_PROTO_VERSION:
            # Unsupported protocol: answer only a hello (SPEC §9.2), drop
            # anything else silently.
            if mtype == 'hello':
                webstack._ws_send('hr_rfid.hello_ack', {
                    'ok': False, 'err': 'proto', 'proto': WS_PROTO_VERSION})
            return
        handlers = {
            'hello': webstack._ws_on_hello,
            'hb': webstack._ws_on_hb,
            'ev': webstack._ws_on_event_batch,
            'rsp': webstack._ws_on_cmd_response,
        }
        handler = handlers.get(mtype)
        if handler is None:
            _logger.debug('WS: unknown message type %r from %s', mtype, serial)
            return
        handler(data)

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
        rec.ws_auth_fail_count += 1
        if rec.ws_auth_fail_count == WS_AUTH_FAIL_THRESHOLD:
            rec.report_sys_ev(
                'Real-time messages with an invalid channel token '
                '(%d in the last minute)' % rec.ws_auth_fail_count,
                post_data={'t': mtype})

    # -- provisioning over the classic HTTP channel (SPEC §10) ----------

    def _ws_provision_payload(self, result):
        """Attach the real-time provisioning block to an HTTP reply.

        Delivered piggyback on the existing device check-in (heartbeat /
        event / response reply) whenever the settings changed - the device
        stores them and (re)starts its websocket state machine. The legacy
        (10.3) reply encoder strips unknown keys, so only JSON-RPC (ESP32)
        modules ever see the block. Requires TLS on the classic channel in
        production - the token travels in this payload (ARCHITECTURE §8).
        """
        self.ensure_one()
        rec = self.sudo()
        if not isinstance(result, dict) or not rec.ws_provision_pending:
            return result
        if rec.ws_enabled and not rec.ws_token:
            return result   # enable flow always generates a token first
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'hr_rfid.ws_base_url') or self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
        result = dict(result)
        result['ws'] = {
            'en': 1 if rec.ws_enabled else 0,
            'url': base_url,
            'db': self.env.cr.dbname,
            'tok': rec.ws_token or '',
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

    # -- handlers ------------------------------------------------------

    def _ws_on_connect_sync(self):
        """Re-publish every pending command on device (re)connect
        (sync-on-connect, ARCHITECTURE §3.2). Idempotent: the device
        deduplicates by ``cid``, so commands already delivered over a
        previous connection are acknowledged, not re-executed."""
        self.ensure_one()
        commands = self.env['hr.rfid.command'].sudo().search([
            ('webstack_id', '=', self.id),
            ('status', 'in', ('Wait', 'Process')),
        ], order='id')
        for command in commands:
            self._ws_publish_command(command)

    def _ws_on_hello(self, data):
        self.ensure_one()
        rec = self.sudo()
        if data.get('fw'):
            rec.version = str(data['fw'])[:6]
        rec.ws_proto = WS_PROTO_VERSION
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
            try:
                with self.env.cr.savepoint():
                    if not isinstance(event, dict):
                        raise ValueError('malformed event entry')
                    ev_ts = '%s %s' % (event.get('date') or '', event.get('time') or '')
                    ctrl_num = int(event.get('id') or 0)
                    bos = int(event.get('bos') or 0)
                    if Dedup._seen(rec, ctrl_num, bos, ev_ts):
                        entry.update(ok=True, dup=True)
                        results.append(entry)
                        continue
                    result = rec.with_context(ws_no_publish=True)._hw_parse_event(
                        {'convertor': rec.serial, 'event': event})
                    status = result.get('status') if isinstance(result, dict) else None
                    entry['ok'] = status == 200
                    if entry['ok']:
                        Dedup._claim(rec, ctrl_num, bos, ev_ts)
                    # An event may spawn an immediate command - the ev64
                    # cloud-permission reply (status 200) or the F0 setup of
                    # a new controller (status 400). Carry it inline in the
                    # ack so the controller timeout is honoured (SPEC §6.3).
                    if (inline_cmd is None and isinstance(result, dict)
                            and result.get('cmd')):
                        cmd_rec = Command.search(
                            [('webstack_id', '=', rec.id),
                             ('status', '=', 'Process')],
                            order='id desc', limit=1)
                        inline_cmd = {'cid': cmd_rec.id or 0,
                                      'cmd': result['cmd']}
            except Exception:
                # ok:false -> the device keeps the event and re-sends it
                # later; the failure is visible in the log and as a system
                # event. Same recovery shape as the HTTP path's 500.
                _logger.warning(
                    'WS: event %s of batch %s from %s failed to parse',
                    i, bid, rec.serial, exc_info=True)
                try:
                    rec.report_sys_ev(
                        'Real-time event could not be processed',
                        post_data={'bid': bid, 'event': event})
                except Exception:
                    _logger.exception('WS: could not log the parse failure')
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
            if (candidate and candidate.webstack_id == rec
                    and candidate.status == 'Process'):
                command = candidate
        rec.parse_response(
            {'convertor': rec.serial, 'response': response},
            direct_cmd=True, command=command)
