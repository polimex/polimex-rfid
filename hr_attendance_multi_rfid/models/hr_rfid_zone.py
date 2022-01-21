# -*- coding: utf-8 -*-
from odoo import models, api, fields, exceptions


class HrRfidZone(models.Model):
    _inherit = 'hr.rfid.zone'

    attendance = fields.Boolean(
        string='Attendance',
        help='Zone will track attendance if ticked.',
        default=False,
    )

    overwrite_check_in = fields.Boolean(
        string='Overwrite check-in',
        help='If a the user has already checked in and also enters this zone then overwrite the time of the check in',
        default=False,
    )

    overwrite_check_out = fields.Boolean(
        string='Overwrite check-out',
        help='If a the user has already checked out and also leaves this zone then overwrite the time of the check out',
        default=False,
    )

    @api.multi
    def person_entered(self, person, event):
        if not isinstance(person, type(self.env['hr.employee'])):
            return super(HrRfidZone, self).person_entered(person, event)

        for zone in self.filtered(lambda z: z.attendance):
            if person.last_attendance_id and (event.event_time < person.last_attendance_id.check_in):
                continue
            any_open_check_in = self.env['hr.attendance'].search([('employee_id', '=', person.id), ('check_out', '=', False)])
            if person in zone.employee_ids and zone.overwrite_check_in and any_open_check_in:
                event.in_or_out = 'in'
                any_open_check_in.write({'check_in':  event.event_time})
            elif person not in zone.employee_ids and not any_open_check_in:
                event.in_or_out = 'in'
                person.attendance_action_change_with_date(event.event_time)
        return super(HrRfidZone, self).person_entered(person, event)

    @api.multi
    def person_left(self, person, event):
        if not isinstance(person, type(self.env['hr.employee'])):
            return super(HrRfidZone, self).person_left(person, event)

        for zone in self.filtered(lambda z: z.attendance):
            if person.last_attendance_id and (event.event_time < person.last_attendance_id.check_in):
                continue
            any_open_check_in = self.env['hr.attendance'].search([('employee_id', '=', person.id), ('check_out', '=', False)])
            if person not in zone.employee_ids and zone.overwrite_check_out:
                check = self.env['hr.attendance'].search([('employee_id', '=', person.id)], limit=1)
                if event:
                    event.in_or_out = 'out'
                    check.write({'check_out': event.event_time})
                else:
                    check.write({'check_out': fields.Datetime.now()})
            elif person in zone.employee_ids and any_open_check_in:
                if event:
                    event.in_or_out = 'out'
                    person.attendance_action_change_with_date(event.event_time)
                else:
                    person.attendance_action_change_with_date(fields.Datetime.now())

        return super(HrRfidZone, self).person_left(person, event)
