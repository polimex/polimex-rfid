import json
from datetime import timedelta

from odoo import fields, models, api, exceptions


class HrRfidSystemEvent(models.Model):
    _name = 'hr.rfid.event.system'
    _description = 'RFID System Event'
    _order = 'timestamp desc'

    name = fields.Char(
        compute='_compute_sys_ev_name'
    )

    webstack_id = fields.Many2one(
        'hr.rfid.webstack',
        string='Module',
        help='Module affected by this event',
        default=None,
        ondelete='cascade',
    )

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        string='Controller',
        help='Controller affected by this event',
        default=None,
        ondelete='cascade',
    )

    timestamp = fields.Datetime(
        string='Timestamp',
        help='Time the event occurred',
        required=True,
        index=True,
    )

    occurrences = fields.Integer(
        string='Occurrences',
        help='Number of times the event has happened',
        default=1,
    )

    last_occurrence = fields.Datetime(
        string='Last occurrence',
    )

    action_selection = [
        ('0', 'Unknown Event?'),
        ('1', 'DuressOK'),
        ('2', 'DuressError'),
        ('3', 'R1 Card OK'),
        ('4', 'R1 Card Error'),
        ('5', 'R1 T/S Error'),
        ('6', 'R1 APB Error'),
        ('7', 'R2 Card OK'),
        ('8', 'R2 Card Error'),
        ('9', 'R2 T/S Error'),
        ('10', 'R2 APB Error'),
        ('11', 'R3 Card OK'),
        ('12', 'R3 Card Error'),
        ('13', 'R3 T/S Error'),
        ('14', 'R3 APB Error'),
        ('15', 'R4 Card Ok'),
        ('16', 'R4 Card Error'),
        ('17', 'R4 T/S Error'),
        ('18', 'R4 APB Error'),
        ('19', 'EmergencyOpenDoor'),
        ('20', 'ON/OFF Siren'),
        ('21', 'OpenDoor1 from In1'),
        ('22', 'OpenDoor2 from In2'),
        ('23', 'OpenDoor3 from In3'),
        ('24', 'OpenDoor4 from In4'),
        ('25', 'Dx Overtime'),
        ('26', 'ForcedOpenDx'),
        ('27', 'DELAY ZONE ON (if out) Z4,Z3,Z2,Z1'),
        ('28', 'DELAY ZONE OFF (if in) Z4,Z3,Z2,Z1'),
        ('29', ''),
        ('30', 'Power On event'),
        ('31', 'Open/Close Door From PC'),
        ('33', 'Siren On/Off from PC'),
        ('34', 'eZoneAlarm'),
        ('35', 'Zone Arm/Disarm'),
        ('36', 'Inserted Card'),
        ('37', 'Ejected Card'),
        ('38', 'Hotel Button Pressed'),
        ('45', '1-W ERROR (wiring problems)'),
        ('47', 'Vending Purchase Complete'),
        ('48', 'Vending Error1'),
        ('49', 'Vending Error2'),
        ('64', 'Vending Request User Balance'),
        ('67', 'Arm Denied'),
    ]

    event_nums = list(map(lambda a: a[0], action_selection))

    event_action = fields.Selection(
        selection=action_selection,
        string='Event Type',
    )

    error_description = fields.Char(
        string='Description',
        help='Description on why the error happened',
    )


    input_js = fields.Char(
        string='Input JSON',
    )

    is_card_event = fields.Boolean(compute='_compute_is_card_event')

    @api.depends('event_action')
    def _compute_is_card_event(self):
        for e in self:
            e.is_card_event = e.event_action in ['4','8','12','16']

    @api.autovacuum
    def _gc_events_life(self):
        event_lifetime = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.event_lifetime')
        if event_lifetime is None:
            return False

        lifetime = timedelta(days=int(event_lifetime))
        today = fields.Date.today()
        res = self.search([
            ('timestamp', '<', today-lifetime)
        ])
        res.unlink()

        return True

    def _compute_sys_ev_name(self):
        for record in self:
            record.name = str(record.webstack_id.name) + '-' + str(record.controller_id.name) +\
                          ' at ' + str(record.timestamp)

    def _check_save_comms(self, vals):
        save_comms = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.save_webstack_communications')
        if save_comms != 'True':
            if 'input_js' not in vals:
                return

            if 'error_description' in vals and vals['error_description'] == 'Could not find the card':
                js = json.loads(vals['input_js'])
                vals['input_js'] = js['event']['card']
            else:
                vals.pop('input_js')

    def _check_duplicate_sys_ev(self, vals):
        dupe = self.env['hr.rfid.event.system'].search([
            ('webstack_id', '=', vals['webstack_id']),
        ], limit=1)

        if not dupe:
            return False

        if vals.get('controller_id', False) != dupe.controller_id.id:
            return False

        if vals.get('event_action', False) != dupe.event_action:
            return False

        if vals.get('error_description', False) != dupe.error_description:
            return False

        if vals.get('input_js', False) != dupe.input_js:
            return False

        dupe.write({
            'last_occurrence': vals['timestamp'],
            'occurrences': dupe.occurrences + 1,
        })

        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = self.env['hr.rfid.event.system']

        for vals in vals_list:
            if 'event_action' in vals and vals['event_action'] not in self.event_nums:
                vals['event_action'] = '0'

            self._check_save_comms(vals)

            if self._check_duplicate_sys_ev(vals):
                continue

            if 'last_occurrence' not in vals:
                vals['last_occurrence'] = vals['timestamp']

            records += super(HrRfidSystemEvent, self).create([vals])

        return records

    def write(self, vals):
        self._check_save_comms(vals)
        return super(HrRfidSystemEvent, self).write(vals)


