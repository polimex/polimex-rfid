# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from decimal import Decimal


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    hr_rfid_vending_balance = fields.Float(
        string='Vending Balance',
        help='Amount of money an employee can spend on the vending machine',
        default=0.0,
    )

    hr_rfid_vending_recharge_balance = fields.Float(
        string='Self Recharge Balance',
        help='Amount of self charged money the employee can spend on the vending machine',
        default=0.0,
    )

    hr_rfid_vending_negative_balance = fields.Boolean(
        string='Negative Balance',
        help='Whether the user is allowed to have a negative balance or not',
        tracking=True,
    )

    # Only displayed if negative_balance is true
    hr_rfid_vending_limit = fields.Float(
        string='Limit',
        help='User cannot go in more debt than this value',
        default=0.0,
        tracking=True,
    )

    hr_rfid_vending_in_attendance = fields.Boolean(
        string='Only while attending',
        help='Only allow the user to perform vending transactions while attending',
        tracking=True,
    )

    hr_rfid_vending_daily_limit = fields.Float(
        string='Daily Limit',
        help='Maximum amount of funds allowed for the employee to spend each day. No limit if set to 0.',
        default=0.0,
    )

    hr_rfid_vending_spent_today = fields.Float(
        string='Spend Today',
        default=0.0,
    )

    hr_rfid_vending_auto_refill = fields.Boolean(
        string='Auto Refill',
        help='Automatically refill balance monthly',
        default=False,
        tracking=True,
    )

    hr_rfid_vending_refill_amount = fields.Float(
        string='Refill Amount',
        help="How much money to be added to the person's balance",
        default=0.0,
        tracking=True,
    )

    hr_rfid_vending_refill_type = fields.Selection(
        selection=[('fixed', 'Fixed'), ('up_to', 'Up To')],
        string='Refill Type',
        help="Fixed type just adds the refill amount to the user's balance every month. Up To type adds to the user's balance every month with a maximum the auto refill will never go over.",
        default='fixed',
        tracking=True,
    )

    hr_rfid_vending_refill_max = fields.Float(
        string='Refill Max',
        help='The limit of cash the auto refill should never go over',
        default=0.0,
    )

    hr_rfid_vending_balance_history = fields.One2many(
        'hr.rfid.vending.balance.history',
        'employee_id',
        string='Balance History',
    )

    def employee_vending_balance_history_action(self):
        self.ensure_one()
        bh_action = self.env.ref('hr_rfid_vending.hr_rfid_vending_balance_history_action').sudo().read()[0]
        bh_action['domain'] = [('employee_id', '=', self.id)]
        return bh_action

    def get_employee_balance(self, controller):
        self.ensure_one()
        balance = Decimal(str(self.hr_rfid_vending_balance))
        if self.hr_rfid_vending_negative_balance is True:
            balance += Decimal(str(abs(self.hr_rfid_vending_limit)))
        if balance <= 0:
            return '0000', 0
        if self.hr_rfid_vending_in_attendance is True:
            if self.attendance_state == 'checked_out':
                return '0000', 0
        balance += Decimal(str(self.hr_rfid_vending_recharge_balance))
        if self.hr_rfid_vending_daily_limit != 0:
            limit = abs(self.hr_rfid_vending_daily_limit)
            limit = Decimal(str(limit))
            limit -= Decimal(str(self.hr_rfid_vending_spent_today))
            if limit < balance:
                balance = limit
        balance *= 100
        if controller.scale_factor > 0:
            balance /= controller.scale_factor
        else:
            balance = 0
        balance = int(balance)
        if balance > 0xFF:
            balance = 0xFF
        b1 = (balance & 0xF0) // 0x10
        b2 = balance & 0x0F
        return '%02X%02X' % (b1, b2), balance

    @api.returns('hr.rfid.vending.balance.history')
    def hr_rfid_vending_add_to_balance(self, value: float, ev: int = 0):
        """
        Add to the balance of an employee
        :param value: How much to add/subtract to/from the balance. Can be a positive or negative number.
        :param ev: Event id, ignored if 0
        :return: Balance history if successful
        """
        bh_ids = self.env['hr.rfid.vending.balance.history']
        for e in self:
            new_vend_balance = e.hr_rfid_vending_balance + value
            new_recharge_balance = e.hr_rfid_vending_recharge_balance
            if new_vend_balance < 0 and abs(new_vend_balance) > abs(e.hr_rfid_vending_limit):
                new_recharge_balance -= abs(new_vend_balance) - abs(e.hr_rfid_vending_limit)
                new_vend_balance = -abs(e.hr_rfid_vending_limit)

            e.write({
                'hr_rfid_vending_balance': new_vend_balance,
                'hr_rfid_vending_recharge_balance': new_recharge_balance,
            })

            bh_dict = {
                'balance_change': value,
                'employee_id': e.id,
                'balance_result': e.hr_rfid_vending_balance,
            }
            if ev > 0:
                bh_dict['vending_event_id'] = ev
            bh_ids += self.env['hr.rfid.vending.balance.history'].create(bh_dict)
        return bh_ids

    @api.returns('hr.rfid.vending.balance.history')
    def hr_rfid_vending_set_balance(self, value: float, max_add: float = 0, min_add: float = 0, ev: int = 0):
        """
        Set an employee's balance to a specific number, with the option of max_add
        :param value:
        :param max_add:
        :param min_add:
        :param ev: Event id, ignored if 0
        :return: Balance history on success
        """
        bh_ids = self.env['hr.rfid.vending.balance.history']
        for c in self:
            val = value - c.hr_rfid_vending_balance
            if max_add != 0 and val > max_add:
                val = max_add
            if min_add != 0 and val < min_add:
                val = min_add
            bh_ids += c.hr_rfid_vending_add_to_balance(val, ev)
        return bh_ids

    @api.returns('hr.rfid.vending.balance.history')
    def hr_rfid_vending_purchase(self, cost: float, ev: int = 0):
        """
        Purchase a product. Subtracts the parameter "cost" from the employee's balance
        :param cost: How much to subtract
        :param ev: Event id, ignored if 0
        :return: Balance history on success
        """
        return self.hr_rfid_vending_add_to_balance(-cost, ev)

    @api.model
    def _reset_daily_limits(self):
        self.search([
            ('hr_rfid_vending_spent_today', '!=', 0),
        ]).write({
            'hr_rfid_vending_spent_today': 0,
        })
