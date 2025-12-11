from odoo import fields, models, api, SUPERUSER_ID
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare

_intervalTypes = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}
class VendingAutoRefillEvents(models.Model):
    _name = 'hr.rfid.vending.auto.refill'
    _description = 'Auto Refill Events'
    _order = 'id desc'

    name = fields.Char(
        string='Refill Event Name',
        default=lambda self: self.env['ir.sequence'].next_by_code('hr.rfid.vending.auto.refill.event.seq'),
        help="Unique identifier for this automatic refill event, generated automatically."
    )
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)


    create_date = fields.Datetime(
        string='Refill Date & Time',
        help="""Date and time when this automatic refill was processed.
        
• Schedule: Based on company's auto-refill cron job settings
• Frequency: Typically monthly, but configurable
• Processing: Shows when the refill calculation and application occurred
• Audit: Used for tracking refill schedule compliance
        
Shows exactly when employee balances were automatically updated."""
    )

    auto_refill_total = fields.Float(
        string='Total Amount Refilled',
        required=True,
        readonly=True,
        help="""Total amount of money added to all employee balances in this refill event.
        
• Calculation: Sum of all individual employee refills in this batch
• Cost tracking: Helps monitor total company spending on vending allowances
• Budget control: Useful for financial planning and budget monitoring
• Reporting: Aggregate view of refill costs per period
        
Shows the company's total investment in employee vending benefits for this cycle."""
    )

    balance_history_ids = fields.One2many(
        'hr.rfid.vending.balance.history',
        'auto_refill_id',
        string='Employee Balance Changes',
        help="""Individual balance changes made to each employee during this auto-refill event.
        
• Detail view: Shows exactly which employees received refills and how much
• Audit trail: Complete record of who received money and when
• Verification: Allows checking individual refill calculations
• Troubleshooting: Helps identify any refill processing issues

Each record shows one employee's balance change in this refill cycle."""
    )

    # Cron job task
    @api.model
    def auto_refill_job(self):
        for c in self.env['res.company'].with_user(SUPERUSER_ID).search([]):
            if c.refill_nextcall <= fields.Datetime.now():
                try:
                    self.with_company(c.id)._auto_refill()
                finally:
                    c.refill_nextcall = c.refill_nextcall + _intervalTypes[c.refill_interval_type](c.refill_interval_number)


    @api.model
    def _auto_refill(self):
        employees = self.env['hr.employee'].search([
            ('hr_rfid_vending_auto_refill', '=', True),
            ('hr_rfid_vending_refill_amount', '>', 0),
            ('company_id', '=', self.env.company.id),
        ])
        balance_histories = self.env['hr.rfid.vending.balance.history']
        total_refill = 0.0

        for emp in employees:
            if not emp.hr_rfid_vending_auto_refill or float_compare(emp.hr_rfid_vending_refill_amount, 0, precision_digits=2) == 0:
                continue
            refill_type = emp.hr_rfid_vending_refill_type
            refill_amount = emp.hr_rfid_vending_refill_amount
            refill_max = emp.hr_rfid_vending_refill_max

            if refill_type == 'fixed':
                if float_compare(emp.hr_rfid_vending_balance, refill_amount, precision_digits=2) != 0:
                    bh = emp.hr_rfid_vending_set_balance(refill_amount)
                    total_refill += bh.balance_change
                    balance_histories += bh
                continue

            if refill_max <= emp.hr_rfid_vending_balance:
                continue

            difference = refill_max - emp.hr_rfid_vending_balance
            refill_amount = refill_amount if refill_amount < difference else difference
            if refill_amount != 0:
                balance_histories += emp.hr_rfid_vending_add_to_balance(refill_amount)
                total_refill += refill_amount
        result = self
        if len(balance_histories) > 0:
            result = self.create([{'auto_refill_total': total_refill}])
            balance_histories.write({'auto_refill_id': result.id})
        return result
