from odoo import api, fields, models
from datetime import datetime, timedelta


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
        for a in self:
            check_in = fields.Datetime.context_timestamp(a.employee_id.resource_calendar_id, a.check_in)
            day_start = fields.Datetime.context_timestamp(
                a.employee_id.resource_calendar_id,
                fields.Datetime.start_of(check_in, 'day')
            )

            check_in_in_interval = a._in_interval(check_in)
            near_start = a.employee_id.resource_calendar_id._get_closest_work_time(check_in)
            previous_inteval = a._previous_interval_for_today()
            if not previous_inteval:
                a.late = a.employee_id.resource_calendar_id.get_work_hours_count(day_start, check_in)
            else:
                a.late = a.employee_id.resource_calendar_id.get_work_hours_count(
                    previous_inteval.check_out,
                    check_in)
                # a.late = (abs((near_start-check_in).total_seconds())/(60))/60 if near_start and near_start < check_in else 0
            # if a.late == 0 or not previous_inteval:
            #     if not previous_inteval:
            #         a.late = a.employee_id.resource_calendar_id.get_work_hours_count(day_start, check_in)
            #     else:
            #         a.late = a.employee_id.resource_calendar_id.get_work_hours_count(
            #             previous_inteval.check_out or day_start,
            #             check_in)

            a.early = 0
            a.overtime = 0

            if a.employee_id.department_id and a.late < a.employee_id.department_id.minimum_late_time:
                a.late = 0


            if a.check_out:
                check_out = fields.Datetime.context_timestamp(a.employee_id.resource_calendar_id, a.check_out)
                check_out_in_interval = a._in_interval(check_out)
                near_end = a.employee_id.resource_calendar_id._get_closest_work_time(check_out, match_end=True)
                a.early = (abs((near_end - check_out).total_seconds()) / (60)) / 60 if near_end and near_end > check_out else 0
                near_start = a.employee_id.resource_calendar_id._get_closest_work_time(check_out)
                if near_end and near_end<check_in:
                    near_end = check_in

                if not check_out_in_interval and near_end and near_end < check_out:
                    a.overtime = (abs((near_end - check_out).total_seconds()) / 60) / 60
                else:
                    a.overtime = 0

                if a.employee_id.department_id and a.early < a.employee_id.department_id.minimum_early_leave_time:
                    a.early = 0
                if a.employee_id.department_id and a.overtime < a.employee_id.department_id.minimum_overtime:
                    a.overtime = 0

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