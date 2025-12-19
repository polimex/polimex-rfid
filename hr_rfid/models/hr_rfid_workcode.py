# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions


class HrRfidWorkcode(models.Model):
    _name = 'hr.rfid.workcode'
    _description = 'RFID Workcode for Time Tracking'
    _inherit = ['mail.thread']

    _rfid_workcode_unique = models.Constraint(
        'UNIQUE(workcode)',
        'Work code must be unique!'
    )
    name = fields.Char(
        string='Name',
        help='A descriptive name for this workcode that helps employees understand its purpose. '
             'For example: "Start Work", "Lunch Break", "End of Day", etc.',
        tracking=True,
        required=True,
    )
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 help='The company this workcode belongs to. In multi-company setups, '
                                      'each company can have its own set of workcodes.',
                                 default=lambda self: self.env.company)
    workcode = fields.Char(
        string='Workcode',
        help='A 4-digit numerical code that employees will enter on RFID terminals to record '
             'their time tracking actions. Must be exactly 4 digits (0000-9999). '
             'Common examples: 0001 for start work, 0002 for break, 0003 for end work.',
        size=4,
        required=True,
    )

    user_action = fields.Selection(
        selection=[
            ('stop', 'End last action (return from break, leave work, etc)'),
            ('start', 'Coming to work'),
            ('break', 'Going to a break'),
        ],
        string='User action',
        help='Defines what type of time tracking action this workcode represents:\n'
             '• Start: Records the beginning of a work shift (clock in)\n'
             '• Break: Records when an employee goes on break (lunch, rest, etc.)\n'
             '• Stop: Records the end of an action (returning from break, leaving work, etc.)',
        default='stop',
        tracking=True,
        required=True,
    )

    @api.constrains('workcode')
    def _check_workcode_code(self):
        for workcode in self:
            wc = workcode.workcode
            if len(wc) != 4:
                raise exceptions.ValidationError('Workcode must have exactly 4 characters')

            # If char is not a valid decimal number, int(char, 10) will raise an error
            try:
                for char in str(wc):
                    int(char, 10)
            except ValueError:
                raise exceptions.ValidationError('Invalid workcode, digits must be from 0 to 9')
