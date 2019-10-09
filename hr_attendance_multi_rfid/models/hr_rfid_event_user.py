# -*- coding: utf-8 -*-
from odoo import models, api, fields
from datetime import datetime, timedelta


class HrRfidUserEvent(models.Model):
    _inherit = "hr.rfid.event.user"

    in_or_out = fields.Selection(
        selection=[ ('0', 'In'), ('1', 'Out'), ('2', 'No Info') ],
        help='Whether the user came in or out',
        string='User presence',
        default='2',
    )

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        def check_check_in(cev):
            if cev.employee_id.attendance_state == 'checked_out':
                cev.in_or_out = '0'
                cev.employee_id.attendance_action_change_with_date(cev.event_time, cev.id)

        def check_check_out(cev):
            if cev.employee_id.attendance_state == 'checked_in':
                cev.in_or_out = '1'
                cev.employee_id.attendance_action_change_with_date(cev.event_time, cev.id)

        records = self.env['hr.rfid.event.user']
        for vals in vals_list:
            ev = super(HrRfidUserEvent, self).create([vals])
            records += ev

            if len(ev.contact_id) > 0:
                continue

            if ev.door_id.attendance is True and ev.event_action == '1':
                if ev.reader_id.mode == '03':  # Workcode mode
                    wc = ev.workcode_id
                    if len(wc) == 0:
                        continue

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
                elif ev.reader_id.reader_type == '0' and ev.employee_id.attendance_state == 'checked_out':
                    ev.in_or_out = '0'
                    ev.employee_id.attendance_action_change_with_date(ev.event_time, ev.id)
                elif ev.reader_id.reader_type == '1' and ev.employee_id.attendance_state == 'checked_in':
                    ev.in_or_out = '1'
                    ev.employee_id.attendance_action_change_with_date(ev.event_time, ev.id)

        return records
