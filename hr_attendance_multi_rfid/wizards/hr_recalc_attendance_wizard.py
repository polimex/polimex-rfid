from odoo import fields, models, api, _
from datetime import timedelta


class WizardHrRecalcAttendanceEmployee(models.TransientModel):
    _name = 'hr.attendance.recalc.wizard'
    _description = 'Wizard for re-create attendance records based on RFID events'

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
        # default=lambda self: self._get_default_employees(),
        help="""Select employees whose attendance records will be recalculated from RFID events.
        
• Process: Existing auto-generated attendance will be deleted and recreated
• Manual attendance: Records created manually by HR will be preserved
• RFID events: System will analyze all RFID door events to rebuild attendance

Use this when attendance data seems incorrect or after changing zone settings.""",
    )
    start_date = fields.Date(
        string='Start Date',
        default=lambda self: self._get_default_from(),
        help="Starting date for attendance recalculation. Only attendance records from this "
             "date forward will be processed. Default is 30 days ago to cover recent period."
    )
    end_date = fields.Date(
        string='End Date',
        default=lambda self: self._get_default_to(),
        help="Ending date for attendance recalculation. Attendance records will be processed "
             "up to and including this date. Default is today."
    )

    def execute(self):
        self.employee_ids.recalc_attendance(self.start_date, self.end_date)
        return {"type": "ir.actions.act_window_close"}
        # res = self.env['ir.actions.act_window']._for_xml_id('hr_attendance_late.hr_attendance_extra_action')
        # # res.update(
        # #     context=dict(self.env.context, group_by=False),
        # #     domain=domain
        # # )
        # return res
