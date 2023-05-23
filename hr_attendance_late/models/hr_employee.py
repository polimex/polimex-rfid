# -*- coding: utf-8 -*-
from dateutil.rrule import rrule, DAILY

from odoo import api, fields, models
from datetime import datetime, timedelta, time
from pytz import timezone, UTC

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
        to_datetime = to_datetime or from_datetime
        for e in self:
            current_date = from_datetime
            tz = timezone(e.resource_calendar_id.tz) if e.resource_calendar_id.tz else UTC
            while current_date <= to_datetime:
                work_time_ranges = [line_to_tz_datetime(current_date, line, tz) for line in e.resource_calendar_id.attendance_ids if
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
                att_extra_vals = None
                if attendance_ranges:
                    att_extra_vals = self.get_work_time_details(work_time_ranges, attendance_ranges)
                if att_extra_vals:
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
    def get_work_time_details(self, work_time_ranges, attendance_ranges, day_period=(time(8, 0), time(22, 0))):
        actual_work_time = timedelta()
        theoretical_work_time = timedelta()
        late_time = timedelta()
        early_leave_time = timedelta()
        early_come_time = timedelta()
        overtime = timedelta()
        extra_time = timedelta()
        actual_work_time_day = timedelta()
        actual_work_time_night = timedelta()

        if not work_time_ranges:  # If work_time_ranges is empty
            for attendance_range in attendance_ranges:
                if len(attendance_range) == 2:
                    extra_time += attendance_range[1] - attendance_range[0]
                    if attendance_ranges.index(attendance_range) == 0:
                        early_come_time += datetime.now() - attendance_range[0]
        else:
            for work_period in work_time_ranges:
                if len(work_period) == 2:
                    theoretical_work_time += work_period[1] - work_period[0]

            for i, work_period in enumerate(work_time_ranges):
                for j, attendance_range in enumerate(attendance_ranges):
                    if len(attendance_range) == 2 and len(work_period) == 2:
                        if attendance_range[0] < work_period[1] and attendance_range[1] > work_period[0]:
                            actual_start = max(attendance_range[0], work_period[0])
                            actual_end = min(attendance_range[1], work_period[1])
                            actual_work_time += actual_end - actual_start

                            if actual_start.time() >= day_period[0] and actual_end.time() <= day_period[1]:
                                actual_work_time_day += actual_end - actual_start
                            else:
                                actual_work_time_night += actual_end - actual_start

                            if j == 0 and attendance_range[0] > work_period[0]:
                                late_time += actual_start - work_period[0]
                            if j == len(attendance_ranges) - 1 and attendance_range[1] < work_period[1]:
                                early_leave_time += work_period[1] - actual_end

                    if j == 0 and i == 0 and attendance_range[0] < work_period[0]:
                        early_come_time += work_period[0] - attendance_range[0]

            if attendance_ranges[-1][1] > work_time_ranges[-1][1]:
                overtime += attendance_ranges[-1][1] - work_time_ranges[-1][1]

                return {
                    'theoretical_work_time': theoretical_work_time.total_seconds() / 3600,
                    'actual_work_time': actual_work_time.total_seconds() / 3600,
                    'actual_work_time_day': actual_work_time_day.total_seconds() / 3600,
                    'actual_work_time_night': actual_work_time_night.total_seconds() / 3600,
                    'late_time': late_time.total_seconds() / 3600,
                    'early_leave_time': early_leave_time.total_seconds() / 3600,
                    'early_come_time': early_come_time.total_seconds() / 3600,
                    'extra_time': extra_time.total_seconds() / 3600,
                    'overtime': overtime.total_seconds() / 3600
                }
