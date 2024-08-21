from odoo import api, fields, models
from datetime import datetime, timedelta, time

class HrAttendanceExtraCost(models.Model):
    _inherit = ['hr.attendance.extra']

    currency_id = fields.Many2one('res.currency', related='employee_id.currency_id', readonly=True)
    hourly_cost = fields.Monetary('Hourly Cost', related='employee_id.hourly_cost', currency_field='currency_id',
        groups="hr.group_hr_user")

    actual_work_time_cost = fields.Monetary('Actual Work Time Cost',
                                            currency_field='currency_id',
                                            compute='_compute_actual_work_time_cost',
                                            groups="hr.group_hr_manager",
                                            store=True)

    @api.depends('actual_work_time', 'hourly_cost')
    def _compute_actual_work_time_cost(self):
        for ae in self:
            ae.actual_work_time_cost = ae.hourly_cost * ae.actual_work_time
