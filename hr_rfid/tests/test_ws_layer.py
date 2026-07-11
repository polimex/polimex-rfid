# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Unit tests for the WebSocket (Odoo bus) transport layer - package A of
docs/odoo-bus/ODOO_BUS_ODOO_PLAN.md (esp32 repo); wire contract in
ODOO_BUS_PROTOCOL_SPEC.md."""
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.models.hr_rfid_webstack_ws import (
    WS_TOKEN_ROTATE_GRACE_S,
)
from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_ws')
class TestWsLayer(RFIDAppCase):
    """Token lifecycle, channel naming, publish helper, presence."""

    def _ws(self):
        return self.test_webstack_10_3_id

    # ------------------------------------------------------------------
    # Token lifecycle
    # ------------------------------------------------------------------

    def test_enable_generates_token_once(self):
        ws = self._ws()
        self.assertFalse(ws.ws_enabled)
        ws.action_ws_enable()
        self.assertTrue(ws.ws_enabled)
        self.assertTrue(ws.ws_provision_pending)
        token = ws.ws_token
        self.assertEqual(len(token), 32, 'token must be 32 hex chars (128 bit)')
        int(token, 16)  # raises if not hex
        # enable is idempotent for the secret: a second enable keeps it
        ws.action_ws_enable()
        self.assertEqual(ws.ws_token, token, 'enable must not rotate the token')

    def test_disable_keeps_token(self):
        ws = self._ws()
        ws.action_ws_enable()
        token = ws.ws_token
        ws.action_ws_disable()
        self.assertFalse(ws.ws_enabled)
        self.assertEqual(ws.ws_token, token)

    def test_rotate_token_notifies_old_channel(self):
        ws = self._ws()
        ws.action_ws_enable()
        old_token = ws.ws_token
        old_channel = ws._ws_channel()
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            ws.action_ws_rotate_token()
        self.assertNotEqual(ws.ws_token, old_token)
        self.assertEqual(ws.ws_token_old, old_token)
        self.assertTrue(ws.ws_provision_pending)
        # the rotation notice travels on the OLD channel (SPEC §6.6)
        sendone.assert_called_once()
        channel, mtype, payload = sendone.call_args.args
        self.assertEqual(channel, old_channel)
        self.assertEqual(mtype, 'hr_rfid.token')
        self.assertEqual(payload['new_token'], ws.ws_token)
        self.assertEqual(payload['grace_s'], WS_TOKEN_ROTATE_GRACE_S)

    def test_rotate_requires_enabled(self):
        ws = self._ws()
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            ws.action_ws_rotate_token()   # not enabled -> no-op
        sendone.assert_not_called()
        self.assertFalse(ws.ws_token)

    # ------------------------------------------------------------------
    # Channel + publish helper
    # ------------------------------------------------------------------

    def test_channel_format(self):
        ws = self._ws()
        ws.action_ws_enable()
        self.assertEqual(
            ws._ws_channel(), 'hr_rfid#%s#%s' % (ws.serial, ws.ws_token))
        self.assertEqual(
            ws._ws_channel(token='cafe'), 'hr_rfid#%s#cafe' % ws.serial)

    def test_send_requires_enabled_and_token(self):
        ws = self._ws()
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self.assertFalse(ws._ws_send('hr_rfid.sync', {'pending_cmds': 1}))
        sendone.assert_not_called()

    def test_send_publishes_on_device_channel(self):
        ws = self._ws()
        ws.action_ws_enable()
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self.assertTrue(ws._ws_send('hr_rfid.sync', {'pending_cmds': 2}))
        sendone.assert_called_once_with(
            ws._ws_channel(), 'hr_rfid.sync', {'pending_cmds': 2})

    def test_send_mirrors_old_channel_during_grace(self):
        ws = self._ws()
        ws.action_ws_enable()
        old_channel = ws._ws_channel()
        ws.action_ws_rotate_token()
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            ws._ws_send('hr_rfid.sync', {'pending_cmds': 3})
        channels = [c.args[0] for c in sendone.call_args_list]
        self.assertEqual(len(channels), 2, 'grace window -> publish on both')
        self.assertIn(ws._ws_channel(), channels)
        self.assertIn(old_channel, channels)
        # after the grace window only the new channel receives
        ws.sudo().ws_token_rotated_at = fields.Datetime.now() - timedelta(
            seconds=WS_TOKEN_ROTATE_GRACE_S + 5)
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            ws._ws_send('hr_rfid.sync', {'pending_cmds': 4})
        sendone.assert_called_once_with(
            ws._ws_channel(), 'hr_rfid.sync', {'pending_cmds': 4})

    # ------------------------------------------------------------------
    # Presence
    # ------------------------------------------------------------------

    def test_ws_online_compute_and_search(self):
        ws = self._ws()
        Webstack = self.env['hr.rfid.webstack']
        self.assertFalse(ws.ws_online, 'disabled -> offline')
        ws.action_ws_enable()
        self.assertFalse(ws.ws_online, 'no activity yet -> offline')
        ws._ws_touch()
        self.assertTrue(ws.ws_online)
        self.assertIn(ws, Webstack.search([('ws_online', '=', True)]))
        # stale activity -> offline (older than 2 heartbeat intervals)
        ws.sudo().ws_last_seen = fields.Datetime.now() - timedelta(
            seconds=3 * ws._ws_hb_interval())
        ws.invalidate_recordset(['ws_online'])
        self.assertFalse(ws.ws_online)
        self.assertIn(ws, Webstack.search([('ws_online', '=', False)]))
        self.assertNotIn(ws, Webstack.search([('ws_online', '=', True)]))

    # ------------------------------------------------------------------
    # Provisioning over the classic HTTP reply (SPEC §10)
    # ------------------------------------------------------------------

    def test_provision_payload_only_when_pending(self):
        ws = self._ws()
        base = {'status': 200}
        self.assertEqual(ws._ws_provision_payload(base), base,
                         'nothing pending -> untouched reply')
        ws.action_ws_enable()   # sets ws_provision_pending
        result = ws._ws_provision_payload(base)
        self.assertEqual(result['status'], 200)
        block = result['ws']
        self.assertEqual(block['en'], 1)
        self.assertEqual(block['tok'], ws.ws_token)
        self.assertEqual(block['db'], self.env.cr.dbname)
        self.assertTrue(block['url'])
        self.assertEqual(block['proto'], 1)
        # the original dict is not mutated (the reply may be reused)
        self.assertNotIn('ws', base)

    def test_provision_cleared_by_hello(self):
        ws = self._ws()
        ws.action_ws_enable()
        self.assertTrue(ws.ws_provision_pending)
        with patch.object(type(self.env['bus.bus']), '_sendone'):
            self.env['ir.websocket']._serve_ir_websocket('hr_rfid', {
                'v': 1, 's': ws.serial, 'k': ws.ws_token, 't': 'hello'})
        self.assertFalse(ws.ws_provision_pending,
                         'a hello with the new token confirms delivery')
        self.assertEqual(ws._ws_provision_payload({'status': 200}),
                         {'status': 200})

    # ------------------------------------------------------------------
    # Secret protection
    # ------------------------------------------------------------------

    def test_token_field_is_group_protected(self):
        ws = self._ws()
        ws.action_ws_enable()
        user = self.env['res.users'].create({
            'name': 'WS NoAccess',
            'login': 'ws_noaccess',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        with self.assertRaises(AccessError):
            ws.with_user(user).read(['ws_token'])
