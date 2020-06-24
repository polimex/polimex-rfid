from odoo import api, fields, models
from datetime import datetime, timedelta


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    check_in = fields.Datetime(
        index=True,
    )

    check_out = fields.Datetime(
        index=True,
    )


    @api.model
    def _check_for_forgotten_attendances(self):
        max_att = int(self.env['ir.config_parameter'].sudo().get_param('hr_attendance_multi_rfid.max_attendance'))

        td = timedelta(minutes=max_att)

        atts = self.search([
            ('check_out', '=', None)
        ])

        for att in atts:
            check_out = att.check_in + td
            if check_out <= datetime.now():
                att.check_out = check_out

