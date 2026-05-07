from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SchEncoderRoom(models.Model):
    _name = 'rfid_pms_base.room'
    _description = 'Rooms'
    _order = 'number'

    name = fields.Char(required=True)
    group = fields.Char(default='Ungrouped')
    number = fields.Integer(string='Internal number', required=True)
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)
    door_id = fields.Many2one('hr.rfid.door',
                              string='Room door',
                              required=True
                              )
    access_group_id = fields.Many2one('hr.rfid.access.group',
                                      string='Guest Group',
                                      required=True
                                      )
    all_employee_ids = fields.Many2many(
        'hr.rfid.access.group.employee.rel',
        string='All employees',
        help='All employees that use this access group, including the ones from the inheritors',
        related='access_group_id.all_employee_ids',
    )

    all_contact_ids = fields.Many2many(
        'hr.rfid.access.group.contact.rel',
        string='All contacts',
        help='All contacts that use this access group, including the ones from the inheritors',
        related='access_group_id.all_contact_ids',
    )
    reservation = fields.Many2one('res.partner',
                                  string='Reservation',
                                  compute='_compute_reservation'
                                  )

    hb_dnd = fields.Boolean(
        string='DND button pressed',
        related='door_id.hb_dnd',
    )
    hb_clean = fields.Boolean(
        string='Clean button pressed',
        related='door_id.hb_clean',
    )
    hb_card_present = fields.Boolean(
        string='Present card in reader',
        related='door_id.hb_card_present',
    )

    last_temperature = fields.Float(string='Temperature', compute='_compute_temperature')
    last_humidity = fields.Float(string='Humidity', compute='_compute_temperature')
    last_occupancy = fields.Char(string='Occupancy', compute='_compute_temperature')
    last_insert_name = fields.Char(string='Last Insert Card', compute='_compute_last_insert_name')

    @api.depends('hb_card_present')
    def _compute_last_insert_name(self):
        # Batched: one query for all rooms in self instead of N+1 — important
        # because the kanban renders this field on every card refresh.
        door_ids = self.mapped('door_id').ids
        last_event_per_door = {}
        if door_ids:
            grouped = self.env['hr.rfid.event.user']._read_group(
                domain=[('door_id', 'in', door_ids), ('event_action', '=', '7')],
                groupby=['door_id'],
                aggregates=['id:max'],
            )
            event_ids = [event_id for __, event_id in grouped if event_id]
            events_by_id = {e.id: e for e in self.env['hr.rfid.event.user'].browse(event_ids)}
            last_event_per_door = {
                door.id: events_by_id[event_id]
                for door, event_id in grouped if event_id and event_id in events_by_id
            }
        for r in self:
            event = last_event_per_door.get(r.door_id.id)
            r.last_insert_name = (
                event and (event.employee_id.name or event.contact_id.name) or 'Unknown'
            )

    @api.depends('all_contact_ids')
    def _compute_reservation(self):
        for r in self:
            r.reservation = r.all_contact_ids[0].contact_id.parent_id if r.all_contact_ids else None

    def user_events_act(self):
        self.ensure_one()
        return self.with_context(res_model='hr.rfid.event.user').door_id.button_act_window()

    def toggle_hotel(self):
        self.ensure_one()
        button = self.env.context.get('btn', '')
        if button == 'dnd':
            self.door_id.hb_dnd = not self.hb_dnd
        elif button == 'clean':
            self.door_id.hb_clean = not self.hb_clean
        elif button == 'guests':
            pass

    def _compute_temperature(self):
        # Stub values until a BMS sensor module supplies live data.
        for r in self:
            r.last_humidity = 45.7
            r.last_occupancy = 1
            r.last_temperature = 21.5

    @api.constrains('number')
    def _check_number(self):
        for record in self:
            if record.number < 1 or record.number > 65535:
                raise ValidationError(_('Room number have to be between 1 and 65535'))

    _unique_room_number = models.Constraint('unique(number)', "Duplicate room number.")
