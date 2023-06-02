from odoo import api, fields, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.mapped('employee_id').update_extra_attendance_data(self.check_in.date(),overwrite_existing=True)
        return res

    def write(self, vals):
        super(HrAttendance, self).write(vals)
        self.mapped('employee_id').update_extra_attendance_data(self.check_in.date(),overwrite_existing=True)
