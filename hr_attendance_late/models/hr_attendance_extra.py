from odoo import api, fields, models
from datetime import datetime, timedelta, time

class HrAttendanceExtra(models.Model):
    _name = 'hr.attendance.extra'
    _description = 'Extra work time calculations'
    _order = 'for_date'

    for_date = fields.Date()
    employee_id = fields.Many2one(comodel_name='hr.employee', required=True, ondelete='cascade')
    department_id = fields.Many2one(related='employee_id.department_id', readonly=True, store=True)

    actual_work_time = fields.Float(digits=(2, 2))
    actual_work_time_day = fields.Float(digits=(2, 2))
    actual_work_time_night = fields.Float(digits=(2, 2))
    theoretical_work_time = fields.Float(digits=(2, 2))
    late_time = fields.Float(digits=(2, 2))
    early_leave_time = fields.Float(digits=(2, 2))
    early_come_time = fields.Float(digits=(2, 2))
    overtime = fields.Float(digits=(2, 2))
    overtime_night = fields.Float(digits=(2, 2))
    extra_time = fields.Float(digits=(2, 2))
    extra_night = fields.Float(digits=(2, 2))
    shift_number = fields.Integer(group_operator='count_distinct')

    attendance_count = fields.Char(string='Attendance records', compute='_compute_counts')

    def _compute_counts(self):
        for ae in self:
            ae.attendance_count = self.env['hr.attendance'].search_count([
                ('employee_id', '=', ae.employee_id.id),
                ('check_in', '>=', datetime.combine(ae.for_date, time(0, 0))),
                ('check_in', '<=', datetime.combine(ae.for_date, time(0, 0)) + timedelta(days=1))
            ])

    def _compute_display_name(self):
        super()._compute_display_name()
        for rec in self:
            rec.display_name = '%s / %s' % (rec.for_date, rec.employee_id.name)

    def open_attendance_logs(self):
        self.ensure_one()
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', datetime.combine(self.for_date, time(0, 0))),
            ('check_in', '<=', datetime.combine(self.for_date, time(0, 0)) + timedelta(days=1))
        ]
        res = self.env['ir.actions.act_window']._for_xml_id('hr_attendance.hr_attendance_action')
        res.update(
            context=dict(self.env.context, group_by=False),
            domain=domain
        )
        return res

