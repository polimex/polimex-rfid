# -*- coding: utf-8 -*-
from odoo import models, api, fields


class HrRfidUserEvent(models.Model):
    _inherit = "hr.rfid.event.user"

    in_or_out = fields.Selection(
        selection=[ ('0', 'In'), ('1', 'Out'), ('2', 'No Info') ],
        help='Whether the user came in or out',
        string='User presence',
        default='2',
    )

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        ev = super(HrRfidUserEvent, self).create(vals)

        if ev.door_id.attendance is True and ev.event_action == '1':
            if ev.reader_id.reader_type == '0' and ev.user_id.attendance_state == 'checked_out':
                ev.in_or_out = '0'
                ev.user_id.attendance_action_change_with_date(ev.event_time)
            elif ev.reader_id.reader_type == '1' and ev.user_id.attendance_state == 'checked_in':
                ev.in_or_out = '1'
                ev.user_id.attendance_action_change_with_date(ev.event_time)

        return ev
