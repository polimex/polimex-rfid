from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SchEncoderRoom(models.Model):
    _name = 'rfid_pms_base.room'
    _description = 'Rooms'

    name = fields.Char(required=True)
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

    # log = fields.One2many(comodel_name='sch_encoder.encoder.log', inverse_name='room_id')
    # bms_log_ids = fields.One2many(comodel_name='sch_encoder.bms.log', inverse_name='room_id')
    last_temperature = fields.Float(string='Temperature', compute='_compute_temperature')
    last_humidity = fields.Float(string='Humidity', compute='_compute_temperature')
    last_occupancy = fields.Char(string='Occupancy', compute='_compute_temperature')

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
        if 0 > self.number > 65535:
            raise ValidationError(_('Room number have to be between 1 and 65535'))

    _sql_constraints = [
        ('unique_room_number', 'unique(number)', _("Duplicate room number.")),
    ]

    


