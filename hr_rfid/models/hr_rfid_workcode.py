# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions


class HrRfidWorkcode(models.Model):
    _name = 'hr.rfid.workcode'
    _description = 'Workcode'
    _inherit = ['mail.thread']

    _sql_constraints = [ ('rfid_workcode_unique', 'unique(workcode)',
                          'Workcodes must be unique!') ]
    name = fields.Char(
        string='Name',
        help='A label to remind what the workcode represents.',
        track_visibility='onchange',
        required=True,
    )

    workcode = fields.Char(
        string='Workcode',
        help="The actual workcode ",
        limit=4,
        required=True,
    )

    user_action = fields.Selection(
        selection=[
            ('stop', 'End last action (return from break, leave work, etc)'),
            ('start', 'Coming to work'),
            ('break', 'Going to a break'),
        ],
        string='User action',
        help='What the user does when he submits this workcode',
        default='stop',
        track_visibility='onchange',
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
