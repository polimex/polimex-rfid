# -*- coding: utf-8 -*-
from dateutil.rrule import rrule, DAILY

from odoo import api, fields, models
from datetime import datetime, timedelta, time, date
from pytz import timezone, UTC
import logging

from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    attendance_extra_ids = fields.One2many(
        comodel_name='hr.attendance.extra',
        inverse_name='employee_id',
        groups='hr_attendance.group_hr_attendance_officer',
        help="Daily roll-up records computed for this employee by the Recompute Extra Attendance wizard or the nightly cron - late minutes, overtime, extra time per working day.",
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

                # Check if we have any attendance data to process
                if not attendance_ranges:
                    if overwrite_existing and attendance_extra_id:
                        attendance_extra_id.unlink()
                    current_date += timedelta(days=1)
                    continue

                # Get work schedule for the day
                work_time_ranges = [line_to_tz_datetime(current_date, line, tz) for line in
                                    e.resource_calendar_id.attendance_ids if
                                    line.dayofweek == str(current_date.weekday())]
                shift_number = None
                if e.resource_calendar_id.daily_ranges_are_shifts:
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
            overtime_intersec = [(attendance_ranges[-1][1], attendance_ranges[-1][1] + timedelta(days=1))]
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
