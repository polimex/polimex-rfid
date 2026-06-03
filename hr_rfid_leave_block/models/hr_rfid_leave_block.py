# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models
from odoo.tools.constants import GC_UNLINK_LIMIT

_logger = logging.getLogger(__name__)

# Keep restored audit rows this long, then let autovacuum reclaim them.
GC_RESTORED_BLOCK_DAYS = 365


class HrRfidLeaveBlock(models.Model):
    """Audit snapshot of RFID cards suspended for one approved leave.

    When a leave is approved we deactivate the employee's currently-active
    cards and remember EXACTLY which ones here. On restore we re-activate only
    that snapshot — so a card the employee had already disabled before the
    leave (or a third card added during it) is never silently switched on.
    One block per leave; overlapping leaves keep independent snapshots.
    """
    _name = 'hr.rfid.leave.block'
    _description = 'RFID Access Block for Leave'
    _order = 'blocked_at desc'

    leave_id = fields.Many2one(
        'hr.leave', string='Leave', required=True, ondelete='cascade', index=True,
        help="The approved time-off that triggered suspending the cards.")
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', related='leave_id.employee_id',
        store=True, index=True,
        help="Employee whose cards were suspended (from the leave).")
    company_id = fields.Many2one(
        'res.company', related='leave_id.company_id', store=True, index=True,
        help="Company of the leave, for multi-company isolation.")
    blocked_card_ids = fields.Many2many(
        'hr.rfid.card', string='Suspended Cards',
        # Suspending a card sets active=False, i.e. archives it. Without this
        # context the M2M would hide its own snapshot (active_test defaults to
        # True), and restore would find nothing to re-activate.
        context={'active_test': False},
        help="Exactly the cards that were active when the leave was approved "
             "and got deactivated. Only these are re-activated on restore.")
    state = fields.Selection([
        ('active', 'Blocking'),
        ('restored', 'Restored'),
    ], default='active', required=True, index=True,
        help="Blocking: cards currently suspended. Restored: access was given "
             "back (leave ended, cancelled or refused).")
    blocked_at = fields.Datetime(
        default=fields.Datetime.now, readonly=True,
        help="When the cards were suspended.")
    restored_at = fields.Datetime(
        readonly=True, help="When access was restored.")

    def _restore(self):
        """Re-activate the snapshot cards and mark the block restored."""
        for block in self.filtered(lambda b: b.state == 'active'):
            # Snapshot cards are archived (active=False); read them with
            # active_test off, then re-activate only those still inactive
            # (skip ones already re-enabled manually) to avoid command churn.
            cards = block.with_context(active_test=False).blocked_card_ids
            cards = cards.filtered(lambda c: not c.active)
            if cards:
                cards.write({'active': True})
            block.write({'state': 'restored', 'restored_at': fields.Datetime.now()})

    @api.model
    def _cron_restore_expired_blocks(self):
        """Restore access for leaves whose end date has passed."""
        today = fields.Date.context_today(self)
        expired = self.search([
            ('state', '=', 'active'),
            ('leave_id.date_to', '<', today),
        ])
        if expired:
            _logger.info("Restoring RFID access for %s ended leave(s).", len(expired))
            expired._restore()

    @api.autovacuum
    def _gc_restored_blocks(self):
        """Drop restored audit rows older than the retention window.

        Batched and returning ``(done, has_more)`` so the core vacuum cron
        re-queues until the table drains, matching ``ir.cron._gc_cron_triggers``
        (odoo/addons/base/models/ir_cron.py:915)."""
        limit_date = fields.Datetime.subtract(
            fields.Datetime.now(), days=GC_RESTORED_BLOCK_DAYS)
        stale = self.search([
            ('state', '=', 'restored'),
            ('restored_at', '<', limit_date),
        ], limit=GC_UNLINK_LIMIT)
        done = len(stale)
        stale.unlink()
        return done, done == GC_UNLINK_LIMIT
