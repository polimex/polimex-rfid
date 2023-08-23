# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _


class CashCollectLog(models.Model):
    _name = 'hr.rfid.ctrl.cash.log'
    _description = 'Cash Collect log from Vending Machines'

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        required=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        readonly=True,
        default=lambda self: self.env.user.company_id.currency_id,
    )
    value = fields.Monetary(
        string='Value',
        help='Amount of money collected from Vending machine',
        readonly=True,
        required=True,
    )

class CashCollectWiz(models.TransientModel):
    _name = 'hr.rfid.ctrl.cash.wiz'
    _description = 'Wizard for Collect cash from Vending Machine'

    def _default_ctrl(self):
        return self.env['hr.rfid.ctrl'].browse(self._context.get('active_ids'))

    def _default_value(self):
        ctrl_id = self._default_ctrl()
        return ctrl_id.cash_contained

    controller_ids = fields.Many2many(
        'hr.rfid.ctrl',
        required=True,
        readonly=True,
        default=_default_ctrl,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        readonly=True,
        default=lambda self: self.env.user.company_id.currency_id,
    )
    value = fields.Monetary(
        string='Value',
        help='Amount of money collected from Vending machine',
        required=True,
        default=_default_value,
    )

    def collect(self):
        for e in self.controller_ids:
            if e.cash_contained < self.value:
                raise exceptions.ValidationError(
                        "The collected cash is more then amount in machine. Check detail and try again."
                    )

            e.message_post(
                body=_('Manual cash collect amount: %f %s') %
                     (self.currency_id.round(self.value), self.currency_id.name)
            )
            self.env['hr.rfid.ctrl.cash.log'].create({
              'controller_id': e.id,
              'value': self.value
            })
            e.cash_contained -= self.value
