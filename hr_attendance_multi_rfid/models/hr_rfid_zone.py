# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models, api, fields, _, exceptions
from dateutil.relativedelta import relativedelta


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

    max_time_in_zone = fields.Float(
        help='Maximum attendance time in zone. Used for auto-close attendance. Zero means not use.',
        default=12,
        digits=(2, 2)
    )
    auto_close_time_for_zone = fields.Float(
        help='Attendance time in zone if autoclosed. Used for auto-close attendance',
        default=7,
        digits=(2, 2)
    )
    delete_attendance_if_late_more_than = fields.Float(
        help='Remove attendance for employee if late is more than this time. Set zeo to disable function.',
        default=0,
        digits=(2, 2)
    )

    # TODO Need to added .with_context(no_validity_check=True) for attendance management!!!
    def person_entered(self, person, event):
        is_employee = isinstance(person, type(self.env['hr.employee']))
        if not is_employee:
            return super(HrRfidZone, self).person_entered(person, event)

        for zone in self.filtered(lambda z: z.attendance):
            if is_employee and not zone._check_employee_permit(person):
                continue
            check = person._last_open_checkin(zone.id, before_dt=event and event.event_time or None)

            if check and zone.overwrite_check_in:
                if event:
                    event.in_or_out = 'in'
                    if person.last_attendance_id and person.last_attendance_id.check_out and person.last_attendance_id.check_out < event.event_time:
                        check.with_context(no_validity_check=True).write({
                            'check_in': event.event_time
                        })
                else:
                    check.with_context(no_validity_check=True).write({
                        'check_in': fields.Datetime.now()
                    })
            if not check:
                if event:
                    event.in_or_out = 'in'
                    person.with_context(no_validity_check=True).attendance_action_change_with_date(event.event_time,
                                                                                               zone.id)
                else:
                    person.with_context(no_validity_check=True).attendance_action_change_with_date(fields.Datetime.now(),
                                                                                                   zone.id)
        return super(HrRfidZone, self).person_entered(person, event)

    def person_left(self, person, event=None):
        is_employee = isinstance(person, type(self.env['hr.employee']))
        if not is_employee:
            return super(HrRfidZone, self).person_left(person, event)

        for zone in self.filtered(lambda z: z.attendance):
            if is_employee and not zone._check_employee_permit(person):
                continue
            checkin = person._last_open_checkin(zone.id, before_dt=event and event.event_time or None)
            if not checkin and zone.overwrite_check_out:
                if event:
                    event.in_or_out = 'out'
                    last_att_id = self.env['hr.attendance'].search([
                        ('check_out', '<', event.event_time),
                        ('employee_id', '=', person.id),
                        ('in_zone_id', '=', zone.id),
                    ], order='check_out desc', limit=1)
                    # If event older than last checkout ignor it (6+ hours)
                    if last_att_id and (event.event_time - last_att_id.check_out) < timedelta(hours=8):
                        last_att_id.with_context(from_event=True).write({'check_out': event.event_time})
                    # if last_att_id and (event.event_time - last_att_id.check_out) < relativedelta(hours=8):
                    #     last_att_id.with_context(from_event=True).write({'check_out': event.event_time})
                else:
                    person.last_attendance_id.with_context(from_event=True).write({
                        'check_out': fields.Datetime.now()
                    })
            elif checkin and event:
                event.in_or_out = 'out'
                checkin.with_context(from_event=True).write({
                    'check_out': event.event_time
                })
            elif checkin:
                checkin.with_context(from_event=True).write({
                    'check_out': fields.Datetime.now()
                })
        return super(HrRfidZone, self).person_left(person, event)

    def attendance_for_current_zone(self):
        self.ensure_one()
        return {
            'name': _("Check In's {}").format(self.name),
            'view_mode': 'list,form',
            'res_model': 'hr.attendance',
            'domain': [('id', 'in', [i.id for i in self.employee_ids])],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         Buy Odoo Enterprise now to get more providers.
            #     </p>'''),
        }
