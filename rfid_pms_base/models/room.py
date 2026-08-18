from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SchEncoderRoom(models.Model):
    _name = 'rfid_pms_base.room'
    _description = 'Rooms'
    _order = 'number'

    name = fields.Char(
        required=True,
        help="Friendly label for the room shown to the receptionist (e.g. 'Suite 101' or 'Twin Sea View'). The internal number below is the technical identifier used by the controller.",
    )
    group = fields.Char(
        default='Ungrouped',
        help="Optional grouping label used to split the kanban into columns (e.g. floor or wing). Rooms with the same group appear side by side.",
    )
    number = fields.Integer(
        string='Internal number',
        required=True,
        help="Numeric identifier the controller uses to address this room's door. Must be unique across the whole hotel; valid range 1-65535.",
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Company that owns the room. Hotel data is isolated per company; users only see rooms of their allowed companies.",
    )
    door_id = fields.Many2one(
        'hr.rfid.door',
        string='Room door',
        required=True,
        help="The controller door wired to this room's lock. The DND, Clean and Card-present flags shown on the kanban card mirror this door's hotel-mode state.",
    )
    access_group_id = fields.Many2one(
        'hr.rfid.access.group',
        string='Guest Group',
        required=True,
        help="Access group the issued guest cards are added to. Defines which doors a card can open (typically the room + common areas) and on what schedule.",
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
    reservation = fields.Many2one(
        'res.partner',
        string='Reservation',
        compute='_compute_reservation',
        help="Parent partner that groups every guest card currently issued for this room. Empty when the room is free; populated automatically when the first card is encoded.",
    )

    hb_dnd = fields.Boolean(
        string='DND button pressed',
        related='door_id.hb_dnd',
        help="True when the guest pressed Do Not Disturb on the in-room console. Staff cards still open the door; cleaning carts visiting the room will see the DND flag on the kanban card.",
    )
    hb_clean = fields.Boolean(
        string='Clean button pressed',
        related='door_id.hb_clean',
        help="True when the guest requested cleaning from the in-room console. Visible to housekeeping on the kanban so they know which rooms to prioritise.",
    )
    hb_card_present = fields.Boolean(
        string='Present card in reader',
        related='door_id.hb_card_present',
        help="True while a card is inserted in the room's energy-saver reader. Used by the kanban to switch the guest icon between present / absent and to gate the Last Insert Card label.",
    )

    # log = fields.One2many(comodel_name='sch_encoder.encoder.log', inverse_name='room_id')
    # bms_log_ids = fields.One2many(comodel_name='sch_encoder.bms.log', inverse_name='room_id')
    last_temperature = fields.Float(
        string='Temperature',
        compute='_compute_temperature',
        help="Room temperature reported by the BMS sensor. Currently a stub value until a BMS sensor module is connected.",
    )
    last_humidity = fields.Float(
        string='Humidity',
        compute='_compute_temperature',
        help="Room humidity reported by the BMS sensor. Currently a stub value until a BMS sensor module is connected.",
    )
    last_occupancy = fields.Char(
        string='Occupancy',
        compute='_compute_temperature',
        help="Occupancy state reported by the BMS sensor. Currently a stub value until a BMS sensor module is connected.",
    )
    last_insert_name = fields.Char(
        string='Last Insert Card',
        compute='_compute_last_insert_name',
        help="Name of the employee or guest whose card was last inserted at the room's energy-saver reader. Shown only while a card is currently in the reader.",
    )

    @api.depends('hb_card_present')
    def _compute_last_insert_name(self):
        for r in self:
            last_event_id = self.env['hr.rfid.event.user'].search([
                ('door_id', '=', r.door_id.id),
                ('event_action', '=', '7')
            ], limit=1)
            r.last_insert_name = last_event_id.employee_id and last_event_id.employee_id.name or \
                                 last_event_id.contact_id and last_event_id.contact_id.name or 'Unknown'
            # if not r.last_insert_name:
            #     r.last_insert_name = 'Unknown'

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

    # @api.depends('bms_log_ids')
    def _compute_temperature(self):
        for r in self:
            r.last_humidity = 45.7
            r.last_occupancy = 1
            r.last_temperature = 21.5
            continue

            last_log = r.bms_log_ids.search([
                ('room_id', '=', r.id),
                ('temperature', '!=', False)], limit=1)
            if last_log:
                r.last_temperature = last_log.temperature
            else:
                r.last_temperature = 0.00

            last_log = r.bms_log_ids.search([
                ('room_id', '=', r.id),
                ('occupancy', '!=', False)], limit=1)
            if last_log:
                r.last_occupancy = last_log.occupancy
            else:
                r.last_occupancy = False

    @api.constrains('number')
    def _check_number(self):
        for record in self:
            if record.number < 1 or record.number > 65535:
                raise ValidationError(_('Room number have to be between 1 and 65535'))

    _sql_constraints = [
        ('unique_room_number', 'unique(number)', _("Duplicate room number.")),
    ]
