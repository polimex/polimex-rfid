# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from datetime import datetime, timedelta


class HrRfidUserEvent(models.Model):
    _inherit = "hr.rfid.event.user"

    in_or_out = fields.Selection(
        selection=[ ('in', 'Check In'), ('out', 'Check Out'), ('no_info', 'No Info') ],
        help='Whether the user came in or out',
        string='Attendance',
        default='no_info',
    )

    def button_show_employee_att_events(self):
        self.ensure_one()
        return {
            'name': _('Attendance for {}').format(self.employee_id.name),
            'view_mode': 'tree,form',
            'res_model': 'hr.attendance',
            'domain': [('employee_id', '=', self.employee_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }
