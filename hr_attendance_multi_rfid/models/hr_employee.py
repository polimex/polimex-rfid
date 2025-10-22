from datetime import timedelta

from odoo import models, exceptions, _, api, fields
from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _last_open_checkin(self, zone_id=None, before_dt=None):
        """Find the last open check-in for this employee.
        
        :param zone_id: Optional zone to filter by
        :param before_dt: Optional datetime to find check-ins before this time
        :return: hr.attendance record or False
        """
        self.ensure_one()
        if zone_id is not None:
            domain = [
                ('employee_id', '=', self.id),
                ('check_out', '=', False),
                ('in_zone_id', '=', zone_id),
            ]
            if before_dt is not None:
                domain.append(('check_in', '<=', before_dt))
            _last = self.env['hr.attendance'].search(domain, limit=1)
            if _last:
                return _last
        domain = [
            ('employee_id', '=', self.id),
            ('check_out', '=', False),
        ]
        if before_dt is not None:
            domain.append(('check_in', '<', before_dt))
        return self.env['hr.attendance'].search(domain, limit=1)

    def attendance_action_change_with_date(self, action_date, zone_id=None):
        """ Check In/Check Out action with support for out-of-order events.
        
        This method handles both real-time and historical attendance events:
        - Check In: Creates a new attendance record
        - Check Out: Finds and updates the appropriate attendance record
        
        For out-of-order events:
        - Check In: Always creates new attendance (may be inserted between existing ones)
        - Check Out: Finds the correct open attendance based on event time
        
        :param action_date: The datetime of the attendance action
        :param zone_id: Optional zone ID for the attendance
        :return: The created or modified attendance record
        """
        self.ensure_one()

        # First, look for an open attendance that could be closed by this event
        # This handles out-of-order check-outs properly
        open_attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
            ('check_out', '=', False),
            ('check_in', '<', action_date)  # Check-in must be before this event
        ], order='check_in desc', limit=1)
        
        # Determine if this should be a check-out based on:
        # 1. Existence of an open attendance that started before this event
        # 2. Current attendance state (for real-time events)
        should_check_out = open_attendance and (
            self.attendance_state == 'checked_in' or 
            self.env.context.get('force_check_out', False)
        )
        
        if should_check_out:
            # Validate that check_out is after check_in
            if action_date < open_attendance.check_in:
                _logger.warning(
                    'Attempted to set check_out (%s) before check_in (%s) for employee %s. '
                    'Setting check_out to check_in + 1 minute to maintain data integrity.',
                    action_date, open_attendance.check_in, self.name
                )
                # Set check_out to check_in + 1 minute to maintain valid record
                action_date = open_attendance.check_in + timedelta(minutes=1)
            
            # Update the attendance with proper context for validation bypass
            if self.env.context.get('no_validity_check'):
                open_attendance.with_context(no_validity_check=True).check_out = action_date
            else:
                open_attendance.check_out = action_date
            return open_attendance
        
        # For check-in or when no suitable open attendance found
        if self.attendance_state != 'checked_in' or not open_attendance:
            # Create new attendance record
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
                'in_zone_id': zone_id
            }
            
            # Use no_validity_check context for historical events to bypass constraints
            if self.env.context.get('no_validity_check'):
                return self.env['hr.attendance'].with_context(no_validity_check=True).create(vals)
            else:
                return self.env['hr.attendance'].create(vals)
        
        # If we get here, something went wrong
        raise exceptions.UserError(
            _('Cannot perform check out on %(empl_name)s, '
              'could not find corresponding check in. Your '
              'attendances have probably been modified manually '
              'by human resources.') % {'empl_name': self.name}
        )

    def recalc_attendance(self, from_date=None, to_date=None):
        """Recalculate attendance records from RFID events.
        
        This method processes RFID events to recreate attendance records,
        handling out-of-order events and various edge cases.
        
        :param from_date: Start date for recalculation (default: 30 days ago)
        :param to_date: End date for recalculation (default: today)
        """
        if from_date is None:
            from_date = fields.Date.today() - timedelta(days=30)
        to_date = to_date or fields.Date.today()
        
        # Find all zones configured for attendance
        att_zone_ids = self.env['hr.rfid.zone'].search([('attendance', "=", True)])
        doors_with_attendance = att_zone_ids.mapped('door_ids')
        readers_ids = doors_with_attendance.mapped('reader_ids')
        in_readers_ids = readers_ids.filtered(lambda r: r.reader_type == '0')
        out_readers_ids = readers_ids.filtered(lambda r: r.reader_type == '1')

        for employee_id in self:
            # Get all relevant events for this employee
            event_ids = self.env['hr.rfid.event.user'].search([
                ('employee_id', '=', employee_id.id),
                ('door_id', 'in', doors_with_attendance.mapped('id')),
                ('event_time', '>=', from_date),
                ('event_action', '=', '1')  # Only granted access events
            ], order='event_time')

            if not event_ids:  # no events for processing
                continue

            # Remove all auto-generated attendance records for the period
            # Keep manual attendance records based on attendance reasons
            auto_close_reason = False
            if self.env.company._fields.get('hr_attendance_autoclose_reason', False):
                auto_close_reason = self.env.company.hr_attendance_autoclose_reason and self.env.company.hr_attendance_autoclose_reason.id or False
            
            search_domain = [
                ('check_in', '>=', from_date),
                ('employee_id', '=', employee_id.id),
            ]
            if auto_close_reason:
                # Keep manual attendance records (those without auto-close reason)
                search_domain.append('|')
                search_domain.append(('attendance_reason_ids', '=', False))
                search_domain.append(('attendance_reason_ids', '=', auto_close_reason))
            else:
                _logger.warning('No Attendance reason module found - removing all attendance records')
            
            self.env['hr.attendance'].search(search_domain).unlink()
            
            # Get remaining manual attendance records
            manual_att_ids = self.env['hr.attendance'].search([
                ('check_in', '>=', from_date),
                ('employee_id', '=', employee_id.id),
            ])
            
            # Process events to create attendance records
            presence = [None, None]  # [check_in, check_out]
            in_zone = None
            previous_attendance_id = None
            previous_event_id = None
            
            for e in event_ids:
                # Skip events that are already recorded in manual attendance
                if manual_att_ids.filtered(lambda a: a.check_in == e.event_time or a.check_out == e.event_time):
                    continue
                
                e.in_or_out = 'no_info'
                
                # Handle check-in events (entry readers)
                if e.reader_id in in_readers_ids:
                    # Create new check-in or override existing based on zone settings
                    if not presence[0] or (presence[0] and in_zone.overwrite_check_in):
                        if presence[0] and in_zone.overwrite_check_in and previous_event_id:
                            previous_event_id.in_or_out = 'no_info'
                        presence[0] = e.event_time
                        e.in_or_out = 'in'
                        in_zone = att_zone_ids.filtered(lambda z: e.door_id in z.door_ids)
                
                # Handle check-out events (exit readers)
                if e.reader_id in out_readers_ids:
                    if presence[0]:
                        # Normal check-out for open attendance
                        presence[1] = e.event_time
                        e.in_or_out = 'out'
                    elif not presence[0] and previous_attendance_id:
                        # Out-of-order check-out - update previous attendance if allowed
                        in_zone = att_zone_ids.filtered(lambda z: e.door_id in z.door_ids)
                        if in_zone.overwrite_check_out and previous_attendance_id.check_out and (
                                e.event_time - previous_attendance_id.check_out) < timedelta(hours=8):
                            previous_attendance_id.with_context(no_validity_check=True).check_out = e.event_time
                            e.in_or_out = 'out'
                
                # Create attendance record when we have both check-in and check-out
                if all(presence):
                    previous_attendance_id = self.env['hr.attendance'].with_context(no_validity_check=True).create({
                        'check_in': presence[0],
                        'check_out': presence[1],
                        'employee_id': employee_id.id,
                        'in_zone_id': in_zone and in_zone.id,
                    })
                    presence = [None, None]
                
                previous_event_id = e

            # Handle last open attendance (check-in without check-out)
            if presence[0] and not presence[1]:
                self.env['hr.attendance'].create({
                    'check_in': presence[0],
                    'in_zone_id': in_zone and in_zone.id,
                    'employee_id': employee_id.id,
                })