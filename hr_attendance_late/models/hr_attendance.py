from odoo import api, fields, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        e_ids = res.mapped('employee_id')
        dates = res.mapped('check_in')
        calc = [e_id.update_extra_attendance_data(a_date.date(),overwrite_existing=True) for e_id,a_date in zip(e_ids,dates)]
        return res

    def write(self, vals):
        super(HrAttendance, self).write(vals)
        e_ids = self.mapped('employee_id')
        dates = self.mapped('check_in')
        res = [e_id.update_extra_attendance_data(a_date.date(),overwrite_existing=True) for e_id,a_date in zip(e_ids,dates)]

    def unlink(self):
        e_ids = self.mapped('employee_id')
        dates = self.mapped('check_in')
        super().unlink()
        res = [e_id.update_extra_attendance_data(a_date.date(),overwrite_existing=True) for e_id,a_date in zip(e_ids,dates)]
