# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from datetime import timedelta, datetime
from enum import Enum
import secrets
import logging

_logger = logging.getLogger(__name__)


class OwnerType(Enum):
    Employee = 1
    Contact = 2


class HrRfidCard(models.Model):
    _name = 'hr.rfid.card'
    _description = 'Card'
    _inherit = ['mail.thread']

    name = fields.Char(
        compute='_compute_card_name',
    )

    internal_number = fields.Char(
        index=True,
        store=True,
        compute='_compute_internal_number'
    )
    number = fields.Char(
        string='Card Number',
        required=True,
        size=10,
        index=True,
        tracking=True,
    )

    card_input_type = fields.Selection(
        selection=[
            ('w34','Wiegand 34 bit (5d+5d)'),
            ('w34s','Wiegand 34 bit (10d)'),
        ],
        default=lambda self: self.env.company.card_input_type or 'w34'
    )

    card_reference = fields.Char(
        string='Card reference',
        help='Card reference provide human recognizable label or any other text. It can be used for Badge Printed ID, or other identification',
        index=True,

    )

    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)

    card_type = fields.Many2one(
        'hr.rfid.card.type',
        string='Card type',
        help='Only doors that support this type will be able to open this card',
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_card_type_def').id,
        tracking=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Card Owner (Employee)',
        default=lambda self: self.env.context.get('default_employee_id', None),
        tracking=True,
    )

    contact_id = fields.Many2one(
        'res.partner',
        string='Card Owner (Partner)',
        default=lambda self: self.env.context.get('default_contact_id', None),
        tracking=True,
        domain=[('is_company', '=', False)],
    )

    activate_on = fields.Datetime(
        string='Activate on',
        help='Date and time the card will be activated on',
        tracking=True,
        default=lambda self: fields.Datetime.now(),
        index=True,
    )

    deactivate_on = fields.Datetime(
        string='Deactivate on',
        help='Date and time the card will be deactivated on',
        tracking=True,
        index=True,
    )

    active = fields.Boolean(
        string='Active',
        help='Whether the card is active or not',
        tracking=True,
        default=True,
    )

    cloud_card = fields.Boolean(
        string='Cloud Card',
        help='A cloud card will not be added to controllers that are in the "externalDB" mode.',
        tracking=True,
        default=True,
        required=True,
    )

    door_rel_ids = fields.One2many(
        'hr.rfid.card.door.rel',
        'card_id',
        string='Doors',
        help='Doors this card has access to',
    )

    door_ids = fields.Many2many(
        'hr.rfid.door',
        string='Doors',
        compute='_compute_door_ids',
    )

    door_count = fields.Char('Door Count', compute='_compute_door_ids')

    pin_code = fields.Char(compute='_compute_pin_code')

    barcode_number = fields.Char(compute='_compute_barcode_number')
    is_barcode = fields.Boolean(compute='_compute_barcode_number')

    _sql_constraints = [
        ('card_uniq', 'unique (number, company_id)', _("Card number already exists!")),
        ('card_int_uniq', 'unique (internal_number, company_id)', _("Card internal number already exists!")),
        ('check_card_owner',
         'check((contact_id is null and employee_id is not null) or (contact_id is not null and employee_id is null))',
         'Card user and contact cannot both be set in the same time, and cannot both be empty.')

    ]

    @api.depends('number','card_input_type')
    def _compute_internal_number(self):
        for c in self:
            if c.number and c.card_input_type:
                c._check_len_number()
                if c.card_input_type == 'w34s':
                    h4 = '{:08X}'.format(int(c.number))
                    # Split the 8-character hex string into two parts
                    part1, part2 = h4[:4], h4[4:]
                    # Convert each part to decimal
                    dec1 = '{:05}'.format(int(part1, 16))
                    dec2 = '{:05}'.format(int(part2, 16))
                    c.internal_number = dec1+dec2
                else:
                    c.internal_number = c.number
            else:
                c.internal_number=''

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Cards'),
            'template': '/hr_rfid/static/xls/Polimex RFID card import template.xls'
        }]

    def get_owner(self, event_dict: dict = None):
        self.ensure_one()
        if not event_dict:
            return self.employee_id or self.contact_id or None
        else:
            if self.contact_id:
                event_dict['contact_id'] = self.contact_id.id
            elif self.employee_id:
                event_dict['employee_id'] = self.employee_id.id
            else:
                _logger.warning('The requested card ({}) have no owner'.format(self.number))

    def get_potential_access_doors(self, access_groups=None):
        """
        Returns a list of tuples (door, time_schedule, alarm_rights) the card potentially has access to
        """
        if access_groups is None:
            owner = self.get_owner()
            access_groups = owner.hr_rfid_access_group_ids._filter_active().mapped('access_group_id')
        else:
            owner = self.get_owner()
            valid_access_groups = owner.hr_rfid_access_group_ids._filter_active().mapped('access_group_id')
            if access_groups not in valid_access_groups:
                return []
        door_rel_ids = access_groups.mapped('all_door_ids')
        return [(rel.door_id, rel.time_schedule_id, rel.alarm_rights) for rel in door_rel_ids]

    def door_compatible(self, door_id):
        return self.card_type == door_id.card_type \
            and not (self.cloud_card is True and door_id.controller_id.external_db is True)

    def card_ready(self):
        res = []
        for c in self:
            res.append(c.active)
            if c.activate_on:
                res.append(c.activate_on <= fields.Datetime.now())
            else:
                res.append(True)
            if c.deactivate_on:
                res.append(c.deactivate_on > fields.Datetime.now())
            else:
                res.append(True)
        return len(res) > 0 and all(res)

    @api.onchange('activate_on', 'number')
    def _check_activate_on(self):
        for c in self:
            c.active = c.activate_on and c.activate_on <= fields.Datetime.now()
            # c.active = c.activate_on and (c.activate_on + timedelta(seconds=30)) <= fields.Datetime.now()

    @api.depends('employee_id', 'contact_id')
    def _compute_pin_code(self):
        for card in self:
            card.pin_code = card.get_owner().hr_rfid_pin_code
    @api.depends('number', 'card_type')
    def _compute_barcode_number(self):
        for c in self:
            c.barcode_number = c.number and self.w34_to_hex(c.number).upper() or False
            c.is_barcode = c.card_type == self.env.ref('hr_rfid.hr_rfid_card_type_barcode')

    @api.constrains('employee_id', 'contact_id')
    def _check_user(self):
        for card in self:
            if card.employee_id is not None and card.contact_id is not None:
                if card.employee_id == card.contact_id or \
                        (len(card.employee_id) > 0 and len(card.contact_id) > 0):
                    raise exceptions.ValidationError('Card user and contact cannot both be set '
                                                     'in the same time, and cannot both be empty.')

    @api.onchange('number')
    def _check_len_number(self):
        for card in self:
            if card.number:
                if len(card.number) < 10:
                    zeroes = 10 - len(card.number)
                    card.number = (zeroes * '0') + card.number
                elif len(card.number) > 10:
                    raise exceptions.UserError(_('Card number must be exactly 10 digits'))

    @api.constrains('number')
    def _check_number(self):
        for card in self:
            dupes = self.search([('number', '=', card.number), ('card_type', '=', card.card_type.id),
                                 ('company_id', '=', card.company_id.id)])
            # dupes = self.end['hr.rfid.card'].with_company(card.company_id).search([('number', '=', card.number), ('card_type', '=', card.card_type.id)])
            if len(dupes) > 1:
                raise exceptions.ValidationError(_('Card number must be unique for every card type!'))

            if len(card.number) > 10:
                raise exceptions.ValidationError(_('Card number must be exactly 10 digits'))

            if not card.number.isdigit():
                raise exceptions.ValidationError('Card number digits must be from 0 to 9')


    @api.depends('card_reference', 'number')
    def _compute_card_name(self):
        for record in self:
            record.name = record.card_reference or record.number

    @api.depends('door_rel_ids')
    def _compute_door_ids(self):
        for card in self:
            card.door_ids = card.door_rel_ids.mapped('door_id')
            card.door_count = len(card.door_ids)

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        card_door_rel_env = self.env['hr.rfid.card.door.rel']
        invalid_user_and_contact_msg = _('Card user and contact cannot both be set' \
                                         ' in the same time, and cannot both be empty.')

        records = self.env['hr.rfid.card']
        for val in vals:
            if 'card_type' in val and val['card_type'] == self.env.ref('hr_rfid.hr_rfid_card_type_barcode').id:
                val['card_input_type'] = 'w34'
            card = super(HrRfidCard, self).create([val])
            card._check_len_number()
            records = records + card

            if card.employee_id and card.contact_id:
                raise exceptions.ValidationError(invalid_user_and_contact_msg)

            if not card.employee_id and not card.contact_id:
                raise exceptions.ValidationError(invalid_user_and_contact_msg)

            card_door_rel_env.update_card_rels(card)

        return records

    def write(self, vals):
        rel_env = self.env['hr.rfid.card.door.rel']
        invalid_user_and_contact_msg = 'Card user and contact cannot both be set' \
                                       ' in the same time, and cannot both be empty.'

        for card in self:
            old_number = str(card.internal_number)[:]
            old_owner = card.get_owner()
            old_active = card.active
            old_card_type_id = card.card_type
            old_cloud = card.cloud_card

            super(HrRfidCard, card).write(vals)

            if len(card.employee_id) > 0 and len(card.contact_id) > 0:
                raise exceptions.ValidationError(invalid_user_and_contact_msg)

            if len(card.employee_id) == 0 and len(card.contact_id) == 0:
                raise exceptions.ValidationError(invalid_user_and_contact_msg)

            if old_number != card.internal_number:
                # card._compute_internal_number()
                card.door_rel_ids.card_number_changed(old_number)

            if old_owner != card.get_owner() and old_owner:
                old_owner_doors = old_owner.get_doors()
                new_owner_doors = card.get_owner().get_doors()
                removed_doors = old_owner_doors - new_owner_doors
                added_doors = new_owner_doors - old_owner_doors
                rel_env._remove_cards(card, removed_doors)
                for door in added_doors:
                    rel_env.check_relevance_fast(card, door)

            if old_active != card.active:
                if card.active is False:
                    card.door_rel_ids.unlink()
                else:
                    rel_env.update_card_rels(card)

            if old_card_type_id != card.card_type:
                rel_env.update_card_rels(card)

            if old_cloud != card.cloud_card:
                rel_env.update_card_rels(card)

            if vals.keys() & ['activate_on', 'deactivate_on', 'active']:
                if card.card_ready():
                    rel_env.update_card_rels(card)
                else:
                    card.door_rel_ids.unlink()


    def unlink(self):
        for card in self:
            card.door_rel_ids.unlink()
        return super(HrRfidCard, self).unlink()

    @api.model
    def hex_to_w34(self, bc):
        return f"{int(bc[:4], 16):05}"f"{int(bc[4:], 16):05}"

    @api.model
    def w34_to_hex(self, w34):
        return f"{int(w34[:5]):04x}"f"{int(w34[5:]):04x}"

    @api.model
    def create_bc_card(self):
        i = 0
        while True:
            new_card_hex = secrets.token_hex(4)
            card_number = self.hex_to_w34(new_card_hex)
            card_ids = self.env['hr.rfid.card'].search([
                ('number', '=', card_number)
            ])
            if len(card_ids) == 0:
                return new_card_hex, card_number
            if i > 10:
                _logger.warning('Can not create barcode data. Random data duplicated 10 times!')
                return None, None
            i += 1

    @api.model
    def _update_cards(self):
        now = fields.datetime.now()
        str_before = str(now - timedelta(seconds=31))
        str_after = str(now + timedelta(seconds=31))
        # cards_to_activate = self.env['hr.rfid.card'].search(['|', ('active', '=', True), ('active', '=', False),
        #                                                      ('activate_on', '<', str_after),
        #                                                      ('activate_on', '>', str_before)])
        # cards_to_deactivate = self.env['hr.rfid.card'].search(['|', ('active', '=', True), ('active', '=', False),
        #                                                        ('deactivate_on', '<', str_after),
        #                                                        ('deactivate_on', '>', str_before)])
        # Cards to activate
        cards_to_activate = self.env['hr.rfid.card'].search([
            ('active', '=', False),
            ('activate_on', '<=', str_after),
            ('deactivate_on', '>=', str_after)])

        # Cards to deactivate
        cards_to_deactivate = self.env['hr.rfid.card'].search([
            ('active', '=', True),
            ('deactivate_on', '<=', str_before),])
                                                               # ('deactivate_on', '<=', str_after),
                                                               # ('deactivate_on', '>=', str_before)])

        neutral_cards = cards_to_activate & cards_to_deactivate
        cards_to_activate = cards_to_activate - neutral_cards
        cards_to_deactivate = cards_to_deactivate - neutral_cards

        if len(neutral_cards) > 0:
            to_activate = neutral_cards.filtered(lambda c: c.activate_on >= c.deactivate_on)
            cards_to_activate = cards_to_activate + to_activate
            cards_to_deactivate = cards_to_deactivate + (neutral_cards - to_activate)

        cards_to_activate.write({'active': True})
        cards_to_deactivate.write({'active': False})

    @api.model
    def do_cron_jobs(self):
        self._update_cards()
        self.env['hr.rfid.access.group.contact.rel']._check_expirations()
        self.env['hr.rfid.access.group.employee.rel']._check_expirations()
        self.env['hr.rfid.webstack']._notify_inactive()

    def return_action_doors(self):
        self.ensure_one()
        domain = [('id', 'in', [d.id for d in self.door_ids])]
        res = self.env['ir.actions.act_window']._for_xml_id('hr_rfid.hr_rfid_door_action')
        res.update(
            context=dict(self.env.context, group_by=False),
            domain=domain
        )
        return res

    def _message_auto_subscribe_followers(self, updated_values, subtype_ids):
        res = super(HrRfidCard, self)._message_auto_subscribe_followers(updated_values, subtype_ids)
        if updated_values.get('employee_id'):
            employee = self.env['hr.employee'].browse(updated_values['employee_id'])
            if employee.user_id:
                res.append((employee.user_id.partner_id.id, subtype_ids, False))
        if updated_values.get('contact_id'):
            res.append((updated_values.get('contact_id'), subtype_ids, False))
        return res


