# -*- coding: utf-8 -*-
"""Websocket ingress for iCON1XX modules (Odoo Bus real-time channel).

The device holds ONE anonymous websocket to ``/websocket`` and sends
``{"event_name": "hr_rfid", "data": {...}}`` frames; the bus core routes
every inbound frame through this model-level hook
(``bus/websocket.py`` ``_serve_ir_websocket`` - there is no per-message
controller on the websocket path). Authentication is per message: the
device token is verified with a constant-time compare inside
``hr.rfid.webstack._ws_dispatch``.

Known limitation (documented in the plan): Odoo.sh does not execute this
hook for custom events; Polimex installs are self-hosted.
"""
from odoo import models


class IrWebsocket(models.AbstractModel):
    _inherit = 'ir.websocket'

    def _serve_ir_websocket(self, event_name, data):
        super()._serve_ir_websocket(event_name, data)
        if event_name != 'hr_rfid':
            return
        # sudo: the websocket runs as the public user; the dispatch
        # re-authenticates every message against the webstack token
        # (the same trust model as the auth='none' HTTP route, where
        # _authenticate_webstack + SUPERUSER_ID perform the device auth).
        self.env['hr.rfid.webstack'].sudo()._ws_dispatch(data or {})
