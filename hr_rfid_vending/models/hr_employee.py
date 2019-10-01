# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions


class VendingBalanceWiz(models.TransientModel):
    _name = 'hr.employee.vending.balance.wiz'

    def _default_employee(self):
        return self.env['hr.employee'].browse(self._context.get('active_ids'))

    def _default_value(self):
        emp = self._default_employee()
        if self._context.get('setting_balance', False) is True:
            return emp.hr_rfid_vending_balance
        return 0.0

    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        default=_default_employee,
    )

    value = fields.Float(
        string='Value',
        required=True,
        default=_default_value,
    )

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
        string='Negative Balance',
        help='Whether the user is allowed to have a negative balance or not',
    )

    # Only displayed if negative_balance is true
    hr_rfid_vending_limit = fields.Float(
        string='Limit',
        help='User cannot go in more debt than this value',
    )

    hr_rfid_vending_in_attendance = fields.Boolean(
        string='Only while attending',
        help='Only allow the user to perform vending transactions while attending',
    )

    hr_rfid_vending_auto_refill = fields.Boolean(
        string='Auto Refill',
        help='Automatically refill balance monthly',
        default=False,
    )

    hr_rfid_vending_refill_amount = fields.Float(
        string='Refill Amount',
        help="How much money to be added to the person's balance",
        default=0,
        required=True,
    )

    hr_rfid_vending_refill_type = fields.Selection(
        [ ('fixed', 'Fixed type'), ('up_to', 'Up To type') ],
        string='Refill Type',
        help="Fixed type just adds the refill amount to the user's balance every month. Up To type adds to the user's balance every month with a maximum the auto refill will never go over.",
        default='fixed',
        required=True,
    )

    hr_rfid_vending_refill_max = fields.Float(
        string='Refill Max',
        help='The limit of cash the auto refill should never go over',
        default=0,
        required=True,
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
        bh_env = self.env['hr.rfid.vending.balance.history']
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
        return self.hr_rfid_vending_add_to_balance(-cost)

    @api.model
    def _auto_refill(self):
        employees = self.env['hr.employee'].search([])

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
                emp.hr_rfid_vending_add_to_balance(refill_amount)
                continue

            if refill_max <= emp.hr_rfid_vending_balance:
                continue

            difference = refill_max - emp.hr_rfid_vending_balance
            refill_amount = refill_amount if refill_amount < difference else difference
            emp.hr_rfid_vending_add_to_balance(refill_amount)


class BalanceHistory(models.Model):
    _name = 'hr.rfid.vending.balance.history'
    _description = 'Balance history for employees'
    _order = 'id desc'

    person_responsible = fields.Many2one(
        'res.users',
        string='Person responsible for the change',
        default=lambda self: self.env.uid,
        readonly=True,
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
    )










