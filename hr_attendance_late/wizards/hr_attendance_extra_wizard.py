from odoo import fields, models, api, _
from datetime import timedelta

class WizardHrEmployee(models.TransientModel):
    _name = 'hr.attendance.extra.wizard'
    _description = 'Wizard for attendance extra calculations'

    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        required=True,
        string="Employees",
        help="Recompute these employees extra attendances",
    )
    start_date = fields.Date(string='Start Date', default=lambda self: fields.Date.today() - timedelta(days=30))
    end_date = fields.Date(string='End Date',default=lambda self: fields.Date.today())

    def execute(self):
        self.employee_ids.update_extra_attendance_data(self.start_date, self.end_date)
        return {"type": "ir.actions.act_window_close"}