class HrRfidSystemEventWizard(models.TransientModel):
    _name = 'hr.rfid.event.sys.wiz'
    _description = 'Add card to employee/contact'

    def _default_sys_ev(self):
        return self.env['hr.rfid.event.system'].browse(self._context.get('active_ids'))

    def _default_card_number(self):
        sys_ev = self._default_sys_ev()

        if type(sys_ev.input_js) != type(''):
            raise exceptions.ValidationError('System event does not have a card number in it')

        if len(sys_ev.input_js) == 10:
            return sys_ev.input_js

        js = json.loads(sys_ev.input_js)
        try:
            card_number = js['event']['card']
            return card_number
        except KeyError as _:
            raise exceptions.ValidationError('System event does not have a card number in it')

    sys_ev_id = fields.Many2one(
        'hr.rfid.event.system',
        string='System event',
        required=True,
        default=_default_sys_ev,
        ondelete='cascade',
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Card owner (employee)',
    )

    contact_id = fields.Many2one(
        'res.partner',
        string='Card owner (contact)',
    )

    card_number = fields.Char(
        string='Card Number',
        default =_default_card_number,
    )

    card_type = fields.Many2one(
        'hr.rfid.card.type',
        string='Card type',
        help='Only doors that support this type will be able to open this card',
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_card_type_def').id,
    )

    activate_on = fields.Datetime(
        string='Activate on',
        help='Date and time the card will be activated on',
        default=lambda self: fields.Datetime.now(),
    )

    deactivate_on = fields.Datetime(
        string='Deactivate on',
        help='Date and time the card will be deactivated on',
    )

    active = fields.Boolean(
        string='Active',
        help='Whether the card is active or not',
        default=True,
    )

    cloud_card = fields.Boolean(
        string='Cloud Card',
        help='A cloud card will not be added to controllers that are in the "externalDB" mode.',
        default=True,
        required=True,
    )

    def add_card(self):
        self.ensure_one()

        if len(self.contact_id) == len(self.employee_id):
            raise exceptions.ValidationError(
                'Card cannot have both or neither a contact owner and an employee owner.'
            )

        card_env = self.env['hr.rfid.card']
        new_card = {
            'number': self.card_number,
            'card_type': self.card_type.id,
            'activate_on': self.activate_on,
            'deactivate_on': self.deactivate_on,
            'active': self.active,
            'cloud_card': self.cloud_card,
        }
        if len(self.contact_id) > 0:
            new_card['contact_id'] = self.contact_id.id
        else:
            new_card['employee_id'] = self.employee_id.id
        card_env.create(new_card)


