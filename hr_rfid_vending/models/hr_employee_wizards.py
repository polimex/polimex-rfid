# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from decimal import Decimal


class VendingBalanceWiz(models.TransientModel):
    _name = 'hr.employee.vending.balance.wiz'
    _description = 'Employee balance setter'

    def _default_employee(self):
        return self.env['hr.employee'].browse(self._context.get('active_ids'))

    def _default_value(self):
        emp = self._default_employee()
        if len(emp) > 0:
            return 0.0
        if self._context.get('setting_balance', False) == 2:
            return emp.hr_rfid_vending_balance
        if self._context.get('setting_balance', False) == 3:
            return emp.hr_rfid_vending_recharge_balance
        return 0.0

    employee_ids = fields.Many2many(
        'hr.employee',
        required=True,
        default=_default_employee,
    )

    value = fields.Float(
        string='Value',
        required=True,
        default=_default_value,
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
        if self._context.get('setting_balance', False) == 2:
            res = self.employee_ids.hr_rfid_vending_set_balance(self.value)
        if self._context.get('setting_balance', False) == 3:
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