class HrRfidCardType(models.Model):
    _name = 'hr.rfid.card.type'
    _inherit = ['mail.thread']
    _description = 'Card Type'

    name = fields.Char(
        string='Type Name',
        help='Label to differentiate types with',
        required=True,
        tracking=True,
    )
    card_ids = fields.One2many(
        'hr.rfid.card',
        'card_type',
        string='Cards',
        help='Cards of this card type',
        context={'active_test': False},
    )

    door_ids = fields.One2many(
        'hr.rfid.door',
        'card_type',
        string='Doors',
        help='Doors that will open to this card type',
    )

    def unlink(self):
        default_card_type_id = self.env.ref('hr_rfid.hr_rfid_card_type_def').id

        for card_type in self:
            if card_type.id == default_card_type_id \
                    or len(card_type.card_ids) > 0 \
                    or len(card_type.door_ids) > 0:
                raise exceptions.ValidationError('Cannot delete the default card type or a card '
                                                 'type that is already used by doors or cards. '
                                                 'Please change the doors/cards types first.')

        return super(HrRfidCardType, self).unlink()

    def list_cards_from_this_type(self):
        self.ensure_one()
        return {
            'name': _('%s list' % self.name),
            'domain': [('card_type', '=', self.id)],
            # 'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'hr.rfid.card',
            'views': [[False, "tree"], [False, "form"]],
            'type': 'ir.actions.act_window',
            'context': {'active_test': False},
            # 'target': 'new',
        }
