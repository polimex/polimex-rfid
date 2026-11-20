# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

# Leave states that mean "access should be restored" (no longer an active,
# approved absence).
RESTORE_STATES = ('draft', 'confirm', 'refuse', 'cancel')


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    rfid_block_ids = fields.One2many(
        'hr.rfid.leave.block', 'leave_id', string='RFID Access Blocks',
        help="Snapshots of RFID cards suspended while this leave is approved.")

    def write(self, vals):
        res = super().write(vals)
        # React only to a state transition, after the core write succeeded.
        if 'state' in vals:
            new_state = vals['state']
            if new_state == 'validate':
                # Only a leave that is going on now stops the cards. One that
                # starts later is picked up by the scheduled action when it
                # begins (hr.rfid.leave.block._cron_follow_the_leaves); one that
                # is already over stops nothing.
                self._rfid_going_on(fields.Datetime.now())._rfid_block_access()
            elif new_state in RESTORE_STATES:
                self._rfid_restore_access()
        return res

    def _rfid_going_on(self, moment):
        """The leaves that have begun and not yet ended at ``moment``."""
        return self.filtered(
            lambda leave: leave.date_from
            and leave.date_to
            and leave.date_from <= moment < leave.date_to
        )

    def _rfid_block_access(self):
        """Suspend the employee's currently-active cards for each leave.

        Idempotent: a leave that already has an active block is skipped, so a
        re-approval does not double-block or re-snapshot.
        """
        Card = self.env['hr.rfid.card']
        Block = self.env['hr.rfid.leave.block']
        for leave in self:
            employee = leave.employee_id
            if not employee:
                continue
            if leave.rfid_block_ids.filtered(lambda b: b.state == 'active'):
                continue
            active_cards = Card.search([
                ('employee_id', '=', employee.id),
                ('active', '=', True),
            ])
            if not active_cards:
                continue
            Block.create({
                'leave_id': leave.id,
                'blocked_card_ids': [(6, 0, active_cards.ids)],
            })
            active_cards.write({'active': False})

    def _rfid_restore_access(self):
        """Restore access snapshotted by any active block on these leaves."""
        blocks = self.rfid_block_ids.filtered(lambda b: b.state == 'active')
        blocks._restore()
