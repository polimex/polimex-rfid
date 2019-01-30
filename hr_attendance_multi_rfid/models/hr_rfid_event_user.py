# -*- coding: utf-8 -*-
from odoo import models, api


class HrRfidUserEvent(models.Model):
    _inherit = "hr.rfid.event.user"

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        ev = super(HrRfidUserEvent, self).create(vals)

        if ev.door_id.attendance is True and ev.event_action == '1':
            if ev.reader_id.reader_type == '0' and ev.user_id.attendance_state == 'checked_out':
                ev.user_id.attendance_action_change_with_date(ev.event_time)
            elif ev.reader_id.reader_type == '1' and ev.user_id.attendance_state == 'checked_in':
                ev.user_id.attendance_action_change_with_date(ev.event_time)

        return ev
