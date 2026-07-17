# -*- coding: utf-8 -*-
from dateutil.rrule import rrule, DAILY

from odoo import api, fields, models
from datetime import datetime, timedelta, time, date
from pytz import timezone, UTC
import logging

from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

# Guard flag + tuning constants for the demo attendance generator, so every
# fresh demo DB renders the same working-time / labour-cost dashboards and a
# demo reload never duplicates records. The per-day deviations are derived
# deterministically from (employee index, day offset), so no RNG is needed.
DEMO_ATT_FLAG = 'hr_attendance_late.demo_generated'
DEMO_ATT_EMPLOYEE_LIMIT = 10
DEMO_ATT_DAYS = 30


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = 'hr.employee'

    attendance_extra_ids = fields.One2many(
        comodel_name='hr.attendance.extra',
        inverse_name='employee_id',
        groups='hr_attendance.group_hr_attendance_officer',
        help="Daily roll-up records computed for this employee by the Recompute Extra Attendance wizard or the nightly cron — late minutes, overtime, extra time per working day.",
    )

    @api.model
    def _total_time(self, time_ranges):
        """Calculate total time from a list of time ranges.
        
        :param time_ranges: List of tuples (start_datetime, end_datetime)
        :return: Total seconds covered by all time ranges
        """
        return sum((end - start).total_seconds() for start, end in time_ranges)

    @api.model
    def _intersection_time(self, time_ranges1, time_ranges2):
        """Find intersections between two lists of time ranges.
        
        :param time_ranges1: First list of time ranges
        :param time_ranges2: Second list of time ranges
        :return: List of intersecting time ranges
        """
        intersection = [(max(start1, start2), min(end1, end2))
                        for start1, end1 in time_ranges1
                        for start2, end2 in time_ranges2
                        if end1 and end2 and start1 <= end2 and start2 <= end1]
        return intersection

    def update_extra_attendance_data(self, from_datetime, to_datetime=None, overwrite_existing=False):
        """Update attendance extra records for employees in date range.
        
        This method calculates additional attendance metrics like late time,
        early leave, overtime, etc. based on attendance records and work schedules.
        
        :param from_datetime: Start date for calculation
        :param to_datetime: End date for calculation (defaults to from_datetime)
        :param overwrite_existing: Whether to recalculate existing records
        """
        def line_to_tz_datetime(for_date, line, tz):
            """Convert calendar attendance line to UTC datetime range."""
            ht = line.hour_to
            dt = for_date
            if float_compare(ht, 24.00, 2) == 0:
                ht = 0.0
                dt = for_date + timedelta(days=1)
            return (
                tz.localize(
                    datetime.combine(for_date,
                                     time(hour=int(line.hour_from),
                                          minute=int((line.hour_from % 1) * 60)))).astimezone(UTC).replace(tzinfo=None),
                tz.localize(
                    datetime.combine(dt,
                                     time(hour=int(ht),
                                          minute=int((ht % 1) * 60)))).astimezone(UTC).replace(tzinfo=None)
            )

        def convert_day_period_to_utc(day_period, tz):
            """Convert local day/night period times to UTC."""
            start_time_local = datetime.combine(date.today(), day_period[0])
            end_time_local = datetime.combine(date.today(), day_period[1])

            start_time_utc = tz.localize(start_time_local).astimezone(UTC)
            end_time_utc = tz.localize(end_time_local).astimezone(UTC)

            day_period_utc = (start_time_utc.time(), end_time_utc.time())
            return day_period_utc

        to_datetime = to_datetime or from_datetime
        for e in self:
            _logger.info('Attendance extra calculation for %s' % e.name)
            current_date = from_datetime
            tz = timezone(e.resource_calendar_id.tz) if e.resource_calendar_id.tz else UTC
            while current_date <= to_datetime:
                attendance_extra_id = self.env['hr.attendance.extra'].sudo().search([
                    ('employee_id', '=', e.id),
                    ('for_date', '=', current_date),
                ])
                if not overwrite_existing and attendance_extra_id:
                    current_date += timedelta(days=1)
                    continue

                # Get attendance records that affect the current date
                # Include records that:
                # 1. Start on current date, OR
                # 2. Start before current date but end on/after current date (night shifts)
                current_date_start = datetime.combine(current_date, datetime.min.time())
                current_date_end = datetime.combine(current_date, datetime.max.time())
                
                attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', e.id),
                    '|',
                    # Records starting on current date
                    '&',
                    ('check_in', '>=', current_date_start),
                    ('check_in', '<=', current_date_end),
                    # Records from previous days that extend into current date
                    '&',
                    ('check_in', '<', current_date_start),
                    '|',
                    ('check_out', '>=', current_date_start),
                    ('check_out', '=', False)
                ], order='check_in')
                
                # Process attendances, including those without check_out
                attendance_ranges = []
                now = fields.Datetime.now()
                
                for att in attendances:
                    check_in = att.check_in
                    if att.check_out:
                        # Normal case - has check_out
                        check_out = att.check_out
                        # Validate check_out is after check_in
                        if check_out < check_in:
                            _logger.warning('Invalid attendance found: check_out (%s) before check_in (%s) for %s on %s. Skipping.',
                                          check_out.strftime('%H:%M'), check_in.strftime('%H:%M'), 
                                          e.name, current_date.strftime('%Y-%m-%d'))
                            continue  # Skip this invalid record
                    else:
                        # Missing check_out - apply zone rules or use context time
                        # Context 'attendance_calc_time' can be used for testing
                        calc_time = self.env.context.get('attendance_calc_time', now)
                        
                        # Check if we have zone configuration (from hr_rfid module)
                        zone = getattr(att, 'in_zone_id', None) if hasattr(att, 'in_zone_id') else None
                        if zone and hasattr(zone, 'max_time_in_zone') and zone.max_time_in_zone > 0:
                            max_duration = timedelta(hours=zone.max_time_in_zone)
                            time_in_zone = calc_time - check_in
                            if time_in_zone > max_duration:
                                # Auto-close with configured duration when max time exceeded
                                auto_close_hours = getattr(zone, 'auto_close_time_for_zone', 8.0)
                                check_out = check_in + timedelta(hours=auto_close_hours)
                                _logger.info('Auto-closing attendance for %s on %s after %.1f hours (zone: %s)',
                                            e.name, current_date.strftime('%Y-%m-%d'), 
                                            auto_close_hours, zone.name)
                            else:
                                # Still within max time - use calculation time
                                check_out = calc_time
                        else:
                            # No zone or no max time configured - use calculation time
                            check_out = calc_time
                            if (calc_time - check_in) > timedelta(hours=24):
                                _logger.warning('Attendance without check_out for %s exceeds 24 hours on %s',
                                               e.name, current_date.strftime('%Y-%m-%d'))
                    
                    attendance_ranges.append((check_in, check_out))

                # Scheduled work ranges for the day (empty on a non-working day).
                # Computed once here and reused both for the absence-row
                # theoretical time below and the presence calculation further down.
                work_time_ranges = [line_to_tz_datetime(current_date, line, tz) for line in
                                    e.resource_calendar_id.attendance_ids if
                                    line.dayofweek == str(current_date.weekday())]

                # Check if we have any attendance data to process
                if not attendance_ranges:
                    # No badge at all on a SCHEDULED working day = an absence
                    # (no-show). Record it as a measurement row with only the
                    # planned time filled in, so absence reporting ("who was
                    # missing", absence rate, absences per department) can be
                    # counted directly: theoretical_work_time > 0 and
                    # actual_work_time = 0. Non-working days stay rowless.
                    planned_time = (self._total_time(work_time_ranges) / 3600.0) if work_time_ranges else 0.0
                    if planned_time > 0 and current_date < fields.Date.today():
                        absence_vals = {
                            'theoretical_work_time': planned_time,
                            'actual_work_time': 0, 'actual_work_time_day': 0,
                            'actual_work_time_night': 0, 'late_time': 0,
                            'early_leave_time': 0, 'early_come_time': 0,
                            'overtime': 0, 'overtime_night': 0,
                            'extra_time': 0, 'extra_night': 0,
                            'first_in': 0, 'last_out': 0,
                        }
                        if attendance_extra_id:
                            attendance_extra_id.sudo().write(absence_vals)
                        else:
                            absence_vals.update({'employee_id': e.id,
                                                 'for_date': current_date})
                            self.env['hr.attendance.extra'].sudo().create(absence_vals)
                    elif overwrite_existing and attendance_extra_id:
                        attendance_extra_id.unlink()
                    current_date += timedelta(days=1)
                    continue

                shift_number = None
                # Only pick a shift when the day actually has scheduled ranges.
                # On a non-working day (empty work_time_ranges) an attendance is
                # extra/rest-day work: leave the ranges empty so the non-working
                # day path below computes extra_time. Guarding here also avoids
                # max([]) raising on shift calendars when someone badges on a day
                # off - which would otherwise crash attendance creation via the
                # create hook.
                if e.resource_calendar_id.daily_ranges_are_shifts and work_time_ranges:
                    # Handle shift-based schedules
                    shift_intersections = [self._total_time(self._intersection_time([wr], attendance_ranges)) for
                                           wr in work_time_ranges]
                    max_shift_time = max(shift_intersections)
                    shift_number = shift_intersections.index(max_shift_time)
                    work_time_ranges = [work_time_ranges[shift_number]]
                
                # Calculate attendance metrics with improved error handling
                try:
                    att_extra_vals = self.get_work_time_details(
                        for_date=current_date,
                        work_time_ranges=work_time_ranges,
                        attendance_ranges=attendance_ranges,
                        day_period=convert_day_period_to_utc((time(6, 0), time(22, 0)), tz)
                    )
                except Exception as ex:
                    _logger.error('ERROR in Attendance extra calculation for %s on %s: %s', 
                                  e.name, current_date.strftime('%Y-%m-%d'), str(ex), exc_info=True)
                    current_date += timedelta(days=1)
                    continue

                if shift_number is not None:
                    att_extra_vals['shift_number'] = shift_number + 1

                # Cap theoretical_work_time at calendar hours_per_day if exceeds 20 hours
                # This prevents errors from misconfigured calendars or overlapping attendance periods
                if att_extra_vals.get('theoretical_work_time', None) is not None and att_extra_vals['theoretical_work_time'] > 20:
                    att_extra_vals['theoretical_work_time'] = min(att_extra_vals['theoretical_work_time'], e.resource_calendar_id.hours_per_day)

                # Apply department tolerance settings
                if att_extra_vals and (
                        sum(att_extra_vals.values()) - att_extra_vals.get('theoretical_work_time', 0.0)) > 0:
                    if e.department_id.ignore_early_come_time >= att_extra_vals['early_come_time']:
                        att_extra_vals['early_come_time'] = 0
                    if e.department_id.ignore_late_time >= att_extra_vals['late_time']:
                        # If late time is within tolerance, add it to actual work time
                        att_extra_vals['actual_work_time'] += att_extra_vals['late_time']
                        att_extra_vals['actual_work_time_day'] += att_extra_vals['late_time']
                        att_extra_vals['late_time'] = 0
                    if e.department_id.ignore_early_leave_time >= att_extra_vals['early_leave_time']:
                        # If early leave is within tolerance, add it to actual work time
                        att_extra_vals['actual_work_time'] += att_extra_vals['early_leave_time']
                        att_extra_vals['actual_work_time_day'] += att_extra_vals['early_leave_time']
                        att_extra_vals['early_leave_time'] = 0
                    if e.department_id.ignore_overtime >= att_extra_vals['overtime']:
                        att_extra_vals['overtime'] = 0
                    if e.department_id.ignore_extra_time >= att_extra_vals['extra_time']:
                        att_extra_vals['extra_time'] = 0

                    # First badge-in / last badge-out of the day as local-time
                    # hour fractions (e.g. 8.25 = 08:15) - the "came at / left
                    # at" columns clients expect on working-time reports. Added
                    # AFTER the record-creation gate above so they never change
                    # which days produce a record.
                    first_in_dt = UTC.localize(min(r[0] for r in attendance_ranges)).astimezone(tz)
                    last_out_dt = UTC.localize(max(r[1] for r in attendance_ranges)).astimezone(tz)
                    att_extra_vals['first_in'] = (first_in_dt.hour + first_in_dt.minute / 60.0
                                                  + first_in_dt.second / 3600.0)
                    att_extra_vals['last_out'] = (last_out_dt.hour + last_out_dt.minute / 60.0
                                                  + last_out_dt.second / 3600.0)
                    # Create or update attendance extra record
                    if attendance_extra_id:
                        attendance_extra_id.sudo().write(att_extra_vals)
                    else:
                        att_extra_vals.update({
                            'employee_id': e.id,
                            'for_date': current_date
                        })
                        self.env['hr.attendance.extra'].sudo().create(att_extra_vals)
                current_date += timedelta(days=1)

    @api.model
    def get_work_time_details(self, for_date, work_time_ranges, attendance_ranges,
                              day_period=(time(6, 0), time(22, 0))):
        """Calculate detailed work time metrics for a specific date.
        
        This method analyzes attendance records against work schedules to calculate:
        - Theoretical vs actual work time
        - Late arrivals and early departures
        - Overtime and extra time
        - Day vs night time split
        
        :param for_date: Date to calculate for
        :param work_time_ranges: List of scheduled work periods
        :param attendance_ranges: List of actual attendance periods
        :param day_period: Time range considered as "day" (vs "night")
        :return: Dictionary with calculated time metrics in hours
        """

        def day_time_intersection():
            """Get day period ranges for previous, current and next day."""
            return [
                (datetime.combine(for_date - timedelta(days=1), day_period[0]),
                 datetime.combine(for_date - timedelta(days=1), day_period[1])),
                (datetime.combine(for_date, day_period[0]), datetime.combine(for_date, day_period[1])),
                (datetime.combine(for_date + timedelta(days=1), day_period[0]),
                 datetime.combine(for_date + timedelta(days=1), day_period[1])),
            ]

        def day_time(time_ranges):
            """Calculate time during day period from time ranges."""
            if not time_ranges:
                return 0
            return self._total_time(self._intersection_time(time_ranges, day_time_intersection()))

        def early_time(work_time_ranges, attendance_ranges):
            """Calculate early arrival time (arrived before work start)."""
            if not attendance_ranges or not work_time_ranges:
                return 0

            first_attendance, first_work = attendance_ranges[0][0], work_time_ranges[0][0]
            return max(0, (first_work - first_attendance).total_seconds())

        def late_time(work_time_ranges, attendance_ranges):
            """Calculate late arrival time (arrived after work start)."""
            if not attendance_ranges or not work_time_ranges:
                return 0
            first_attendance, first_work = attendance_ranges[0][0], work_time_ranges[0][0]
            return max(0, (first_attendance - first_work).total_seconds())

        def early_leave_time(work_time_ranges, attendance_ranges):
            """Calculate early leave time (left before work end)."""
            # Filter out attendances without check_out
            attendance_ranges = [range for range in attendance_ranges if range[1]]
            if not attendance_ranges:
                return 0
            last_attendance, last_work = (attendance_ranges[-1][1] or attendance_ranges[-1][0]), work_time_ranges[-1][1]
            return max(0, (last_work - last_attendance).total_seconds())

        def overtime(work_time_ranges, attendance_ranges):
            """Calculate overtime (work after scheduled end)."""
            # Filter out attendances without check_out
            attendance_ranges = [range for range in attendance_ranges if range[1]]
            if not work_time_ranges or not attendance_ranges:
                return 0
            overtime_intersec = [(work_time_ranges[-1][1], work_time_ranges[-1][1] + timedelta(days=1))]
            overtime_ranges = self._intersection_time(attendance_ranges, overtime_intersec)
            return self._total_time(overtime_ranges)

        def overtime_night(work_time_ranges, attendance_ranges):
            """Calculate night portion of overtime."""
            # Filter out attendances without check_out
            attendance_ranges = [range for range in attendance_ranges if range[1]]
            if not work_time_ranges or not attendance_ranges:
                return 0
            # Overtime = presence AFTER the SCHEDULED end of the day. The
            # window must open at the schedule end (work_time_ranges), not at
            # the end of the attendance itself - intersecting the attendance
            # with a window that starts where the attendance ends is always
            # empty, which made night overtime permanently zero.
            overtime_intersec = [(work_time_ranges[-1][1], work_time_ranges[-1][1] + timedelta(days=1))]
            overtime_ranges = self._intersection_time(attendance_ranges, overtime_intersec)
            overtime_day_ranges = self._intersection_time(overtime_ranges, day_time_intersection())
            return self._total_time(overtime_ranges) - self._total_time(overtime_day_ranges)

        def extra_time(work_time_ranges, attendance_ranges):
            """Calculate extra time (attendance on non-working day)."""
            # Filter out attendances without check_out
            attendance_ranges = [range for range in attendance_ranges if range[1]]
            if not work_time_ranges and attendance_ranges:
                return self._total_time(attendance_ranges)
            return 0

        def extra_night(work_time_ranges, attendance_ranges):
            """Calculate night portion of extra time."""
            # Filter out attendances without check_out
            attendance_ranges = [range for range in attendance_ranges if range[1]]
            if not work_time_ranges and attendance_ranges:
                extra_day_intersec = self._intersection_time(attendance_ranges, day_time_intersection())
                extra_day_time = self._total_time(extra_day_intersec)
                return extra_time(work_time_ranges, attendance_ranges) - extra_day_time
            else:
                return 0

        # Log debug information
        debug_msg = ''
        debug_msg += 'Work Ranges:\n'
        for start_time, end_time in work_time_ranges:
            formatted_start_time = start_time.strftime('%Y-%m-%d %H:%M')
            formatted_end_time = end_time.strftime('%Y-%m-%d %H:%M') if end_time else "-"
            debug_msg += f'{formatted_start_time} - {formatted_end_time}' + '\n'
        debug_msg += 'Attendance Ranges:\n'
        for start_time, end_time in attendance_ranges:
            formatted_start_time = start_time.strftime('%Y-%m-%d %H:%M')
            formatted_end_time = end_time.strftime('%Y-%m-%d %H:%M') if end_time else "-"
            debug_msg += f'{formatted_start_time} - {formatted_end_time}' + '\n'
        debug_msg += 'Daily period:\n'
        debug_msg += f"{day_period[0].strftime('%H:%M')} - {day_period[1].strftime('%H:%M')}" + '\n'
        _logger.debug(debug_msg)

        # Calculate all time metrics
        theoretical_work_time = self._total_time(work_time_ranges)
        extra_time_value = extra_time(work_time_ranges, attendance_ranges)
        extra_night_time = extra_night(work_time_ranges, attendance_ranges)

        if extra_time_value > 0:
            # On non-working days, no early/late/overtime calculations
            early_come_time = 0
            late_time_value = 0
            early_leave_time_value = 0
            overtime_value = 0
            overtime_night_time = 0
        else:
            # Calculate deviations from schedule
            early_come_time = early_time(work_time_ranges, attendance_ranges)
            late_time_value = late_time(work_time_ranges, attendance_ranges)
            early_leave_time_value = early_leave_time(work_time_ranges, attendance_ranges)
            overtime_value = overtime(work_time_ranges, attendance_ranges)
            overtime_night_time = overtime_night(work_time_ranges, attendance_ranges)

        # Calculate actual work time
        list_of_intersection = self._intersection_time(work_time_ranges, attendance_ranges)
        actual_work_time = self._total_time(list_of_intersection)
        actual_work_time_day = day_time(list_of_intersection)
        actual_work_time_night = actual_work_time - actual_work_time_day

        # Prepare return data (convert seconds to hours)
        data = {
            "theoretical_work_time": theoretical_work_time / 3600,
            "actual_work_time": actual_work_time / 3600,
            "actual_work_time_day": actual_work_time_day / 3600,
            "actual_work_time_night": actual_work_time_night / 3600,
            "early_come_time": early_come_time / 3600,
            "late_time": late_time_value / 3600,
            "early_leave_time": early_leave_time_value / 3600,
            "overtime": overtime_value / 3600,
            "overtime_night": overtime_night_time / 3600,
            "extra_time": extra_time_value / 3600,
            "extra_night": extra_night_time / 3600
        }

        # Log calculated values
        debug_msg = ''
        for key, value in data.items():
            debug_msg += f"{key.replace('_', ' ').title()}: {value:.2f} hours" + '\n'
        debug_msg += '-----------------------------------------------------------\n'
        _logger.debug(debug_msg)

        # Validate calculated times before returning
        self._validate_time_calculations(
            theoretical_work_time, actual_work_time, actual_work_time_day, 
            actual_work_time_night, early_come_time, late_time_value,
            early_leave_time_value, overtime_value, extra_time_value
        )

        return data
    
    def _validate_time_calculations(self, theoretical_work_time, actual_work_time, 
                                   actual_work_time_day, actual_work_time_night,
                                   early_come_time, late_time_value, early_leave_time_value,
                                   overtime_value, extra_time_value):
        """Validate calculated time values for consistency.
        
        This method ensures all calculated times are valid:
        - No negative values
        - Day + night time equals total time
        - Extra time calculations are consistent
        
        :raises ValueError: If validation fails
        """
        time_values = {
            'theoretical_work_time': theoretical_work_time,
            'actual_work_time': actual_work_time,
            'actual_work_time_day': actual_work_time_day,
            'actual_work_time_night': actual_work_time_night,
            'early_come_time': early_come_time,
            'late_time': late_time_value,
            'early_leave_time': early_leave_time_value,
            'overtime': overtime_value,
            'extra_time': extra_time_value
        }
        
        # Check for negative times
        negative_times = [(k, v) for k, v in time_values.items() if v < 0]
        if negative_times:
            error_msg = "Negative time values found: " + ", ".join([f"{k}={v/3600:.2f}h" for k, v in negative_times])
            _logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Check total work time consistency with improved tolerance for floating point errors
        time_diff = abs(actual_work_time - (actual_work_time_day + actual_work_time_night))
        if time_diff > 0.01:  # Allow 0.01 second difference for floating point errors
            error_msg = (f"Total actual work time ({actual_work_time/3600:.2f}h) doesn't match "
                        f"day ({actual_work_time_day/3600:.2f}h) + night ({actual_work_time_night/3600:.2f}h) work time. "
                        f"Difference: {time_diff} seconds")
            _logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Check extra time consistency
        if extra_time_value > 0:
            # When working on non-scheduled day, other deviation times should be zero
            non_zero_times = [(k, v) for k, v in {
                'early_come_time': early_come_time,
                'late_time': late_time_value,
                'early_leave_time': early_leave_time_value,
                'overtime': overtime_value
            }.items() if v > 0]
            if non_zero_times:
                warning_msg = f"Extra time found ({extra_time_value/3600:.2f}h) but other times are not zero: " + ", ".join([f"{k}={v/3600:.2f}h" for k, v in non_zero_times])
                _logger.warning(warning_msg)

    # ------------------------------------------------------------------
    # Demo data generation (dashboards)
    # ------------------------------------------------------------------
    @api.model
    def _demo_select_employees(self):
        """Deterministic set of demo employees with a work schedule + department.

        Shared entry point so the working-time and labour-cost dashboards are
        populated for the same people. Named core demo employees come first for
        continuity with the hand-authored showcase, then the list is topped up
        from the main company. Only employees that have both a resource calendar
        (for a theoretical schedule) and a department (for the department
        breakdown) qualify.
        """
        company = self.env.ref('base.main_company', raise_if_not_found=False)
        employees = self.env['hr.employee']
        for emp_xml in ('hr.employee_admin', 'hr.employee_al',
                        'hr.employee_qdp', 'hr.employee_ngh'):
            emp = self.env.ref(emp_xml, raise_if_not_found=False)
            if emp:
                employees |= emp
        employees = employees.filtered(
            lambda e: e.resource_calendar_id and e.department_id)
        domain = [('resource_calendar_id', '!=', False),
                  ('department_id', '!=', False),
                  ('id', 'not in', employees.ids)]
        if company:
            domain.append(('company_id', '=', company.id))
        top_up = self.env['hr.employee'].search(
            domain, limit=max(0, DEMO_ATT_EMPLOYEE_LIMIT - len(employees)),
            order='id')
        return employees | top_up

    def _demo_day_window(self, day):
        """Scheduled work window (check-in, check-out) in naive UTC for a date.

        Derived from the employee's own resource calendar so deviations added on
        top land exactly relative to the theoretical schedule the extra-time
        computation compares against. Returns None on a non-working day (no
        calendar range for that weekday).
        """
        self.ensure_one()
        cal = self.resource_calendar_id
        tz = timezone(cal.tz) if cal.tz else UTC
        lines = cal.attendance_ids.filtered(
            lambda l: l.dayofweek == str(day.weekday()))
        if not lines:
            return None
        hour_from = min(lines.mapped('hour_from'))
        hour_to = max(lines.mapped('hour_to'))
        start_local = datetime.combine(
            day, time(int(hour_from), int((hour_from % 1) * 60)))
        end_day = day
        if float_compare(hour_to, 24.00, 2) >= 0:
            hour_to -= 24.00
            end_day = day + timedelta(days=1)
        end_local = datetime.combine(
            end_day, time(int(hour_to), int((hour_to % 1) * 60)))
        check_in = tz.localize(start_local).astimezone(UTC).replace(tzinfo=None)
        check_out = tz.localize(end_local).astimezone(UTC).replace(tzinfo=None)
        return check_in, check_out

    @api.model
    def _demo_generate_attendances(self):
        """Generate ~30 days of demo attendances for the working-time dashboards.

        Creates hr.attendance check-in/out pairs over the last ~30 days for a
        handful of employees across several departments, then triggers this
        module's extra-time roll-up so hr.attendance.extra (worked hours,
        overtime, late, day/night split) - and, once hr_attendace_rfid_hr_hourly_cost
        is installed, the derived cost columns - carry rich values.

        Deterministic per (employee, day) so the distribution is reproducible.
        Idempotent: an ir.config_parameter flag makes a demo reload a no-op, and
        every candidate session is overlap-checked against existing attendances
        so it never clashes with the hand-authored showcase or an open session.
        Only invoked from the demo data <function> hook.
        """
        param = self.env['ir.config_parameter'].sudo()
        if param.get_param(DEMO_ATT_FLAG):
            return

        employees = self._demo_select_employees()
        if not employees:
            return

        # Put the demo employees on a clean full-time, non-shift calendar (seeded
        # by the demo XML that calls this helper) so the generated worked-hours /
        # overtime figures are realistic and reproducible, independent of the
        # shift-mode showcase calendar. Skip if the calendar is missing.
        calendar = self.env.ref(
            'hr_attendance_late.demo_calendar_fulltime', raise_if_not_found=False)
        if calendar:
            employees.write({'resource_calendar_id': calendar.id})

        Attendance = self.env['hr.attendance']
        today = fields.Datetime.now().date()
        start_date = today - timedelta(days=DEMO_ATT_DAYS)
        vals_list = []

        for emp_index, emp in enumerate(employees):
            for day_offset in range(1, DEMO_ATT_DAYS + 1):
                day = today - timedelta(days=day_offset)
                window = emp._demo_day_window(day)
                seed = emp_index * 97 + day_offset

                if window is None:
                    # Occasional rest-day (Saturday) work for the first two
                    # employees -> drives extra_time and the rest-day cost tier.
                    if (emp.resource_calendar_id and emp_index < 2
                            and day.weekday() == 5 and day_offset % 2 == 0):
                        tz = (timezone(emp.resource_calendar_id.tz)
                              if emp.resource_calendar_id.tz else UTC)
                        check_in = tz.localize(datetime.combine(
                            day, time(9, 0))).astimezone(UTC).replace(tzinfo=None)
                        check_out = tz.localize(datetime.combine(
                            day, time(14, 0))).astimezone(UTC).replace(tzinfo=None)
                    else:
                        continue
                else:
                    check_in, check_out = window
                    if seed % 5 == 0:
                        # Late arrival (20-59 min, above the 5 min tolerance).
                        check_in += timedelta(minutes=20 + (seed % 40))
                    elif seed % 6 == 0:
                        if emp_index == 0:
                            # Long shift into the night window (22:00-06:00) so
                            # overtime_night and the night-shift supplement appear.
                            check_out += timedelta(hours=6, minutes=15)
                        else:
                            # Daytime overtime (75-210 min, above the 15 min tol).
                            check_out += timedelta(minutes=75 + (seed % 4) * 45)
                    elif seed % 8 == 0:
                        # Early departure (30-54 min).
                        check_out -= timedelta(minutes=30 + (seed % 25))

                if check_out <= check_in:
                    continue

                # Never clash with an existing (or still-open) attendance.
                overlap = Attendance.search([
                    ('employee_id', '=', emp.id),
                    ('check_in', '<', check_out),
                    '|', ('check_out', '=', False),
                    ('check_out', '>', check_in),
                ], limit=1)
                if overlap:
                    continue

                vals_list.append({
                    'employee_id': emp.id,
                    'check_in': check_in,
                    'check_out': check_out,
                })

        if vals_list:
            # migration_mode defers the per-create extra roll-up; recompute once
            # per employee over the whole window instead (fewer passes).
            Attendance.with_context(migration_mode=True).create(vals_list)
            for emp in employees:
                emp.update_extra_attendance_data(
                    from_datetime=start_date,
                    to_datetime=today - timedelta(days=1),
                    overwrite_existing=True,
                )
        param.set_param(DEMO_ATT_FLAG, '1')
        _logger.info(
            'Demo attendances generated: %d sessions for %d employees over %d days',
            len(vals_list), len(employees), DEMO_ATT_DAYS)