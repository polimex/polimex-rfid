from odoo import _, fields, models, api


class BalanceHistory(models.Model):
    _name = 'hr.rfid.vending.balance.history'
    _description = 'Balance history for employees'
    _order = 'id desc'

    name = fields.Char(
        string='Person Responsible/Item',
        compute='_compute_name',
        help="Human-readable label — the operator who made the change for manual adjustments, the product name for vending sales, or 'Reversal: …' for reversed sales.",
    )

    person_responsible = fields.Many2one(
        'res.users',
        string='Person responsible for the change',
        default=lambda self: self.env.uid,
        readonly=True,
        help="User who triggered the balance change. For vending sales this is the system user; for manual top-ups it is the operator who used the wizard.",
    )

    balance_change = fields.Float(
        string='Balance change',
        help="How much was deposited/withdrawn from the employee's balance",
        required=True,
        readonly=True,
    )

    balance_result = fields.Float(
        string='Balance result',
        help='How much the balance was after the change',
        required=True,
        readonly=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        readonly=True,
        help="Employee whose vending balance changed. Cascades on delete — when the employee record is removed, their balance history is removed with them.",
    )
    department_id = fields.Many2one(
        'hr.department', 'Department',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        related='employee_id.department_id',
        store=True,
        help="Department of the employee at the time of the change. Stored so reports filter correctly even after the employee moves.",
    )


    vending_event_id = fields.Many2one(
        'hr.rfid.vending.event',
        string='Event',
        ondelete='set null',
        readonly=True,
        help="Vending controller event that triggered the balance change (a sale or a sale reversal). Empty for manual operator adjustments.",
    )

    auto_refill_id = fields.Many2one(
        'hr.rfid.vending.auto.refill',
        string='Auto Refill Event',
        ondelete='set null',
        readonly=True,
        help="Auto-refill cron run that produced this credit. Empty for manual top-ups and for sales/reversals.",
    )

    item_id = fields.Many2one(
        'product.template',
        string='Item Sold',
        compute='_compute_item_sold',
        store=True,
        ondelete='set null',
        help="Product matching the item sold by the vending controller for this entry — copied from the linked vending event so it survives event archiving.",
    )

    def _compute_name(self):
        for it in self:
            if it.vending_event_id and it.balance_change > 0:
                # Reversal record — show "Reversal: Product" or "Reversal"
                product = it.vending_event_id.item_sold_id.name or ''
                it.name = _('Reversal: %s') % product if product else _('Reversal')
            elif it.vending_event_id and it.vending_event_id.item_sold_id:
                it.name = it.vending_event_id.item_sold_id.name
            else:
                it.name = it.person_responsible.name

    def _compute_item_sold(self):
        for it in self:
            it.item_id = it.vending_event_id.item_sold_id
