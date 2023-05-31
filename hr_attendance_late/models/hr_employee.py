# -*- coding: utf-8 -*-
from dateutil.rrule import rrule, DAILY

from odoo import api, fields, models
from datetime import datetime, timedelta, time, date
from pytz import timezone, UTC
import logging

_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    attendance_extra_ids = fields.One2many(
        comodel_name='hr.attendance.extra',
        inverse_name='employee_id'
    )

    def update_extra_attendance_data(self, from_datetime, to_datetime=None):
        def line_to_tz_datetime(for_date, line, tz):
            return (
                tz.localize(
                    datetime.combine(for_date,
                                     time(hour=int(line.hour_from),
                                          minute=int((line.hour_from % 1) * 60)))).astimezone(UTC).replace(tzinfo=None),
                tz.localize(
                    datetime.combine(for_date,
                                     time(hour=int(line.hour_to),
                                          minute=int((line.hour_to % 1) * 60)))).astimezone(UTC).replace(tzinfo=None)
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
            current_date = from_datetime
            tz = timezone(e.resource_calendar_id.tz) if e.resource_calendar_id.tz else UTC
            while current_date <= to_datetime:
                work_time_ranges = [line_to_tz_datetime(current_date, line, tz) for line in
                                    e.resource_calendar_id.attendance_ids if
                                    line.dayofweek == str(current_date.weekday())]
                attendance_ranges = self.env['hr.attendance'].search(
                    [('employee_id', '=', e.id),
                     ('check_in', '>=', current_date),
                     ('check_out', '<', current_date + timedelta(days=1)),
                     ], order='check_in').mapped(lambda r: (r.check_in, r.check_out))
                attendance_extra_id = self.env['hr.attendance.extra'].sudo().search([
                    ('employee_id', '=', e.id),
                    ('for_date', '=', current_date),
                ])
                att_extra_vals = self.get_work_time_details(
                    work_time_ranges,
                    attendance_ranges,
                    convert_day_period_to_utc((time(6, 0), time(22, 0)), tz)
                )
                # if att_extra_vals and (att_extra_vals.get('theoretical_work_time',0.0) > 0 or att_extra_vals.get('extra_time',0.0) > 0):
                if att_extra_vals and (
                        sum(att_extra_vals.values()) - att_extra_vals.get('theoretical_work_time', 0.0)) > 0:
                    if e.department_id.ignore_early_come_time >= att_extra_vals['early_come_time']:
                        att_extra_vals['early_come_time'] = 0
                    if e.department_id.ignore_late_time >= att_extra_vals['late_time']:
                        att_extra_vals['late_time'] = 0
                    if e.department_id.ignore_early_leave_time >= att_extra_vals['early_leave_time']:
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
    def get_work_time_details(self, work_time_ranges, attendance_ranges, day_period=(time(6, 0), time(22, 0))):
        def total_time(time_ranges):
            return sum((end - start).total_seconds() for start, end in time_ranges)

        def intersection_time(time_ranges1, time_ranges2):
            intersection = [(max(start1, start2), min(end1, end2)) for start1, end1 in time_ranges1 for start2, end2 in
                            time_ranges2 if end1 > start2 and end2 > start1]
            return intersection

        def day_time(time_ranges):
            if not time_ranges:
                return 0
            day_start, day_end = day_period
            day_ranges = [(max(start, datetime.combine(start.date(), day_start)),
                           min(end, datetime.combine(end.date(), day_end))) for start, end in time_ranges if
                          end.time() > day_start and start.time() < day_end]
            return total_time(day_ranges)

        def night_time(time_ranges):
            if not time_ranges:
                return 0
            day_start, day_end = day_period
            night_start = day_end
            night_duration = timedelta(hours=24) - (
                    datetime.combine(date.today(), day_end) - datetime.combine(date.today(), day_start))
            night_end = (datetime.combine(date.today(), night_start) + night_duration).time()

            night_ranges = [(max(start, datetime.combine(start.date(), night_start)),
                             min(end, datetime.combine(end.date(), night_end))) for start, end in time_ranges if
                            end.time() > night_start and start.time() < night_end]
            return total_time(night_ranges)

        def early_time(work_time_ranges, attendance_ranges):
            if not attendance_ranges:
                return 0
            first_attendance, first_work = attendance_ranges[0][0], work_time_ranges[0][0]
            return max(0, (first_work - first_attendance).total_seconds())

        def late_time(work_time_ranges, attendance_ranges):
            if not attendance_ranges:
                return 0
            first_attendance, first_work = attendance_ranges[0][0], work_time_ranges[0][0]
            return max(0, (first_attendance - first_work).total_seconds())

        def early_leave_time(work_time_ranges, attendance_ranges):
            if not attendance_ranges:
                return 0
            last_attendance, last_work = (attendance_ranges[-1][1] or attendance_ranges[-1][0]), work_time_ranges[-1][1]
            return max(0, (last_work - last_attendance).total_seconds())

        def overtime(work_time_ranges, attendance_ranges):
            if not work_time_ranges or not attendance_ranges:
                return 0
            last_work = work_time_ranges[-1][-1] if work_time_ranges else None
            overtime_start = next((start for start, end in reversed(attendance_ranges) if
                                   start < last_work and (end is None or end > last_work)), None)
            if overtime_start is None:
                return 0
            overtime_ranges = [(max(start, last_work), end) for start, end in attendance_ranges if
                               start >= overtime_start and end is not None]
            return total_time(overtime_ranges)

        def overtime_night(work_time_ranges, attendance_ranges):
            if not work_time_ranges or not attendance_ranges:
                return 0
            last_work = work_time_ranges[-1][-1]
            overtime_ranges = [(max(start, last_work), end) for start, end in attendance_ranges if
                               start < last_work and end is not None and end > last_work]
            if not overtime_ranges:
                return 0

            # Define day start and end based on day period
            day_start, day_end = day_period

            # Create empty list for overtime_night_ranges
            overtime_night_ranges = []

            # Check each range in overtime_ranges
            for start, end in overtime_ranges:
                # If start time is before day_start or after day_end, it's night time.
                # Similarly, if end time is before day_start or after day_end, it's also night time.
                if start.time() < day_start or start.time() > day_end:
                    overtime_night_ranges.append((start, min(end, datetime.combine(end.date(), day_start))))
                if end.time() > day_end or end.time() < day_start:
                    overtime_night_ranges.append((max(start, datetime.combine(start.date(), day_end)), end))

            return total_time(overtime_night_ranges)

        def extra_time(work_time_ranges, attendance_ranges):
            if not work_time_ranges:
                return total_time(attendance_ranges)
            return 0

        def extra_night(work_time_ranges, attendance_ranges):
            if work_time_ranges:
                return 0
            return night_time(attendance_ranges)

        theoretical_work_time = total_time(work_time_ranges)
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

        list_of_intersection = intersection_time(work_time_ranges, attendance_ranges)
        actual_work_time = total_time(list_of_intersection)
        actual_work_time_day = day_time(list_of_intersection)
        actual_work_time_night = night_time(list_of_intersection)

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
        for key, value in data.items():
            debug_msg += f"{key.replace('_', ' ').title()}: {value:.2f} hours" + '\n'
        debug_msg += '-----------------------------------------------------------\n'
        _logger.debug(debug_msg)

        assert all(time >= 0 for time in
                   [theoretical_work_time, actual_work_time, actual_work_time_day, actual_work_time_night,
                    early_come_time, late_time_value, early_leave_time_value, overtime_value,
                    extra_time_value]), "Negative time found"
        assert actual_work_time == actual_work_time_day + actual_work_time_night, "Total actual work time doesn't match with day and night work time"
        if extra_time_value > 0:
            assert all(time == 0 for time in [early_come_time, late_time_value, early_leave_time_value,
                                              overtime_value]), "Extra time found but other times are not zero"

        return data

        # def get_work_time_details(self, work_time_ranges, attendance_ranges, day_period=(time(6, 0), time(22, 0))):
    #     def get_overlapping_period(period1, period2):
    #         return max(period1[0], period2[0]), min(period1[1], period2[1])
    #
    #     def get_theoretical_work_time(work_time_ranges):
    #         theoretical_work_time = timedelta()
    #         for work_period in work_time_ranges:
    #             if len(work_period) == 2:
    #                 theoretical_work_time += work_period[1] - work_period[0]
    #         return theoretical_work_time
    #
    #     def get_actual_work_time_day_night(attendance_range, day_period):
    #         actual_work_time_day = timedelta()
    #         actual_work_time_night = timedelta()
    #
    #         start_day_time = datetime.combine(attendance_range[0].date(), day_period[0])
    #         end_day_time = datetime.combine(attendance_range[0].date(), day_period[1])
    #
    #         day_start, day_end = get_overlapping_period((attendance_range[0], attendance_range[1]),
    #                                                     (start_day_time, end_day_time))
    #
    #         if day_end > day_start:
    #             actual_work_time_day += day_end - day_start
    #
    #         night_periods = [(attendance_range[0], day_start), (day_end, attendance_range[1])]
    #
    #         for night_start, night_end in night_periods:
    #             if night_end > night_start:
    #                 actual_work_time_night += night_end - night_start
    #
    #         return actual_work_time_day, actual_work_time_night
    #
    #     def get_time_in_period(start, end, period_start, period_end):
    #         latest_start = max(start, period_start)
    #         earliest_end = min(end, period_end)
    #         delta = (earliest_end - latest_start).total_seconds()
    #         overlap = max(0, delta)
    #         return overlap / 3600
    #
    #     def get_day_night_hours(start_time, end_time, day_start, day_end):
    #         total_hours = (end_time - start_time).total_seconds() / 3600
    #         day_hours = get_time_in_period(start_time, end_time, day_start, day_end)
    #         night_hours = total_hours - day_hours
    #         return day_hours, night_hours
    #
    #     actual_work_time = timedelta()
    #     theoretical_work_time = get_theoretical_work_time(work_time_ranges)
    #     late_time = timedelta()
    #     early_leave_time = timedelta()
    #     early_come_time = timedelta()
    #     overtime = timedelta()
    #     extra_time = timedelta()
    #     actual_work_time_day = timedelta()
    #     actual_work_time_night = timedelta()
    #
    #     for attendance_range in attendance_ranges:
    #         if len(attendance_range) == 2:
    #             for i, work_period in enumerate(work_time_ranges):
    #                 if len(work_period) == 2 and attendance_range[0] < work_period[1] and attendance_range[1] > \
    #                         work_period[0]:
    #                     actual_start = max(attendance_range[0], work_period[0])
    #                     actual_end = min(attendance_range[1], work_period[1])
    #
    #                     day_start = datetime.combine(attendance_range[0].date(), day_period[0])
    #                     day_end = datetime.combine(attendance_range[0].date(), day_period[1])
    #
    #                     day_hours, night_hours = get_day_night_hours(actual_start, actual_end, day_start, day_end)
    #                     actual_work_time_day += day_hours
    #                     actual_work_time_night += night_hours
    #             if not work_time_ranges:  # If work_time_ranges is empty
    #                 extra_time += attendance_range[1] - attendance_range[0]
    #
    #     last_work_period_end = None
    #
    #     for j, attendance_range in enumerate(attendance_ranges):
    #         if len(attendance_range) == 2:
    #             for i, work_period in enumerate(work_time_ranges):
    #                 if len(work_period) == 2 and attendance_range[0] < work_period[1] and attendance_range[1] > \
    #                         work_period[0]:
    #                     actual_start = max(attendance_range[0], work_period[0])
    #                     actual_end = min(attendance_range[1], work_period[1])
    #
    #                     if j == 0 and actual_start > work_period[0]:
    #                         for k in range(i + 1):
    #                             if len(work_time_ranges[k]) == 2 and actual_start > work_time_ranges[k][1]:
    #                                 late_time += work_time_ranges[k][1] - work_time_ranges[k][0]
    #
    #                         late_time += actual_start - work_period[0]
    #
    #                     if j == len(attendance_ranges) - 1 and attendance_range[1] < work_period[1]:
    #                         early_leave_time += work_period[1] - actual_end
    #
    #                     if j == 0 and i == 0 and attendance_range[0] < work_period[0]:
    #                         early_come_time += work_period[0] - attendance_range[0]
    #
    #                     last_work_period_end = work_period[1]
    #
    #                     # Breaking the loop as the corresponding work_period for this attendance range is found
    #                     break
    #
    #     if attendance_ranges and work_time_ranges and attendance_ranges[-1][1] > work_time_ranges[-1][1]:
    #         overtime = attendance_ranges[-1][1] - work_time_ranges[-1][1]
    #
    #     return {
    #         'theoretical_work_time': theoretical_work_time.total_seconds() / 3600,
    #         'actual_work_time': actual_work_time.total_seconds() / 3600,
    #         'actual_work_time_day': actual_work_time_day.total_seconds() / 3600,
    #         'actual_work_time_night': actual_work_time_night.total_seconds() / 3600,
    #         'early_come_time': early_come_time.total_seconds() / 3600,
    #         'late_time': late_time.total_seconds() / 3600,
    #         'early_leave_time': early_leave_time.total_seconds() / 3600,
    #         'overtime': overtime.total_seconds() / 3600,
    #         'extra_time': extra_time.total_seconds() / 3600,
    #     }

    # def get_work_time_details(self, work_time_ranges, attendance_ranges, day_period=(time(8, 0), time(22, 0))):
    #     actual_work_time = timedelta()
    #     theoretical_work_time = timedelta()
    #     late_time = timedelta()
    #     early_leave_time = timedelta()
    #     early_come_time = timedelta()
    #     overtime = timedelta()
    #     extra_time = timedelta()
    #     actual_work_time_day = timedelta()
    #     actual_work_time_night = timedelta()
    #
    #     # Calculate theoretical work time regardless of attendance_ranges
    #     for work_period in work_time_ranges:
    #         if len(work_period) == 2:
    #             theoretical_work_time += work_period[1] - work_period[0]
    #
    #     if not work_time_ranges:  # If work_time_ranges is empty
    #         for attendance_range in attendance_ranges:
    #             if len(attendance_range) == 2:
    #                 extra_time += attendance_range[1] - attendance_range[0]
    #                 actual_work_time += attendance_range[1] - attendance_range[0]
    #
    #                 start_day_time = datetime.combine(attendance_range[0].date(), day_period[0])
    #                 end_day_time = datetime.combine(attendance_range[0].date(), day_period[1])
    #
    #                 if attendance_range[0] < start_day_time:
    #                     actual_work_time_night += start_day_time - attendance_range[0]
    #                 if attendance_range[1] > end_day_time:
    #                     actual_work_time_night += attendance_range[1] - end_day_time
    #
    #                 actual_work_time_day += actual_work_time - actual_work_time_night
    #
    #     else:
    #         for i, work_period in enumerate(work_time_ranges):
    #             for j, attendance_range in enumerate(attendance_ranges):
    #                 if len(attendance_range) == 2 and len(work_period) == 2:
    #                     if attendance_range[0] < work_period[1] and attendance_range[1] > work_period[0]:
    #                         actual_start = max(attendance_range[0], work_period[0])
    #                         actual_end = min(attendance_range[1], work_period[1])
    #                         actual_work_time += actual_end - actual_start
    #
    #                         start_day_time = datetime.combine(actual_start.date(), day_period[0])
    #                         end_day_time = datetime.combine(actual_start.date(), day_period[1])
    #
    #                         if actual_start < start_day_time:
    #                             actual_work_time_night += start_day_time - actual_start
    #                         if actual_end > end_day_time:
    #                             actual_work_time_night += actual_end - end_day_time
    #
    #                         actual_work_time_day += actual_end - actual_start - actual_work_time_night
    #
    #                         if j == 0 and attendance_range[0] > work_period[0]:
    #                             late_time += actual_start - work_period[0]
    #                         if j == len(attendance_ranges) - 1 and attendance_range[1] < work_period[1]:
    #                             early_leave_time += work_period[1] - actual_end
    #
    #                 if j == 0 and i == 0 and attendance_range[0] < work_period[0]:
    #                     early_come_time += work_period[0] - attendance_range[0]
    #
    #         if attendance_ranges and attendance_ranges[-1][1] > work_time_ranges[-1][1]:
    #             overtime += attendance_ranges[-1][1] - work_time_ranges[-1][1]
    #     return {
    #         'theoretical_work_time': theoretical_work_time.total_seconds() / 3600,
    #         'actual_work_time': actual_work_time.total_seconds() / 3600,
    #         'actual_work_time_day': actual_work_time_day.total_seconds() / 3600,
    #         'actual_work_time_night': actual_work_time_night.total_seconds() / 3600,
    #         'early_come_time': early_come_time.total_seconds() / 3600,
    #         'late_time': late_time.total_seconds() / 3600,
    #         'early_leave_time': early_leave_time.total_seconds() / 3600,
    #         'overtime': overtime.total_seconds() / 3600,
    #         'extra_time': extra_time.total_seconds() / 3600,
    #     }
