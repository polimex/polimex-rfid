# -*- coding: utf-8 -*-
"""Exactly-once guard for hardware events arriving over the websocket.

The controller EEPROM FIFO delivers at-least-once: a lost ``ev_ack`` makes
the device re-send the same event (it is still at the BOS position). This
table remembers what was already processed so the re-send is acknowledged
WITHOUT creating a duplicate event record (ODOO_BUS_ARCHITECTURE.md §3.1).

The natural key includes the controller timestamp because ``bos`` is an
index in a circular buffer and gets reused after a wrap.
"""
from datetime import timedelta

from odoo import api, fields, models

# Keep claims long enough to cover any realistic re-send window; the
# controller re-sends within seconds, days only accumulate on a dead link.
WS_DEDUP_RETENTION_DAYS = 7
GC_UNLINK_LIMIT = 1000


class HrRfidWsDedup(models.Model):
    _name = 'hr.rfid.ws.dedup'
    _description = 'Real-time Event Deduplication'
    _log_access = False  # hot-path table: one insert per hw event

    webstack_id = fields.Many2one(
        'hr.rfid.webstack', required=True, index=True, ondelete='cascade')
    ctrl_id_num = fields.Integer(required=True)
    bos = fields.Integer(required=True)
    ev_ts = fields.Char(size=20, required=True,
                        help='Controller date+time string of the event.')
    create_date = fields.Datetime(default=fields.Datetime.now)

    _ws_dedup_key_uniq = models.Constraint(
        'UNIQUE(webstack_id, ctrl_id_num, bos, ev_ts)',
        'Duplicate real-time event claim.'
    )

    @api.model
    def _seen(self, webstack, ctrl_id_num, bos, ev_ts):
        """True when this event key was already successfully processed."""
        return bool(self.sudo().search_count([
            ('webstack_id', '=', webstack.id),
            ('ctrl_id_num', '=', ctrl_id_num),
            ('bos', '=', bos),
            ('ev_ts', '=', ev_ts or ''),
        ], limit=1))

    @api.model
    def _claim(self, webstack, ctrl_id_num, bos, ev_ts):
        """Record a SUCCESSFULLY processed event key (claim only on success:
        an event answered with a non-200 status stays unclaimed so its
        re-send gets processed - mirrors the HTTP path where a non-200
        response keeps the event in the controller FIFO).

        Runs in a savepoint so the unique-constraint violation of a racing
        re-send never poisons the surrounding transaction.
        """
        try:
            with self.env.cr.savepoint():
                self.sudo().create({
                    'webstack_id': webstack.id,
                    'ctrl_id_num': ctrl_id_num,
                    'bos': bos,
                    'ev_ts': ev_ts or '',
                })
            return True
        except Exception:
            return False

    @api.autovacuum
    def _gc_ws_dedup(self):
        cutoff = fields.Datetime.now() - timedelta(days=WS_DEDUP_RETENTION_DAYS)
        records = self.sudo().search(
            [('create_date', '<', cutoff)], limit=GC_UNLINK_LIMIT)
        records.unlink()
        return len(records), len(records) == GC_UNLINK_LIMIT
