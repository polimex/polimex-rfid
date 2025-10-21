from collections import defaultdict

from odoo import api, fields, models
from datetime import datetime, timedelta, time

class HrAttendanceExtra(models.Model):
    _name = 'hr.attendance.extra'
    _description = 'Extra work time calculations'
    _order = 'for_date'

    for_date = fields.Date(required=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', required=True, ondelete='cascade')
    department_id = fields.Many2one(related='employee_id.department_id', readonly=True, store=True)

    actual_work_time = fields.Float(digits=(2,2))
    actual_work_time_day = fields.Float(digits=(2,2))
    actual_work_time_night = fields.Float(digits=(2,2))
    theoretical_work_time = fields.Float(digits=(2,2))
    late_time = fields.Float(digits=(2,2))
    early_leave_time = fields.Float(digits=(2,2))
    early_come_time = fields.Float(digits=(2,2))
    overtime = fields.Float(digits=(2,2))
    overtime_night = fields.Float(digits=(2,2))
    extra_time = fields.Float(digits=(2,2))
    extra_night = fields.Float(digits=(2,2))
    shift_number = fields.Integer(group_operator='count_distinct')

    attendance_count = fields.Char(string='Attendance records', compute='_compute_counts')

    def _compute_counts(self):
        """Compute attendance count using batch prefetch pattern.

        Optimized to use ONE query instead of N queries when computing for multiple records.
        Pattern: Similar to hr_attendance._update_overtime batch processing.
        """
        if not self:
            return

        # Filter out records without dates and set their count to 0
        valid_records = self.filtered(lambda r: r.for_date and r.employee_id)
        invalid_records = self - valid_records

        for ae in invalid_records:
            ae.attendance_count = 0

        if not valid_records:
            return

        # Batch prefetch - ONE query for all attendances in range
        # Filter out any False values from dates
        dates = [d for d in valid_records.mapped('for_date') if d]

        if not dates:
            return

        min_date = min(dates)
        max_date = max(dates)
        employee_ids = valid_records.mapped('employee_id').ids

        all_attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', employee_ids),
            ('check_in', '>=', datetime.combine(min_date, time(0, 0))),
            ('check_in', '<', datetime.combine(max_date + timedelta(days=1), time(0, 0)))
        ])

        # Group by (employee_id, date) in memory - O(N) complexity
        counts = defaultdict(int)
        for att in all_attendances:
            att_date = att.check_in.date()
            key = (att.employee_id.id, att_date)
            counts[key] += 1

        # Assign counts - O(1) lookup per record
        for ae in valid_records:
            ae.attendance_count = counts.get((ae.employee_id.id, ae.for_date), 0)
    def name_get(self):
        def get_names(cat):
            return '%s / %s' % (cat.for_date, cat.employee_id.name)
        return [(cat.id, get_names(cat)) for cat in self]

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

