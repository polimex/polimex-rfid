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
import secrets
from datetime import timedelta

from odoo import api, fields, models, _

# Wire-contract constants (docs/odoo-bus/ODOO_BUS_PROTOCOL_SPEC.md)
WS_PROTO_VERSION = 1
# Token rotation: how long the old channel keeps receiving mirrored
# publishes after a rotation (SPEC §6.6 "grace_s").
WS_TOKEN_ROTATE_GRACE_S = 300
# Default heartbeat interval the server advertises in hello_ack (SPEC §6.1);
# tunable per install via the system parameter below.
WS_HB_INTERVAL_DEFAULT_S = 60
WS_HB_INTERVAL_PARAM = 'hr_rfid.ws_hb_interval'


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
        copy=False,
        help='The real-time settings changed and will be delivered to the '
             'module on its next check-in.',
    )

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
