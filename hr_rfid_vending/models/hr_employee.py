# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions


class VendingBalanceWiz(models.TransientModel):
    _name = 'hr.employee.vending.balance.wiz'

    def _default_employee(self):
        return self.env['hr.employee'].browse(self._context.get('active_ids'))

    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        default=_default_employee,
    )
    
    value = fields.Float()

    @api.multi
    def add_value(self):
        self.ensure_one()
        res = self.employee_id.hr_rfid_vending_add_to_balance(self.value)
        if res is False:
            raise exceptions.ValidationError(
                "Could not add to the balance. Please check if it's going under the limit."
            )

    @api.multi
    def subtract_value(self):
        self.ensure_one()
        res = self.employee_id.hr_rfid_vending_add_to_balance(-self.value)
        if res is False:
            raise exceptions.ValidationError(
                "Could not subtract from the balance. Please check if it's going under the limit."
            )

    @api.multi
    def set_value(self):
        self.ensure_one()
        res = self.employee_id.hr_rfid_vending_set_balance(self.value)
        if res is False:
            raise exceptions.ValidationError(
                "Could not set the balance. Please check if it's going under the limit."
            )


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    hr_rfid_vending_balance = fields.Float(
        string='Vending Balance',
        help='Amount of money an employee can spend on the vending machine',
        default=0,
    )

    hr_rfid_vending_negative_balance = fields.Boolean(
        string='Negative balance',
        help='Whether the user is allowed to have a negative balance or not',
    )

    # Only displayed if negative_balance is true
    hr_rfid_vending_limit = fields.Float(
        string='Limit',
        help='User cannot go bellow this value',
    )

    hr_rfid_vending_in_attendance = fields.Boolean(
        string='Only while attending',
        help='Only allow the user to perform vending transactions while attending',
    )

    hr_rfid_vending_balance_history = fields.One2many(
        'hr.rfid.vending.balance.history',
        'employee_id',
        string='Balance History',
    )

    @api.one
    def hr_rfid_vending_add_to_balance(self, value: float):
        """
        Add to the balance of an employee
        :param value: How much to add/subtract to/from the balance. Can be a positive or negative number.
        :return: True if successful, False otherwise
        """
        if self.hr_rfid_vending_negative_balance is False:
            if self.hr_rfid_vending_balance + value < 0:
                return False
        else:
            if self.hr_rfid_vending_balance + value < self.hr_rfid_vending_limit:
                return False

        bh_env = self.env['hr.rfid.vending.balance.history'].sudo()
        self.hr_rfid_vending_balance = self.hr_rfid_vending_balance + value
        bh_env.create({
            'balance_change': value,
            'employee_id': self.id,
            'balance_result': self.hr_rfid_vending_balance,
        })
        return True

    @api.one
    def hr_rfid_vending_set_balance(self, value: float, max_add: float = 0, min_add: float = 0):
        """
        Set an employee's balance to a specific number, with the option of max_add
        :param value:
        :param max_add:
        :param min_add:
        :return: True on success, False otherwise
        """

        val = value - self.hr_rfid_vending_balance
        if max_add != 0 and val > max_add:
            val = max_add
        if min_add != 0 and val < min_add:
            val = min_add

        return self.hr_rfid_vending_add_to_balance(val)

    @api.one
    def hr_rfid_vending_purchase(self, cost: float):
        """
        Purchase a product. Subtracts the parameter "cost" from the employee's balance
        :param cost: How much to subtract
        :return: True on success, False otherwise
        """
        if self.hr_rfid_vending_in_attendance is True and self.attendance_state != 'checked_in':
            return False

        return self.hr_rfid_vending_add_to_balance(-cost)

    @api.multi
    def write(self, vals):
        if 'hr_rfid_vending_balance' in vals:
            raise exceptions.ValidationError(
                'Cannot straight up modify the balance of a user. Please use the helper functions.'
            )
        return super(HrEmployee, self).write(vals)


class BalanceHistory(models.Model):
    _name = 'hr.rfid.vending.balance.history'
    _description = 'Balance history for employees'

    balance_change = fields.Float(
        string='Balance change',
        help="How much was deposited/withdrawn from the employee's balance",
        required=True,
    )

    balance_result = fields.Float(
        string='Balance result',
        help='How much the balance was after the change',
        required=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )










