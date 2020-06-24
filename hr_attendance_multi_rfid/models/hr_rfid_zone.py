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


    def person_entered(self, person, event):
        if not isinstance(person, type(self.env['hr.employee'])):
            return super(HrRfidZone, self).person_entered(person, event)

        for zone in self:
            if zone.attendance is False:
                continue

            if person in zone.employee_ids and zone.overwrite_check_in:
                check = self.env['hr.attendance'].search([('employee_id', '=', person.id)], limit=1)
                if check.check_out:
                    continue
                event.in_or_out = 'in'
                check.check_in = event.event_time
            elif person not in zone.employee_ids and person.attendance_state == 'checked_out':
                event.in_or_out = 'in'
                person.attendance_action_change_with_date(event.event_time)
        return super(HrRfidZone, self).person_entered(person, event)

    def person_left(self, person, event):
        if not isinstance(person, type(self.env['hr.employee'])):
            return super(HrRfidZone, self).person_left(person, event)

        for zone in self:
            if not zone.attendance:
                continue

            if person not in zone.employee_ids and zone.overwrite_check_out:
                check = self.env['hr.attendance'].search([('employee_id', '=', person.id)], limit=1)
                if event:
                    event.in_or_out = 'out'
                    check.check_out = event.event_time
                else:
                    check.check_out = fields.datetime.now()
            elif person in zone.employee_ids and person.attendance_state == 'checked_in':
                if event:
                    event.in_or_out = 'out'
                    person.attendance_action_change_with_date(event.event_time)
                else:
                    person.attendance_action_change_with_date(fields.datetime.now())

        return super(HrRfidZone, self).person_left(person, event)
