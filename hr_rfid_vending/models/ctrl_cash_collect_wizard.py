# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _


class CashCollectLog(models.Model):
    _name = 'hr.rfid.ctrl.cash.log'
    _description = 'Cash Collect log from Vending Machines'

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        required=True,
        readonly=True,
        string="Vending Machine",
        help="Vending machine from which cash was collected. Set automatically based on the collection event."
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        readonly=True,
        default=lambda self: self.env.user.company_id.currency_id,
    )
    value = fields.Monetary(
        string='Amount Collected',
        help="""Amount of physical cash collected from the vending machine.
        
• Physical cash: Real money removed from machine's cash storage
• Tracking: Logged for audit trail and cash management
• Machine update: Reduces the machine's cash_contained amount
• Currency: Uses company's default currency
        
Record the actual amount of cash physically removed from the machine.""",
        readonly=True,
        required=True,
    )

class CashCollectWiz(models.TransientModel):
    _name = 'hr.rfid.ctrl.cash.wiz'
    _description = 'Wizard for Collect cash from Vending Machine'

    def _default_ctrl(self):
        return self.env['hr.rfid.ctrl'].browse(self.env.context.get('active_ids'))

    def _default_value(self):
        ctrl_id = self._default_ctrl()
        return ctrl_id.cash_contained

    controller_ids = fields.Many2many(
        'hr.rfid.ctrl',
        required=True,
        readonly=True,
        default=_default_ctrl,
        string="Vending Machines",
        help="""Vending machines from which cash will be collected.
        
• Multiple machines: Can collect from several machines at once
• Batch operation: Efficient for route-based cash collection
• Pre-selected: Based on current context or selection
• Validation: System ensures machines have sufficient cash
        
Select all machines from which you are physically collecting cash."""
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        readonly=True,
        default=lambda self: self.env.user.company_id.currency_id,
    )
    value = fields.Monetary(
        string='Collection Amount',
        help="""Amount of cash to collect from each selected vending machine.
        
• Per machine: This amount applies to each selected machine
• Validation: Cannot exceed the cash currently in each machine
• Default: Pre-filled with current cash amount if single machine selected
• Tracking: Creates collection log entries for audit purposes
        
Enter the amount you are physically removing from the machines.""",
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
