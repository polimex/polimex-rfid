# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from decimal import Decimal


class VendingBalanceWiz(models.TransientModel):
    _name = 'hr.employee.vending.balance.wiz'
    _description = 'Employee balance setter'

    def _default_employee(self):
        return self.env['hr.employee'].browse(self.env.context.get('active_ids'))

    def _default_value(self):
        emp = self._default_employee()
        if len(emp) > 0:
            return 0.0
        if self.env.context.get('setting_balance', False) == 2:
            return emp.hr_rfid_vending_balance
        if self.env.context.get('setting_balance', False) == 3:
            return emp.hr_rfid_vending_recharge_balance
        return 0.0

    employee_ids = fields.Many2many(
        'hr.employee',
        required=True,
        default=_default_employee,
        string="Employees",
        help="""Select employees whose vending balances will be modified.
        
• Multiple selection: Can adjust balances for multiple employees at once
• Bulk operations: Efficient for company-wide balance adjustments
• Default selection: Pre-filled based on current context
• Required: At least one employee must be selected
        
Use for mass balance updates, corrections, or special allowances."""
    )

    value = fields.Float(
        string='Amount',
        required=True,
        default=_default_value,
        help="""Amount to add, subtract, or set for the selected employees' vending balances.
        
• Add: Positive amount increases balance (e.g., bonus allowance)
• Subtract: Amount to deduct from balance (e.g., corrections)
• Set: Target balance amount (e.g., standardize all balances)
• Currency: Uses company's default currency
        
Action depends on which button you click: Add, Subtract, or Set Value."""
    )

    def add_value(self):
        res = self.employee_ids.hr_rfid_vending_add_to_balance(self.value)
        if res is False:
            raise exceptions.ValidationError(
                "Could not add to the balance. Please check if it's going under the limit."
            )

    def subtract_value(self):
        self.ensure_one()
        res = self.employee_ids.hr_rfid_vending_add_to_balance(-self.value)
        if res is False:
            raise exceptions.ValidationError(
                "Could not subtract from the balance. Please check if it's going under the limit."
            )

    def set_value(self):
        if self.env.context.get('setting_balance', False) == 2:
            res = self.employee_ids.hr_rfid_vending_set_balance(self.value)
        if self.env.context.get('setting_balance', False) == 3:
            res = True
            for e in self.employee_ids:
                e.message_post(
                    body=_('Manual updated employee personal balance from %d to %d') %
                         (e.hr_rfid_vending_recharge_balance, self.value)
                )
                e.hr_rfid_vending_recharge_balance = self.value
        if not res:
            raise exceptions.ValidationError(
                "Could not set the balance. Please check if it's going under the limit."
            )
