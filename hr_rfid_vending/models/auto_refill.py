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
        string='Name',
        default=lambda self: self.env['ir.sequence'].next_by_code('hr.rfid.vending.auto.refill.event.seq'),
    )
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)


    create_date = fields.Datetime(
        string='Auto Refill Time',
    )

    auto_refill_total = fields.Float(
        string='Total Cash Refilled',
        required=True,
        readonly=True,
    )

    balance_history_ids = fields.One2many(
        'hr.rfid.vending.balance.history',
        'auto_refill_id',
        string='Balance History Changes',
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
