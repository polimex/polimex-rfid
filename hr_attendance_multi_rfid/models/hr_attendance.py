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

    late = fields.Float(string='Late time', compute='_compute_times')

    def _compute_times(self):
        for a in self:
            # interval = a.employee_id.resource_calendar_id._attendance_intervals_batch(
            #     a.check_in,
            #     a.check_in+timedelta(seconds=1)
            # )
            a.late = 5/60

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

    def write(self, vals):
        result = super(HrAttendance, self).write(vals)
        # for att in self:
        #     if vals.get('check_out', False):
        #         self.env['hr.rfid.zone'].search([
        #             ('employee_ids', 'in', att.employee_id.id),
        #             ('attendance', '=', True)
        #         ]).person_left(att.employee_id)
        return result
