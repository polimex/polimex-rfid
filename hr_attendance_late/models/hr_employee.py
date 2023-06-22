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
        inverse_name='employee_id'
    )

    @api.model
    def _total_time(self, time_ranges):
        return sum((end - start).total_seconds() for start, end in time_ranges)

    @api.model
    def _intersection_time(self, time_ranges1, time_ranges2):
        # intersection = [(max(start1, start2), min(end1, end2)) for start1, end1 in time_ranges1 for start2, end2 in
        #                 time_ranges2 if end1 and end2 and end1 > start2 and end2 > start1]
        intersection = [(max(start1, start2), min(end1, end2))
                        for start1, end1 in time_ranges1
                        for start2, end2 in time_ranges2
                        if end1 and end2 and start1 <= end2 and start2 <= end1]
        return intersection

    def update_extra_attendance_data(self, from_datetime, to_datetime=None, overwrite_existing=False):
        def line_to_tz_datetime(for_date, line, tz):
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

                attendance_ranges = self.env['hr.attendance'].search(
                    [('employee_id', '=', e.id),
                     ('check_in', '>=', current_date),
                     ('check_in', '<', current_date + timedelta(days=1)),
                     '|',
                     ('check_out', '<', current_date + timedelta(days=1)),
                     ('check_out', '=', False),
                     ], order='check_in').mapped(
                    lambda r: (r.check_in, r.check_out))

                if not attendance_ranges:
                    if overwrite_existing and attendance_extra_id:
                        attendance_extra_id.unlink()
                    current_date += timedelta(days=1)
                    continue

                work_time_ranges = [line_to_tz_datetime(current_date, line, tz) for line in
                                    e.resource_calendar_id.attendance_ids if
                                    line.dayofweek == str(current_date.weekday())]
                shift_number = None
                if e.resource_calendar_id.daily_ranges_are_shifts:
                    shift_intersections = [self._total_time(self._intersection_time([wr], attendance_ranges)) for
                                           wr in work_time_ranges]
                    max_shift_time = max(shift_intersections)
                    shift_number = shift_intersections.index(max_shift_time)
                    work_time_ranges = [work_time_ranges[shift_number]]

                att_extra_vals = self.get_work_time_details(
                    for_date=current_date,
                    work_time_ranges=work_time_ranges,
                    attendance_ranges=attendance_ranges,
                    day_period=convert_day_period_to_utc((time(6, 0), time(22, 0)), tz)
                )
                if shift_number is not None:
                    att_extra_vals['shift_number'] = shift_number + 1
                # if att_extra_vals and (att_extra_vals.get('theoretical_work_time',0.0) > 0 or att_extra_vals.get('extra_time',0.0) > 0):
                if att_extra_vals and (
                        sum(att_extra_vals.values()) - att_extra_vals.get('theoretical_work_time', 0.0)) > 0:
                    if e.department_id.ignore_early_come_time >= att_extra_vals['early_come_time']:
                        att_extra_vals['early_come_time'] = 0
                    if e.department_id.ignore_late_time >= att_extra_vals['late_time']:
                        att_extra_vals['actual_work_time'] += att_extra_vals['late_time']
                        att_extra_vals['actual_work_time_day'] += att_extra_vals['late_time']
                        att_extra_vals['late_time'] = 0
                    if e.department_id.ignore_early_leave_time >= att_extra_vals['early_leave_time']:
                        att_extra_vals['actual_work_time'] += att_extra_vals['early_leave_time']
                        att_extra_vals['actual_work_time_day'] += att_extra_vals['early_leave_time']
                        att_extra_vals['early_leave_time'] = 0
                    if e.department_id.ignore_overtime >= att_extra_vals['overtime']:
                        att_extra_vals['overtime'] = 0
                    if e.department_id.ignore_extra_time >= att_extra_vals['extra_time']:
                        att_extra_vals['extra_time'] = 0

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

        def day_time_intersection():
            return [
                (datetime.combine(for_date - timedelta(days=1), day_period[0]),
                 datetime.combine(for_date - timedelta(days=1), day_period[1])),
                (datetime.combine(for_date, day_period[0]), datetime.combine(for_date, day_period[1])),
                (datetime.combine(for_date + timedelta(days=1), day_period[0]),
                 datetime.combine(for_date + timedelta(days=1), day_period[1])),
            ]

        def day_time(time_ranges):
            if not time_ranges:
                return 0
            return self._total_time(self._intersection_time(time_ranges, day_time_intersection()))

        def early_time(work_time_ranges, attendance_ranges):
            if not attendance_ranges or not work_time_ranges:
                return 0

            first_attendance, first_work = attendance_ranges[0][0], work_time_ranges[0][0]
            return max(0, (first_work - first_attendance).total_seconds())

        def late_time(work_time_ranges, attendance_ranges):
            if not attendance_ranges or not work_time_ranges:
                return 0
            first_attendance, first_work = attendance_ranges[0][0], work_time_ranges[0][0]
            return max(0, (first_attendance - first_work).total_seconds())

        def early_leave_time(work_time_ranges, attendance_ranges):
            attendance_ranges = [range for range in attendance_ranges if range[1]]
            if not attendance_ranges:
                return 0
            last_attendance, last_work = (attendance_ranges[-1][1] or attendance_ranges[-1][0]), work_time_ranges[-1][1]
            return max(0, (last_work - last_attendance).total_seconds())

        def overtime(work_time_ranges, attendance_ranges):
            attendance_ranges = [range for range in attendance_ranges if range[1]]
            if not work_time_ranges or not attendance_ranges:
                return 0
            overtime_intersec = [(attendance_ranges[-1][1], attendance_ranges[-1][1] + timedelta(days=1))]
            overtime_ranges = self._intersection_time(attendance_ranges, overtime_intersec)
            return self._total_time(overtime_ranges)

        def overtime_night(work_time_ranges, attendance_ranges):
            attendance_ranges = [range for range in attendance_ranges if range[1]]
            if not work_time_ranges or not attendance_ranges:
                return 0
            overtime_intersec = [(attendance_ranges[-1][1], attendance_ranges[-1][1] + timedelta(days=1))]
            overtime_ranges = self._intersection_time(attendance_ranges, overtime_intersec)
            overtime_day_ranges = self._intersection_time(overtime_ranges, day_time_intersection())
            return self._total_time(overtime_ranges) - self._total_time(overtime_day_ranges)

        def extra_time(work_time_ranges, attendance_ranges):
            attendance_ranges = [range for range in attendance_ranges if range[1]]
            if not work_time_ranges and attendance_ranges:
                return self._total_time(attendance_ranges)
            return 0

        def extra_night(work_time_ranges, attendance_ranges):
            attendance_ranges = [range for range in attendance_ranges if range[1]]
            if not work_time_ranges and attendance_ranges:
                extra_day_intersec = self._intersection_time(attendance_ranges, day_time_intersection())
                extra_day_time = self._total_time(extra_day_intersec)
                return extra_time(work_time_ranges, attendance_ranges) - extra_day_time
            else:
                return 0

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
        debug_msg += 'Daly period:\n'
        debug_msg += f"{day_period[0].strftime('%H:%M')} - {day_period[1].strftime('%H:%M')}" + '\n'
        _logger.debug(debug_msg)
        # print(debug_msg)

        theoretical_work_time = self._total_time(work_time_ranges)
        extra_time_value = extra_time(work_time_ranges, attendance_ranges)
        extra_night_time = extra_night(work_time_ranges, attendance_ranges)

        if extra_time_value > 0:
            early_come_time = 0
            late_time_value = 0
            early_leave_time_value = 0
            overtime_value = 0
            overtime_night_time = 0
        else:
            early_come_time = early_time(work_time_ranges, attendance_ranges)
            late_time_value = late_time(work_time_ranges, attendance_ranges)
            early_leave_time_value = early_leave_time(work_time_ranges, attendance_ranges)
            overtime_value = overtime(work_time_ranges, attendance_ranges)
            overtime_night_time = overtime_night(work_time_ranges, attendance_ranges)

        list_of_intersection = self._intersection_time(work_time_ranges, attendance_ranges)
        actual_work_time = self._total_time(list_of_intersection)
        actual_work_time_day = day_time(list_of_intersection)
        actual_work_time_night = actual_work_time - actual_work_time_day
        # actual_work_time_night = night_time(list_of_intersection)

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

        debug_msg = ''
        for key, value in data.items():
            debug_msg += f"{key.replace('_', ' ').title()}: {value:.2f} hours" + '\n'
        debug_msg += '-----------------------------------------------------------\n'
        _logger.debug(debug_msg)
        # print(debug_msg)

        assert all(time >= 0 for time in
                   [theoretical_work_time, actual_work_time, actual_work_time_day, actual_work_time_night,
                    early_come_time, late_time_value, early_leave_time_value, overtime_value,
                    extra_time_value]), "Negative time found"
        assert actual_work_time == actual_work_time_day + actual_work_time_night, "Total actual work time doesn't match with day and night work time"
        if extra_time_value > 0:
            assert all(time == 0 for time in [early_come_time, late_time_value, early_leave_time_value,
                                              overtime_value]), "Extra time found but other times are not zero"

        return data
