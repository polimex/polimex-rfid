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
        def check_check_in(cev):
            if cev.employee_id.attendance_state == 'checked_out':
                cev.in_or_out = '0'
                cev.employee_id.attendance_action_change_with_date(cev.event_time)

        def check_check_out(cev):
            if cev.employee_id.attendance_state == 'checked_in':
                cev.in_or_out = '1'
                cev.employee_id.attendance_action_change_with_date(cev.event_time)

        ev = super(HrRfidUserEvent, self).create(vals)

        if len(ev.contact_id) > 0:
            return ev

        if ev.door_id.attendance is True and ev.event_action == '1':
            if ev.reader_id.mode == '03':  # Workcode mode
                wc = ev.workcode_id
                if len(wc) == 0:
                    return ev

                if wc.user_action == 'stop':
                    stack = []
                    last_events = self.search([
                        ('event_time',  '>=', datetime.now() - timedelta(hours=12)),
                        ('employee_id',  '=', ev.employee_id.id),
                        ('id',          '!=', ev.id),
                        ('workcode_id', '!=', None),
                    ]).sorted(key=lambda r: r.event_time)

                    for event in last_events:
                        action = event.workcode_id.user_action
                        if action == 'stop':
                            if len(stack) > 0:
                                stack.pop()
                        else:
                            stack.append(action)

                    if len(stack) > 0:
                        if stack[-1] == 'start':
                            check_check_out(ev)
                        else:
                            check_check_in(ev)

                elif wc.user_action == 'start':
                    check_check_in(ev)
                elif wc.user_action == 'break':
                    check_check_out(ev)

        return ev
