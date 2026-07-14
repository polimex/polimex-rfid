# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Unit tests for the WebSocket (Odoo bus) transport layer - package A of
docs/odoo-bus/ODOO_BUS_ODOO_PLAN.md (esp32 repo); wire contract in
ODOO_BUS_PROTOCOL_SPEC.md (proto 3: key-channel, no ws_token, TOFU re-key)."""
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.models.hr_rfid_webstack_ws import WS_PROTO_VERSION
from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_ws')
class TestWsLayer(RFIDAppCase):
    """Channel naming, publish helper, presence, provisioning, re-key.

    proto 3 (owner 2026-07-14): the channel credential is the module ``key``
    (server_push_key) - there is no server-issued ws_token, so there is no
    token generation or rotation to test; re-key is TOFU (clear the key,
    adopt the next hello's ``k``).
    """

    def _ws(self):
        return self.test_webstack_10_3_id

    # ------------------------------------------------------------------
    # Enable / disable / re-key
    # ------------------------------------------------------------------

    def test_enable_does_not_mint_a_secret(self):
        ws = self._ws()
        self.assertFalse(ws.ws_enabled)
        key_before = ws.sudo().key
        ws.action_ws_enable()
        self.assertTrue(ws.ws_enabled)
        self.assertTrue(ws.ws_provision_pending)
        # proto 3 has no ws_token: the channel credential is the existing key,
        # so enable must not touch it.
        self.assertEqual(ws.sudo().key, key_before,
                         'enable must reuse the module key, not mint a token')

    def test_disable_keeps_key(self):
        ws = self._ws()
        ws.action_ws_enable()
        key = ws.sudo().key
        ws.action_ws_disable()
        self.assertFalse(ws.ws_enabled)
        self.assertEqual(ws.sudo().key, key, 'disable must not clear the key')

    def test_rekey_clears_key_for_tofu(self):
        """action_ws_rekey arms TOFU: it clears the stored key so the next
        authenticated hello adopts the device's current ``k`` (SPEC §6.6)."""
        ws = self._ws()
        ws.action_ws_enable()
        self.assertTrue(ws.sudo().key)
        ws.action_ws_rekey()
        self.assertFalse(ws.sudo().key, 'rekey clears the key (TOFU re-adopt)')
        self.assertTrue(ws.ws_provision_pending)

    # ------------------------------------------------------------------
    # Channel + publish helper
    # ------------------------------------------------------------------

    def test_channel_format(self):
        ws = self._ws()
        ws.action_ws_enable()
        self.assertEqual(
            ws._ws_channel(), 'hr_rfid#%s#%s' % (ws.serial, ws.sudo().key))

    def test_send_requires_enabled_and_key(self):
        ws = self._ws()  # not enabled
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

    def test_send_requires_a_key(self):
        """With the key cleared (TOFU armed) there is no channel to publish
        on, so _ws_send is a no-op until the next hello re-adopts the key."""
        ws = self._ws()
        ws.action_ws_enable()
        ws.sudo().key = False
        with patch.object(type(self.env['bus.bus']), '_sendone') as sendone:
            self.assertFalse(ws._ws_send('hr_rfid.sync', {'pending_cmds': 3}))
        sendone.assert_not_called()

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
        # proto 3: NO token travels down - the device owns its key.
        self.assertNotIn('tok', block, 'proto 3 sends no secret in the block')
        self.assertEqual(block['db'], self.env.cr.dbname)
        self.assertTrue(block['url'])
        self.assertEqual(block['proto'], WS_PROTO_VERSION)
        # the original dict is not mutated (the reply may be reused)
        self.assertNotIn('ws', base)

