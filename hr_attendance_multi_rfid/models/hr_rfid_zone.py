# -*- coding: utf-8 -*-
import logging

from datetime import timedelta

from odoo import models, api, fields, _, exceptions
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class HrRfidZone(models.Model):
    _name = 'hr.rfid.zone'
    _inherit = 'hr.rfid.zone'

    attendance = fields.Boolean(
        string='Attendance',
        help="Enable automatic attendance tracking for this zone. When employees enter this zone, "
             "they will be automatically checked in for attendance. When they leave, they will be "
             "checked out. Perfect for main entrances or work areas.",
        default=False,
    )

    overwrite_check_in = fields.Boolean(
        string='Overwrite check-in',
        help="When enabled, if an employee who is already checked in enters this zone, their check-in "
             "time will be updated to the current time. Useful when you want the most recent zone entry "
             "to be considered as the actual work start time.",
        default=False,
    )

    overwrite_check_out = fields.Boolean(
        string='Overwrite check-out',
        help="When enabled, if an employee who has already checked out leaves this zone, their check-out "
             "time will be updated to the current time. Useful for ensuring the last zone exit is recorded "
             "as the actual work end time.",
        default=False,
    )

    max_time_in_zone = fields.Float(
        string="Maximum Hours in Zone",
        help="Maximum hours an employee can stay in the zone before attendance is automatically closed. "
             "This prevents forgotten check-outs from creating excessively long attendance records. "
             "Set to 0 to disable automatic closure. Example: 12 hours for a standard work day.",
        default=12,
        digits=(2, 2)
    )
    auto_close_time_for_zone = fields.Float(
        string="Auto-close Worked Hours",
        help="When attendance is automatically closed (due to max_time_in_zone), this value will be "
             "recorded as the actual worked hours. For example, if max is 12 hours but this is set to 7, "
             "the system will record 7 hours of work when auto-closing.",
        default=7,
        digits=(2, 2)
    )
    delete_attendance_if_late_more_than = fields.Float(
        string="Delete if Late More Than (Hours)",
        help="Automatically delete attendance records if the employee is late by more than this many hours. "
             "This helps maintain data quality by removing likely erroneous entries. Set to 0 to disable "
             "this feature. Example: Set to 4 to delete attendance if someone is more than 4 hours late.",
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
                        check.with_context(no_validity_check=True, rfid_machinery_write=True).write({
                            'check_in': event.event_time
                        })
                else:
                    check.with_context(no_validity_check=True, rfid_machinery_write=True).write({
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
        """Handle person leaving a zone with improved out-of-order event support.
        
        This method processes exit events and updates attendance records accordingly.
        It handles various scenarios:
        - Normal check-out (open attendance exists)
        - Out-of-order check-out (finding the correct attendance to close)
        - Overwrite check-out (updating recently closed attendances)
        
        :param person: hr.employee or res.partner
        :param event: Optional RFID event that triggered this action
        """
        is_employee = isinstance(person, type(self.env['hr.employee']))
        if not is_employee:
            return super(HrRfidZone, self).person_left(person, event)

        for zone in self.filtered(lambda z: z.attendance):
            if is_employee and not zone._check_employee_permit(person):
                continue
            
            # For out-of-order events, we need more sophisticated attendance matching
            if event:
                # First, try to find an open attendance that should be closed by this event.
                # The attendance must have started AT or BEFORE this event time:
                # controller clocks have 1-second resolution, so an entry and an
                # exit on adjacent readers can legitimately carry the same
                # timestamp. A strict '<' here silently dropped such check-outs,
                # leaving the attendance open forever (core allows
                # check_out == check_in, see hr_attendance
                # _check_validity_check_in_check_out).
                attendance_to_close = self.env['hr.attendance'].search([
                    ('employee_id', '=', person.id),
                    ('check_in', '<=', event.event_time),
                    ('check_out', '=', False),
                    ('in_zone_id', '=', zone.id),
                ], order='check_in desc', limit=1)
                
                if attendance_to_close:
                    # Found an open attendance to close
                    event.in_or_out = 'out'
                    
                    # Validate check_out time is after check_in
                    check_out_time = event.event_time
                    if check_out_time < attendance_to_close.check_in:
                        _logger.warning(
                            'Check-out time %s is before check-in time %s for employee %s. '
                            'Setting check-out to check-in + 1 minute.',
                            check_out_time, attendance_to_close.check_in, person.name
                        )
                        check_out_time = attendance_to_close.check_in + timedelta(minutes=1)
                    
                    attendance_to_close.with_context(from_event=True, no_validity_check=True).write({
                        'check_out': check_out_time
                    })
                elif zone.overwrite_check_out:
                    # No open attendance found, but zone allows overwriting recent check-outs
                    event.in_or_out = 'out'
                    
                    # Find the most recent closed attendance
                    last_att_id = self.env['hr.attendance'].search([
                        ('check_out', '<', event.event_time),
                        ('employee_id', '=', person.id),
                        ('in_zone_id', '=', zone.id),
                    ], order='check_out desc', limit=1)
                    
                    # Only update if the event is within 8 hours of the last check-out
                    # This prevents updating very old records with out-of-order events
                    if last_att_id and (event.event_time - last_att_id.check_out) < timedelta(hours=8):
                        # Ensure the new check_out is still after check_in
                        if event.event_time > last_att_id.check_in:
                            last_att_id.with_context(from_event=True, no_validity_check=True).write({
                                'check_out': event.event_time
                            })
                        else:
                            _logger.warning(
                                'Cannot update check-out to %s as it would be before check-in %s',
                                event.event_time, last_att_id.check_in
                            )
            else:
                # Real-time event (no specific event time)
                # Use the standard logic for finding open attendance
                checkin = person._last_open_checkin(zone.id)
                if checkin:
                    checkin.with_context(from_event=True).write({
                        'check_out': fields.Datetime.now()
                    })
                elif zone.overwrite_check_out and person.last_attendance_id:
                    # Update the last attendance if zone allows it
                    person.last_attendance_id.with_context(from_event=True).write({
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
