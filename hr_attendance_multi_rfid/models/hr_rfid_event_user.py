# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from datetime import datetime, timedelta


class HrRfidUserEvent(models.Model):
    _name = "hr.rfid.event.user"
    _inherit = "hr.rfid.event.user"

    in_or_out = fields.Selection(
        selection=[ ('in', 'Check In'), ('out', 'Check Out'), ('no_info', 'No Info') ],
        help="""Indicates whether this RFID event was processed as attendance check-in or check-out.

• Check In: Employee entered an attendance zone
• Check Out: Employee left an attendance zone  
• No Info: Event not processed for attendance (may be non-attendance zone or error)

This field is automatically set when recalculating attendance from RFID events.""",
        string='Attendance',
        default='no_info',
    )

    def button_show_employee_att_events(self):
        self.ensure_one()
        return {
            'name': _('Attendance for {}').format(self.employee_id.name),
            'view_mode': 'list,form',
            'res_model': 'hr.attendance',
            'domain': [('employee_id', '=', self.employee_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }
