import json
from datetime import timedelta

from odoo import fields, models, api, exceptions, _

import logging
_logger = logging.getLogger(__name__)

action_selection = [
        ('0', _('Unknown Event?')),
        ('1', _('DuressOK')),
        ('2', _('DuressError')),
        ('3', _('R1 Card OK')),  # User Event
        ('4', _('R1 Card Error')),  # User Event
        ('5', _('R1 T/S Error')),  # User Event
        ('6', _('R1 APB Error')),  # User Event
        ('7', _('R2 Card OK')),  # User Event
        ('8', _('R2 Card Error')),  # User Event
        ('9', _('R2 T/S Error')),  # User Event
        ('10', _('R2 APB Error')),  # User Event
        ('11', _('R3 Card OK')),  # User Event
        ('12', _('R3 Card Error')),  # User Event
        ('13', _('R3 T/S Error')),  # User Event
        ('14', _('R3 APB Error')),  # User Event
        ('15', _('R4 Card Ok')),  # User Event
        ('16', _('R4 Card Error')),  # User Event
        ('17', _('R4 T/S Error')),  # User Event
        ('18', _('R4 APB Error')),  # User Event
        ('19', _('Fire/Emergency')),
        ('20', _('Siren ON/OFF')),
        ('21', _('Exit button')),
        ('22', _('OpenDoor2 from In2')),  # deprecated
        ('23', _('OpenDoor3 from In3')),  # deprecated
        ('24', _('OpenDoor4 from In4')),  # deprecated
        ('25', _('Door Overtime')),
        ('26', _('Forced Door Open')),
        ('27', _('DELAY ZONE ON (if out) Z4,Z3,Z2,Z1')),
        ('28', _('DELAY ZONE OFF (if in) Z4,Z3,Z2,Z1')),
        ('29', _('External Control')),
        ('30', _('Power On event')),
        ('31', _('Open/Close Door From PC')),
        ('32', _('reserved')),
        ('33', _('Zone Arm/Disarm Denied')),  # User Event
        ('34', _('Zone Status')),
        ('35', _('Zone Arm/Disarm')),  # User Event
        ('36', _('Inserted Card')),  # User Event
        ('37', _('Ejected Card')),  # User Event
        ('38', _('Hotel Button Pressed')),  # User Event
        ('45', _('1-W ERROR (wiring problems)')),
        ('47', _('Vending Purchase Complete')),
        ('48', _('Vending Error1')),
        ('49', _('Vending Error2')),
        ('50', _('Vending collect to card')),
        ('51', _('Temperature High')),
        ('52', _('Temperature Normal')),
        ('53', _('Temperature Low')),
        ('54', _('Temperature Error')),
        ('64', _('Cloud Card Request')),  # User Event
        ('99', _('System Event')),
    ]

class HrRfidSystemEvent(models.Model):
    _name = 'hr.rfid.event.system'
    _inherit = ['hr.rfid.event', 'mail.thread']
    _description = 'RFID System Event'
    _order = 'timestamp desc'

    name = fields.Char(
        compute='_compute_sys_ev_name'
    )

    webstack_id = fields.Many2one(
        'hr.rfid.webstack',
        string='Module',
        help='Module affected by this event',
        ondelete='cascade',
    )

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        string='Controller',
        help='Controller affected by this event',
        ondelete='cascade',
    )

    door_id = fields.Many2one(
        'hr.rfid.door',
        string='Door',
        help='Door affected by this event',
        ondelete='cascade',
    )

    alarm_line_id = fields.Many2one(
        'hr.rfid.ctrl.alarm',
        string='Alarm line',
        help='Alarm line affected by this event',
        ondelete='cascade',
    )

    siren = fields.Boolean(
        help='Alarm detected and Siren is ON',
        default=False
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

    event_nums = list(map(lambda a: a[0], action_selection))

    event_action = fields.Selection(
        selection=action_selection,
        string='Event Type',
        default='99'
    )

    error_description = fields.Char(
        string='Description',
        help='Description on why the error happened',
    )

    card_number = fields.Char(
        string='Card number from this event',
        readonly=True
    )

    input_js = fields.Char(
        string='Input JSON',
    )

    is_card_event = fields.Boolean(compute='_compute_is_card_event')

    @api.depends('event_action')
    def _compute_is_card_event(self):
        for e in self:
            e.is_card_event = e.event_action in ['4', '8', '12', '16', '64']

    @api.autovacuum
    def _gc_events_life(self):
        for c in self.env['res.company'].search([]):
            if c.event_lifetime is None:
                return False
            # self._cr.execute("""
            #                        DELETE FROM hr_rfid_event_system
            #                        WHERE timestamp < NOW() - INTERVAL '%s days'
            #                    """, [c.event_lifetime])
            # _logger.info("GC'd %d old rfid system event entries", self._cr.rowcount)
            res = self.with_company(c).search([
                ('timestamp', '<', fields.Datetime.now() - timedelta(days=int(c.event_lifetime)))
            ], limit=1000)
            res.unlink()

        return True

    @api.depends('webstack_id.name', 'controller_id.name', 'timestamp')
    def _compute_sys_ev_name(self):
        for record in self:
            key_val_dict = dict(record._fields['event_action'].selection)
            record.name = key_val_dict[record.event_action] + ' on ' + str(record.webstack_id.name) + '/' + str(
                record.controller_id.name)
            #               ' at ' + str(record.timestamp)

    def _check_save_comms(self, vals):
        save_comms = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.save_webstack_communications') in [
            'true', 'True']
        if not save_comms:
            if 'input_js' not in vals:
                return

            if 'error_description' in vals and vals['error_description'] == 'Could not find the card':
                try:
                    js = json.loads(vals['input_js'])
                    vals['input_js'] = js['event']['card']
                finally:
                    return
            else:
                vals.pop('input_js')

    def _check_duplicate_sys_ev(self, vals):
        if not vals['webstack_id']:
            return False
        dupe = self.env['hr.rfid.event.system'].search([
            ('webstack_id', '=', vals['webstack_id']),
        ], limit=1)

        if not dupe:
            return False

        if vals.get('controller_id', False) != dupe.controller_id.id:
            return False

        if vals.get('door_id', False) != dupe.controller_id.id:
            return False

        if vals.get('alarm_line_id', False) != dupe.controller_id.id:
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
            record = super(HrRfidSystemEvent, self).create([vals])
            if record.door_id and record.door_id.zone_ids:
                record.door_id.zone_ids.process_event(record)
            elif not record.door_id and record.controller_id and record.controller_id.door_ids:
                zone_ids = record.controller_id.door_ids and record.controller_id.door_ids.zone_ids
                zone_ids.process_event(record)
            records += record

            if 'siren' in vals and 'event_action' in vals and vals.get('event_action') == '20':
                for e in records.with_context(no_output=True):
                    e.controller_id.siren_state = vals.get('siren')

        return records

    def zone_process_event(self):
        for rec in self:
            zones = rec.door_id.zone_ids if rec.door_id else None
            if zones:
                zones.process_event(rec)
            elif not rec.door_id and rec.controller_id and rec.controller_id.door_ids:
                zone_ids = rec.controller_id.door_ids.zone_ids
                zone_ids.process_event(rec)

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

        if type(sys_ev.card_number) != type(''):
            raise exceptions.ValidationError(_('System event does not have a card number in it'))

        if len(sys_ev.card_number) == 10:
            return sys_ev.card_number

        js = json.loads(sys_ev.input_js)
        try:
            card_number = js['event']['card']
            return card_number
        except KeyError as e:
            raise exceptions.ValidationError(_('System event does not have a card number in it'))

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
        default=_default_card_number,
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
