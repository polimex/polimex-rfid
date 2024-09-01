from datetime import timedelta

from odoo import fields, models, api, _

import logging
_logger = logging.getLogger(__name__)


action_selection = [
        ('1', _('Card Granted')),
        ('2', _('Card Denied')),
        ('3', _('Card Denied T/S')),
        ('4', _('Card Denied APB')),
        ('5', _('Zone Arm Denied')),
        ('6', _('Card Granted (no entry)')),
        ('7', _('Card Granted Insert')),
        ('8', _('Card Denied Insert')),
        ('9', _('Card Ejected')),
        ('10', _('Zone Arm')),
        ('11', _('Zone Disarm')),
        ('12', _('Hotel Button Pressed')),
        ('15', _('Zone Disarm Denied')),
        ('64', _('Request Instructions')),
    ]

class HrRfidUserEvent(models.Model):
    _name = 'hr.rfid.event.user'
    _inherit = ['hr.rfid.event', 'mail.thread']
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

    alarm_line_id = fields.Many2one(
        'hr.rfid.ctrl.alarm',
        string='Alarm line',
        help='Alarm line affected by this event',
        ondelete='cascade',
    )

    card_id = fields.Many2one(
        'hr.rfid.card',
        string='Card',
        help='Card affected by this event',
        ondelete='set null',
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
        for c in self.env['res.company'].search([]):
            if c.event_lifetime is None:
                return False
            lifetime = timedelta(days=int(c.event_lifetime))
            today = fields.Date.today()
            res = self.with_company(c).search([
                ('event_time', '<', today - lifetime)
            ], limit=1000)
            res.unlink()
            # self._cr.execute("""
            #             DELETE FROM hr_rfid_event_user
            #             WHERE event_time < NOW() - INTERVAL '%s days'
            #         """, [c.event_lifetime])
            _logger.info("GC'd %d old rfid user event entries", self._cr.rowcount)

        return True

    @api.depends('employee_id.name', 'contact_id.name', 'door_id.name', 'event_action')
    def _compute_user_ev_name(self):
        for record in self:
            if record.employee_id:
                name = record.employee_id.name or ''
            elif record.contact_id:
                name = record.contact_id.name or ''
            else:
                name = record.door_id.name or ''
            name += ' - ' if name != '' else ''
            if record.event_action != '64':
                name += record.get_event_action_text()
            else:
                name += _('Request Instructions')
            if record.door_id:
                name += ' @ ' + record.door_id.name
            record.name = name

    @api.depends('event_action')
    def _compute_user_ev_action_str(self):
        for record in self:
            record.action_string = _('Access {}').format(self.action_selection[int(record.event_action) - 1][1])

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        records = super(HrRfidUserEvent, self).create(vals_list)

        for rec in records:
            if not rec.employee_id and not rec.contact_id and rec.card_id:
                rec.employee_id = rec.card_id.employee_id
                rec.contact_id = rec.card_id.contact_id

            # Vending sale with money no user
            if not rec.employee_id and not rec.contact_id and rec.event_action != '47':
                _logger.error('User event without employee, contact and card. FATAL for event')
            # '1' == Granted

            if rec.event_action not in ['1']:
                continue

            if not rec.employee_id and not rec.contact_id:
                continue

            zones = rec.door_id.zone_ids

            if zones:
                # Reader type is In
                if rec.reader_id.reader_type == '0':
                    zones.with_context(from_event=True).person_entered(rec.employee_id or rec.contact_id, rec)
                # Reader type is Out
                else:
                    zones.with_context(from_event=True).person_left(rec.employee_id or rec.contact_id, rec)
                zones.process_event(rec)
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
                        ('event_time', '>=', fields.Datetime.now() - timedelta(hours=12)),
                        ('employee_id', '=', rec.employee_id.id),
                        ('id', '!=', rec.id),
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
        return records

    def zone_process_event(self):
        for rec in self:
            zones = rec.door_id.zone_ids
            if zones:
                zones.process_event(rec)

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

    @api.model
    def last_event(self, door_ids=None, partner_id=None, employee_id=None, event_action=None, domain=[], limit=1):
        """ Get last event for user

            """
        if door_ids is not None:
            domain.append(
                ('door_id', 'in', door_ids.mapped('id'))
            )
        if partner_id is not None:
            domain.append(
                ('contact_id', '=', partner_id.id)
            )
        if employee_id is not None:
            domain.append(
                ('employee_id', '=', employee_id.id)
            )
        if event_action is not None:
            domain.append(
                ('event_action', '=', str(event_action))
            )
        return self.search(domain, limit=limit)
