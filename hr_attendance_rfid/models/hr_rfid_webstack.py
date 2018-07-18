# -*- coding: utf-8 -*-
from odoo import models, api, fields, exceptions


class HrRfidDoor(models.Model):
    _inherit = "hr.rfid.door"

    attendance = fields.Boolean(
        string='Attendance',
        help='Door will track attendance if ticked. Door must '
             'have an in and an out reader to track attendance',
        default=False,
    )

    @api.onchange('attendance')
    def _attendance_on_change(self):
        if self.attendance is True:
            has_in = False
            has_out = False
            for reader in self.reader_ids:
                if reader.reader_type == '0':
                    has_in = True
                elif reader.reader_type == '1':
                    has_out = True

            if has_in is False or has_out is False:
                self.attendance = False
                raise exceptions.ValidationError('This door cannot track attendance because it '
                                                 'does not have both an in and out reader.')

    @api.multi
    @api.constrains('attendance')
    def _attendance_constrains(self):
        for door in self:
            if door.attendance is True:
                has_in = False
                has_out = False
                for reader in door.reader_ids:
                    if reader.reader_type == '0':
                        has_in = True
                    elif reader.reader_type == '1':
                        has_out = True

                if has_in is False or has_out is False:
                    raise exceptions.ValidationError('This door cannot track attendance because it '
                                                     'does not have both an in and out reader.')



