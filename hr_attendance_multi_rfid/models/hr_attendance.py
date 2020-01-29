from odoo import api, fields, models
from datetime import datetime, timedelta


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    theoretical_hours = fields.Float(
        compute="_compute_theoretical_hours",
        store=True,
        compute_sudo=True,
    )

    check_in = fields.Datetime(
        index=True,
    )

    check_out = fields.Datetime(
        index=True,
    )

    @api.depends('check_in', 'employee_id')
    def _compute_theoretical_hours(self):
        obj = self.env['hr.attendance.theoretical.time.report']
        for record in self:
            record.theoretical_hours = obj._theoretical_hours(
                record.employee_id, record.check_in,
            )

    @api.model
    def _check_for_forgotten_attendances(self):
        max_att = str(self.env['ir.config_parameter'].get_param('hr_attendance_multi_rfid.max_attendance'))
        max_att = max_att.split()

        if len(max_att) != 2:
            return

        if max_att[0][-1] == 'h' and max_att[1][-1] == 'm':
            h = max_att[0][:-1]
            m = max_att[1][:-1]
        elif max_att[0][-1] == 'm' and max_att[1][-1] == 'h':
            h = max_att[1][:-1]
            m = max_att[0][:-1]
        else:
            return

        td = timedelta(hours=int(h), minutes=int(m))

        atts = self.search([
            ('check_out', '=', None)
        ])

        for att in atts:
            check_out = att.check_in + td
            if check_out <= datetime.now():
                att.check_out = check_out

