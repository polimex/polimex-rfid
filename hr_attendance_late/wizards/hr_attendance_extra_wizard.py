from odoo import fields, models, api, _
from datetime import timedelta


class WizardHrEmployee(models.TransientModel):
    _name = 'hr.attendance.extra.wizard'
    _description = 'Wizard for attendance extra calculations'

    def _get_default_employees(self):
        if self.env.context.get('active_model') == 'hr.attendance.extra':
            return [self.env['hr.attendance.extra'].browse(self.env.context.get('active_id')).employee_id.id]
        else:
            return []

    def _get_default_from(self):
        if self.env.context.get('active_model') == 'hr.attendance.extra':
            return self.env['hr.attendance.extra'].browse(self.env.context.get('active_id')).for_date
        else:
            return fields.Date.today() - timedelta(days=30)

    def _get_default_to(self):
        if self.env.context.get('active_model') == 'hr.attendance.extra':
            return self.env['hr.attendance.extra'].browse(self.env.context.get('active_id')).for_date
        else:
            return fields.Date.today()

    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        required=True,
        string="Employees",
        default=lambda self: self._get_default_employees(),
        help="""Select employees for attendance calculation recalculation.

        • Selection: Choose one or multiple employees
        • Effect: Recalculates overtime, late arrivals, and extra time for selected employees
        • Default: Pre-selected based on current context

        Note: Large employee selections may take longer to process.""",
    )
    start_date = fields.Date(
        string='Start Date',
        default=lambda self: self._get_default_from(),
        help="""Start date for the attendance calculation period.

        • Range: Beginning of the date range to recalculate
        • Default: 30 days ago or specific date from context
        • Effect: All attendance records from this date forward will be processed

        Note: Earlier dates will include more historical data in the calculation.""",
    )
    end_date = fields.Date(
        string='End Date',
        default=lambda self: self._get_default_to(),
        help="""End date for the attendance calculation period.

        • Range: Final date of the calculation period
        • Default: Today or specific date from context
        • Effect: All attendance records up to this date will be processed

        Note: Future dates will be ignored even if selected.""",
    )
    overwrite_existing = fields.Boolean(
        string="Overwrite Existing",
        help="""Control how existing attendance calculations are handled.

        • When enabled: Recalculates and overwrites all existing attendance extra records
        • When disabled: Only creates calculations for dates that don't have records yet
        • Effect: Determines whether to update or skip existing data

        Note: Enable this to fix calculation errors or update after policy changes.""",
        default=False)


    def execute(self):
        self.employee_ids.update_extra_attendance_data(self.start_date, self.end_date,
                                                       overwrite_existing=self.overwrite_existing)
        # return {"type": "ir.actions.act_window_close"}
        res = self.env['ir.actions.act_window']._for_xml_id('hr_attendance_late.hr_attendance_extra_action')
        # res.update(
        #     context=dict(self.env.context, group_by=False),
        #     domain=domain
        # )
        return res

