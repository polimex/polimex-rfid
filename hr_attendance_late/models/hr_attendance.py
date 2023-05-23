from odoo import api, fields, models
from datetime import datetime, time, timedelta
from pytz import timezone, UTC


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    late = fields.Float(string='Late',
                        compute='_compute_times',
                        store=True,
                        group_operator='sum')
    early = fields.Float(string='Early leave',
                         compute='_compute_times',
                         store=True,
                         group_operator='sum')
    overtime = fields.Float(string='Overtime',
                            compute='_compute_times',
                            store=True,
                            group_operator='sum')

    @api.depends('check_in', 'check_out',
                 'employee_id.department_id.minimum_late_time',
                 'employee_id.department_id.minimum_overtime',
                 'employee_id.department_id.minimum_early_leave_time',
                 'employee_id.resource_calendar_id',
                 'employee_id.resource_calendar_id.attendance_ids')
    def _compute_times(self):
        for record in self:
            employee = record.employee_id

            late = 0.0
            early_leave = 0.0
            extra_time = 0.0

            check_in_time = record.check_in
            check_out_time = record.check_out if record.check_out else None

            attendance_day_of_week = str(check_in_time.weekday())

            work_hours = sum(
                line.hour_to - line.hour_from for line in employee.resource_calendar_id.attendance_ids if
                line.dayofweek == attendance_day_of_week)
            current_id = record.id if isinstance(record.id, int) else record.id.origin
            # Get previous attendance records for the same day
            same_day_attendances = self.search(
                [('employee_id', '=', employee.id),
                 ('check_in', '<', record.check_in),
                 ('check_in', '>=', check_in_time.replace(hour=0, minute=0, second=0)),
                 ('id', '<', current_id)])

            for line in employee.resource_calendar_id.attendance_ids.filtered(
                    lambda r: r.dayofweek == attendance_day_of_week):
                # Get the employee's working schedule timezone
                tz = timezone(employee.resource_calendar_id.tz) if employee.resource_calendar_id.tz else UTC

                # Convert the start_time to UTC
                start_time = tz.localize(
                    datetime.combine(check_in_time.date(),
                                     time(hour=int(line.hour_from),
                                          minute=int((line.hour_from % 1) * 60)))).astimezone(UTC).replace(tzinfo=None)

                # Convert the end_time to UTC
                end_time = tz.localize(
                    datetime.combine(check_in_time.date(),
                                     time(hour=int(line.hour_to),
                                          minute=int((line.hour_to % 1) * 60)))).astimezone(UTC).replace(tzinfo=None)

                # Gather check-ins and check-outs for the current interval
                interval_attendances = [att for att in same_day_attendances] + (
                    [record] if record.check_in <= end_time and (record.check_out or start_time) >= start_time else [])

                if not interval_attendances:
                    continue

                # check_in_time = min([att.check_in for att in interval_attendances])
                # check_out_time = max([att.check_out for att in interval_attendances if att.check_out]) if any(
                #     [att.check_out for att in interval_attendances]) else None

                if check_in_time > start_time:
                    late += (check_in_time - start_time).total_seconds() / 3600

                if check_out_time:
                    if check_out_time < end_time:
                        early_leave += (end_time - check_out_time).total_seconds() / 3600

                    worked_hours = sum(
                        [(att.check_out - att.check_in).total_seconds() / 3600 for att in interval_attendances if
                         att.check_out])
                    extra_time += worked_hours - work_hours if worked_hours > work_hours else 0.0
                else:
                    early_leave = 0.0
                    extra_time = 0.0

            record.late = late
            record.early = early_leave
            record.overtime = extra_time

    def _in_interval(self, dt):
        self.ensure_one()
        return self.employee_id.resource_calendar_id._attendance_intervals_batch(dt, dt + timedelta(seconds=1))

    def _previous_interval_for_today(self):
        self.ensure_one()
        return self.search([
            ('employee_id', '=', self.employee_id.id),
            '&',
            ('check_in', '>=', fields.Datetime.start_of(self.check_in, 'day')),
            ('check_in', '<', self.check_in)
        ], limit=1, order='check_in desc')

    def write(self, vals):
        super(HrAttendance, self).write(vals)
        self.mapped('employee_id').update_extra_attendance_data(self.check_in.date())
        # self._compute_times
