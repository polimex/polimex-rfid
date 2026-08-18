import logging

from odoo import fields, models, api, SUPERUSER_ID
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

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
        help="Auto-generated reference for each cron run (e.g. AR/2026/000123). Used as the human label in lists and history reports.",
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Company in whose scope this refill run executed. Auto-refill is scheduled per company.",
    )

    create_date = fields.Datetime(
        string='Auto Refill Time',
        help="Timestamp the cron run created the record. Use this to correlate refill totals with the cron's nextcall schedule.",
    )

    auto_refill_total = fields.Float(
        string='Total Cash Refilled',
        required=True,
        readonly=True,
        help="Sum of all balance top-ups credited during this run. A useful sanity check against the company's vending budget.",
    )

    balance_history_ids = fields.One2many(
        'hr.rfid.vending.balance.history',
        'auto_refill_id',
        string='Balance History Changes',
        help="Individual employee balance-history entries created by this run. Use them to see exactly which employees were topped up and by how much.",
    )

    # Cron job task
    @api.model
    def auto_refill_job(self):
        now = fields.Datetime.now()
        companies = self.env['res.company'].with_user(SUPERUSER_ID).search([])
        _logger.info(
            "Vending auto-refill cron started; %d companies to evaluate (now=%s)",
            len(companies), now,
        )
        for c in companies:
            if not c.refill_nextcall:
                _logger.warning(
                    "Company %s (id=%s) has no refill_nextcall set; skipping",
                    c.name, c.id,
                )
                continue
            if c.refill_nextcall > now:
                _logger.info(
                    "Company %s (id=%s): refill_nextcall=%s is in the future; skipping",
                    c.name, c.id, c.refill_nextcall,
                )
                continue
            _logger.info(
                "Company %s (id=%s): running auto-refill (nextcall was %s)",
                c.name, c.id, c.refill_nextcall,
            )
            try:
                self.with_company(c.id)._auto_refill()
            finally:
                c.refill_nextcall = c.refill_nextcall + _intervalTypes[c.refill_interval_type](c.refill_interval_number)
                _logger.info(
                    "Company %s (id=%s): refill_nextcall advanced to %s",
                    c.name, c.id, c.refill_nextcall,
                )


    @api.model
    def _auto_refill(self):
        # search() respects record rules of self.env.user; sudo() so the
        # cron user (or any caller) sees employees regardless of company
        # access lists.
        employees = self.env['hr.employee'].sudo().search([
            ('hr_rfid_vending_auto_refill', '=', True),
            ('hr_rfid_vending_refill_amount', '>', 0),
            ('company_id', '=', self.env.company.id),
        ])
        _logger.info(
            "Auto-refill for company id=%s: %d candidate employees",
            self.env.company.id, len(employees),
        )
        balance_histories = self.env['hr.rfid.vending.balance.history']
        total_refill = 0.0
        skipped_by_amount = 0
        skipped_full_balance = 0
        topped_up_count = 0

        for emp in employees:
            if not emp.hr_rfid_vending_auto_refill or float_compare(emp.hr_rfid_vending_refill_amount, 0, precision_digits=2) == 0:
                skipped_by_amount += 1
                continue
            refill_type = emp.hr_rfid_vending_refill_type
            refill_amount = emp.hr_rfid_vending_refill_amount
            refill_max = emp.hr_rfid_vending_refill_max

            if refill_type == 'fixed':
                if float_compare(emp.hr_rfid_vending_balance, refill_amount, precision_digits=2) != 0:
                    bh = emp.hr_rfid_vending_set_balance(refill_amount)
                    total_refill += bh.balance_change
                    balance_histories += bh
                    topped_up_count += 1
                else:
                    skipped_full_balance += 1
                continue

            if refill_max <= emp.hr_rfid_vending_balance:
                skipped_full_balance += 1
                continue

            difference = refill_max - emp.hr_rfid_vending_balance
            refill_amount = refill_amount if refill_amount < difference else difference
            if refill_amount != 0:
                balance_histories += emp.hr_rfid_vending_add_to_balance(refill_amount)
                total_refill += refill_amount
                topped_up_count += 1
        _logger.info(
            "Auto-refill done for company id=%s: %d topped up (total=%.2f), "
            "%d skipped (already at target), %d skipped (no amount/disabled)",
            self.env.company.id, topped_up_count, total_refill,
            skipped_full_balance, skipped_by_amount,
        )
        result = self
        if len(balance_histories) > 0:
            result = self.create([{'auto_refill_total': total_refill}])
            balance_histories.write({'auto_refill_id': result.id})
        return result
