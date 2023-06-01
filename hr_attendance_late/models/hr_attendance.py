from odoo import api, fields, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    def write(self, vals):
        super(HrAttendance, self).write(vals)
        self.mapped('employee_id').update_extra_attendance_data(self.check_in.date(),overwrite_existing=True)
