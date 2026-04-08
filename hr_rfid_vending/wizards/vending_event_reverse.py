from datetime import datetime, time, timedelta

from odoo import fields, models, _
from odoo.exceptions import UserError


class VendingEventReverse(models.TransientModel):
    _name = 'hr.rfid.vending.event.reverse'
    _description = 'Reverse Vending Purchase'

    event_id = fields.Many2one(
        'hr.rfid.vending.event',
        required=True,
        readonly=True,
        default=lambda self: self.env.context.get('active_id'),
    )
    reason = fields.Text(
        string='Reason',
        required=True,
    )

    def _is_already_reversed(self, event):
        """Check if this purchase already has a positive balance_history
        record (= already reversed)."""
        return bool(self.env['hr.rfid.vending.balance.history'].search([
            ('vending_event_id', '=', event.id),
            ('balance_change', '>', 0),
        ], limit=1))

    def action_reverse(self):
        self.ensure_one()
        event = self.event_id

        if event.event_action != '47':
            raise UserError(_('Only purchase events can be reversed.'))
        if not event.employee_id:
            raise UserError(_('Cannot reverse a cash purchase (no employee).'))
        if self._is_already_reversed(event):
            raise UserError(_('This event has already been reversed.'))

        # Restore balance — creates balance_history with vending_event_id
        event.employee_id.hr_rfid_vending_add_to_balance(
            event.transaction_price, ev=event.id,
        )

        # Neutralize daily limit if within same period
        self._neutralize_daily_spend(event)

        # Post reason as chatter message on original event
        event.message_post(
            body=_('Reversed by %s. Reason: %s') % (
                self.env.user.name, self.reason),
        )

        return {'type': 'ir.actions.act_window_close'}

    def _neutralize_daily_spend(self, event):
        """If the original purchase is within today's daily limit period,
        set its balance_history.balance_change to 0 so _compute_spend_today
        no longer counts it."""
        emp = event.employee_id
        if not emp.hr_rfid_vending_daily_limit:
            return

        # Find the original purchase balance history (negative change)
        bh = self.env['hr.rfid.vending.balance.history'].search([
            ('vending_event_id', '=', event.id),
            ('balance_change', '<', 0),
        ], limit=1)
        if not bh:
            return

        # Check if within current daily limit period
        now = fields.Datetime.now()
        if emp.daily_limit_type == 'last_24':
            cutoff = now - timedelta(hours=24)
        else:
            cutoff = datetime.combine(fields.Date.today(), time(0, 0, 0))

        if bh.create_date >= cutoff:
            bh.sudo().write({'balance_change': 0})
