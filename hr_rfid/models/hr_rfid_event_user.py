from datetime import timedelta

from odoo import fields, models, api, _


class HrRfidUserEvent(models.Model):
    _name = 'hr.rfid.event.user'
    _description = "RFID User Event"
    _order = 'event_time desc'

    name = fields.Char(
        compute='_compute_user_ev_name'
    )

    ctrl_addr = fields.Integer(
        string='Controller ID',
        required=True,
        help='ID the controller differentiates itself from the others with on the same webstack'
    )

    workcode = fields.Char(
        string='Workcode (Raw)',
        help="Workcode that arrived from the event. If you are seeing this version, it means that you haven't created "
             'a workcode label for this one in the workcodes page.',
        default='-',
        readonly=True,
    )

    workcode_id = fields.Many2one(
        comodel_name='hr.rfid.workcode',
        string='Workcode',
        help='Workcode that arrived from the event',
        readonly=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help='Employee affected by this event',
        ondelete='cascade',
    )

    contact_id = fields.Many2one(
        'res.partner',
        string='Contact',
        help='Contact affected by this event',
        ondelete='cascade',
    )

    door_id = fields.Many2one(
        'hr.rfid.door',
        string='Door',
        help='Door affected by this event',
        ondelete='cascade',
    )

    reader_id = fields.Many2one(
        'hr.rfid.reader',
        string='Reader',
        help='Reader affected by this event',
        required=True,
        ondelete='cascade',
    )

    card_id = fields.Many2one(
        'hr.rfid.card',
        string='Card',
        help='Card affected by this event',
        ondelete='cascade',
    )

    command_id = fields.Many2one(
        'hr.rfid.command',
        string='Response',
        help='Response command',
        readonly=True,
        ondelete='set null',
    )

    event_time = fields.Datetime(
        string='Timestamp',
        help='Time the event triggered',
        required=True,
        index=True,
    )

    action_selection = [
        ('1', _('Granted')),
        ('2', _('Denied')),
        ('3', _('Denied T/S')),
        ('4', _('Denied APB')),
        ('5', _('Exit Button')),
        ('6', _('Granted (no entry)')),
        ('7', _('Granted Insert')),
        ('8', _('Denied Insert')),
        ('9', _('Ejected')),
        ('10', _('Zone Alarm')),
        ('11', _('Zone Arm/Disarm')),
        ('12', _('Hotel Button Pressed')),
        ('64', _('Request Instructions')),
    ]

    event_action = fields.Selection(
        selection=action_selection,
        string='Action',
        help='What happened to trigger the event',
        required=True,
    )

    action_string = fields.Char(
        compute='_compute_user_ev_action_str',
    )

    more_json = fields.Char(
        string='More info about event in JSON',
    )


    @api.autovacuum
    def _gc_user_events_life(self):
        event_lifetime = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.event_lifetime')
        if event_lifetime is None:
            return False

        lifetime = timedelta(days=int(event_lifetime))
        today = fields.Date.today()
        res = self.search([
            ('event_time', '<', today-lifetime)
        ])
        res.unlink()

    def _compute_user_ev_name(self):
        for record in self:
            if record.employee_id:
                name = record.employee_id.name
            elif record.contact_id:
                name = record.contact_id.name
            else:
                name = record.door_id.name
            name += ' - '
            if record.event_action != '64':
                name += self.action_selection[int(record.event_action)-1][1]
            else:
                name += _('Request Instructions')
            if record.door_id:
                name += ' @ ' + record.door_id.name
            record.name = name

    def _compute_user_ev_action_str(self):
        for record in self:
            record.action_string = _('Access {}').format(self.action_selection[int(record.event_action)-1][1])

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        records = super(HrRfidUserEvent, self).create(vals_list)

        for rec in records:
            # '1' == Granted
            if rec.event_action != '1':
                continue

            if not rec.employee_id and not rec.contact_id:
                continue

            zones = rec.door_id.zone_ids

            if len(rec.door_id.reader_ids) > 1:
                # Reader type is In
                if rec.reader_id.reader_type == '0':
                    zones.person_entered(rec.employee_id or rec.contact_id, rec)
                # Reader type is Out
                else:
                    zones.person_left(rec.employee_id or rec.contact_id, rec)
                continue

            if rec.reader_id.mode != '03':
                zones.person_went_through(rec)
            else:
                wc = rec.workcode_id
                if len(wc) == 0:
                    continue

                if wc.user_action == 'start':
                    rec.door_id.zone_ids.person_entered(rec.employee_id, rec)
                elif wc.user_action == 'break':
                    rec.door_id.zone_ids.person_left(rec.employee_id, rec)
                elif wc.user_action == 'stop':
                    stack = []
                    last_events = self.search([
                        ('event_time',  '>=', fields.Datetime.now() - timedelta(hours=12)),
                        ('employee_id',  '=', rec.employee_id.id),
                        ('id',          '!=', rec.id),
                        ('workcode_id', '!=', None),
                    ], order='event_time')
                    # TODO Check the search above to limit result!!!
                    for event in last_events:
                        action = event.workcode_id.user_action
                        if action == 'stop':
                            if len(stack) > 0:
                                stack.pop()
                        else:
                            stack.append(action)

                    if len(stack) > 0:
                        if stack[-1] == 'start':
                            rec.door_id.zone_ids.person_left(rec.employee_id, rec)
                        else:
                            rec.door_id.zone_ids.person_entered(rec.employee_id, rec)
        # self.refresh_views()
        return records

    def button_show_employee_events(self):
        self.ensure_one()
        return {
            'name': _('Events for {}').format(self.employee_id.name),
            'view_mode': 'tree,form',
            'res_model': self._name,
            'domain': [('employee_id', '=', self.employee_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }

    def button_show_contact_events(self):
        self.ensure_one()
        return {
            'name': _('Events for {}').format(self.contact_id.name),
            'view_mode': 'tree,form',
            'res_model': self._name,
            'domain': [('contact_id', '=', self.contact_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }

    def button_show_card_events(self):
        self.ensure_one()
        return {
            'name': _('Events for {}').format(self.card_id.name),
            'view_mode': 'tree,form',
            'res_model': self._name,
            'domain': [('card_id', '=', self.card_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }
    
    def button_show_door_events(self):
        self.ensure_one()
        return {
            'name': _('Events on {}').format(self.door_id.name),
            'view_mode': 'tree,form',
            'res_model': self._name,
            'domain': [('door_id', '=', self.door_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }

    def button_show_reader_events(self):
        self.ensure_one()
        return {
            'name': _('Events on {}').format(self.reader_id.name),
            'view_mode': 'tree,form',
            'res_model': self._name,
            'domain': [('reader_id', '=', self.reader_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }



