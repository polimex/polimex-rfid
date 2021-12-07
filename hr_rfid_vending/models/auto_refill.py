from odoo import fields, models, api


class VendingAutoRefillEvents(models.Model):
    _name = 'hr.rfid.vending.auto.refill'
    _description = 'Auto Refill Events'
    _order = 'id desc'

    name = fields.Char(
        string='Name',
        default=lambda self: self.env['ir.sequence'].next_by_code('hr.rfid.vending.auto.refill.event.seq'),
    )

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

    @api.model
    def _auto_refill(self):
        employees = self.env['hr.employee'].search([])
        balance_histories = self.env['hr.rfid.vending.balance.history']
        total_refill = 0.0

        for emp in employees:
            auto_refill = emp.hr_rfid_vending_auto_refill
            refill_amount = emp.hr_rfid_vending_refill_amount
            refill_type = emp.hr_rfid_vending_refill_type
            refill_max = emp.hr_rfid_vending_refill_max

            if auto_refill is False:
                continue

            if refill_amount == 0:
                continue

            if refill_type == 'fixed':
                if emp.hr_rfid_vending_balance != refill_amount:
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

        if len(balance_histories) > 0:
            re = self.create([{'auto_refill_total': total_refill}])
            balance_histories.write({'auto_refill_id': re.id})

