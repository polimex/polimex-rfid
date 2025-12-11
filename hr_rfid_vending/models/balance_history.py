from odoo import fields, models, api


class BalanceHistory(models.Model):
    _name = 'hr.rfid.vending.balance.history'
    _description = 'Balance history for employees'
    _order = 'id desc'

    name = fields.Char(
        string='Description',
        compute='_compute_name',
        help="Description of the balance change - either the item purchased or the person responsible for manual changes."
    )

    person_responsible = fields.Many2one(
        'res.users',
        string='Person Responsible',
        default=lambda self: self.env.uid,
        readonly=True,
        help="User who initiated this balance change. For purchases, this is the purchasing employee. "
             "For manual adjustments, this is the administrator who made the change."
    )

    balance_change = fields.Float(
        string='Amount Changed',
        help="""Amount added to (+) or subtracted from (-) the employee's balance.
        
• Positive values: Money added (refills, manual top-ups, corrections)
• Negative values: Money spent (purchases, manual deductions, corrections)
• Source: Purchases, auto-refills, or manual adjustments
• Tracking: Complete audit trail of all balance movements
        
This shows the actual change amount, not the resulting balance.""",
        required=True,
        readonly=True,
    )

    balance_result = fields.Float(
        string='Resulting Balance',
        help="""Employee's total balance after this change was applied.
        
• Calculation: Previous balance + balance change = resulting balance
• Snapshot: Shows exact balance at the time of this transaction
• Audit: Useful for tracking balance progression over time
• Verification: Can be used to verify balance calculations
        
This is the employee's balance immediately after this transaction.""",
        required=True,
        readonly=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        readonly=True,
        help="Employee whose vending balance was affected by this transaction. "
             "History is deleted when employee record is removed."
    )
    department_id = fields.Many2one(
        'hr.department', 'Department',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        related='employee_id.department_id',
        store=True
    )


    vending_event_id = fields.Many2one(
        'hr.rfid.vending.event',
        string='Vending Event',
        ondelete='set null',
        readonly=True,
        help="Related vending machine transaction that caused this balance change. "
             "Empty for manual adjustments and auto-refills."
    )

    auto_refill_id = fields.Many2one(
        'hr.rfid.vending.auto.refill',
        string='Auto Refill Event',
        ondelete='set null',
        readonly=True,
        help="Related automatic refill event that added money to the employee's balance. "
             "Empty for purchases and manual adjustments."
    )

    item_id = fields.Many2one(
        'product.template',
        string='Product Purchased',
        compute='_compute_item_sold',
        store=True,
        ondelete='set null',
        help="Product that was purchased in the vending transaction that caused this balance change. "
             "Empty for refills and manual adjustments."
    )

    def _compute_name(self):
        for it in self:
            if len(it.vending_event_id) > 0 and len(it.vending_event_id.item_sold_id) > 0:
                it.name = it.vending_event_id.item_sold_id.name
            else:
                it.name = it.person_responsible.name

    def _compute_item_sold(self):
        for it in self:
            it.item_id = it.vending_event_id.item_sold_id
