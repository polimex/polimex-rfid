# -*- coding: utf-8 -*-
import logging

from datetime import timedelta

from odoo import models, fields, _

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

    # The hours that used to live here - Maximum Hours in Zone, Auto-close
    # Worked Hours, Delete if Late More Than - are gone. The first two asked
    # the same question as Settings -> Attendances -> Automatic Check-Out and
    # answered it with a different number (12 against core's 10 on the
    # installation this came from), and the third was never read by anything
    # at all: an operator could set it and nothing happened. The migration
    # carries what the first two said onto the company.

    # TODO Need to added .with_context(no_validity_check=True) for attendance management!!!
    def person_entered(self, person, event):
        is_employee = isinstance(person, type(self.env['hr.employee']))
        if not is_employee:
            return super(HrRfidZone, self).person_entered(person, event)

        # Callers pass a bare False when they act on their own clock rather
        # than on a passage; the empty recordset behaves the same in every
        # test below and lets the reason be recorded without a guard.
        event = event or self.env['hr.rfid.event.user']

        for zone in self.filtered(lambda z: z.attendance):
            if not zone._check_employee_permit(person):
                event._mark_no_attendance('not_tracked_here')
                continue
            check = person._last_open_checkin(
                zone.id, before_dt=event.event_time or None)

            if check and not zone.overwrite_check_in:
                # Already checked in and this zone keeps the first entry -
                # nothing to do, but the passage must not read as an
                # unexplained blank in the operator's list.
                event._mark_no_attendance('already_inside')
                continue

            if check:
                # This zone moves the check-in to the newer entry. It only
                # does so when a LATER, already closed attendance says the
                # open one started too early; otherwise the person is simply
                # inside already and nothing changes - and the passage says
                # that instead of claiming a check-in nobody made.
                if event:
                    moved_by = person.last_attendance_id
                    if moved_by.check_out and moved_by.check_out < event.event_time:
                        check.with_context(no_validity_check=True, rfid_machinery_write=True).write({
                            'check_in': event.event_time
                        })
                        event._mark_attendance('in')
                    else:
                        event._mark_no_attendance('already_inside')
                else:
                    check.with_context(no_validity_check=True, rfid_machinery_write=True).write({
                        'check_in': fields.Datetime.now()
                    })
            else:
                if event:
                    event._mark_attendance('in')
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

        # See person_entered: a missing event is the empty recordset here.
        event = event or self.env['hr.rfid.event.user']

        for zone in self.filtered(lambda z: z.attendance):
            if not zone._check_employee_permit(person):
                event._mark_no_attendance('not_tracked_here')
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
                    event._mark_attendance('out')
                    
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
                            # Only now is this passage a check-out. Saying so
                            # before the write meant every exit that reopened
                            # nothing still read as one.
                            event._mark_attendance('out')
                            last_att_id.with_context(from_event=True, no_validity_check=True).write({
                                'check_out': event.event_time
                            })
                        else:
                            _logger.warning(
                                'Cannot update check-out to %s as it would be before check-in %s',
                                event.event_time, last_att_id.check_in
                            )
                            event._mark_no_attendance('nothing_to_close')
                    else:
                        event._mark_no_attendance('nothing_to_close')
                else:
                    # An exit with nothing open, and this zone does not reopen
                    # the previous record. The commonest silent discard there is.
                    event._mark_no_attendance('nothing_to_close')
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
