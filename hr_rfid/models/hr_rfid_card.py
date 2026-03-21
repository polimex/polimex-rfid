# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from datetime import timedelta, datetime
from enum import Enum
import secrets
import re
import logging

_logger = logging.getLogger(__name__)


class OwnerType(Enum):
    Employee = 1
    Contact = 2


class HrRfidCard(models.Model):
    _name = 'hr.rfid.card'
    _description = 'Card'
    _rec_names_search = ['number', 'card_reference', 'employee_id', 'contact_id']
    _inherit = ['mail.thread']

    name = fields.Char(
        compute='_compute_card_name',
        help='Display name of the card - shows either the card reference or card number',
    )

    internal_number = fields.Char(
        index=True,
        store=True,
        compute='_compute_internal_number',
        help='Internal representation of the card number used by the system. This is automatically calculated based on the card input type.'
    )
    number = fields.Char(
        string='Card Number',
        required=True,
        size=10,
        index=True,
        tracking=True,
        help='The unique 10-digit number printed on or associated with the RFID card. This is what the card readers recognize. Example: 0012345678',
    )

    card_input_type = fields.Selection(
        selection=[
            ('w34','Wiegand 34 bit (5d+5d)'),
            ('w34s','Wiegand 34 bit (10d)'),
        ],
        default=lambda self: self.env.company.card_input_type or 'w34',
        help='Technical format of how the card number is encoded. Wiegand 34 bit (5d+5d) splits the number into two 5-digit parts, while Wiegand 34 bit (10d) uses a single 10-digit format. This must match your card reader configuration.'
    )

    card_reference = fields.Char(
        string='Card reference',
        help='A friendly name or ID for this card, such as a badge number printed on the physical card (e.g., "Badge #37" or "Visitor Pass 5"). This makes it easier to identify cards without using the technical card number.',
        index=True,

    )

    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company,
                                 help='The company this card belongs to. Cards are isolated between companies for security.')

    card_type = fields.Many2one(
        'hr.rfid.card.type',
        string='Card type',
        help='Defines what kind of card this is (e.g., Employee Card, Visitor Card, Service Card). Doors must be configured to accept this card type for the card to work. Different card types can have different access privileges.',
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_card_type_def').id,
        tracking=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Card Owner (Employee)',
        default=lambda self: self.env.context.get('default_employee_id', None),
        tracking=True,
        help='The employee who owns this card. Each card must have either an employee or a contact as owner, but not both. The card will inherit access rights from the employee\'s access groups.',
    )

    contact_id = fields.Many2one(
        'res.partner',
        string='Card Owner (Partner)',
        default=lambda self: self.env.context.get('default_contact_id', None),
        tracking=True,
        domain=[('is_company', '=', False)],
        help='The external contact (visitor, contractor, supplier) who owns this card. Each card must have either an employee or a contact as owner, but not both. The card will inherit access rights from the contact\'s access groups.',
    )

    activate_on = fields.Datetime(
        string='Activate on',
        help='The date and time when this card becomes active and can be used. Perfect for temporary access or scheduled start dates. For example, set this to Monday 8:00 AM for a new employee starting that day.',
        tracking=True,
        default=lambda self: fields.Datetime.now(),
        index=True,
    )

    deactivate_on = fields.Datetime(
        string='Deactivate on',
        help='The date and time when this card will automatically expire and stop working. Useful for temporary visitors, contractors with end dates, or trial periods. Leave empty for cards that should not expire.',
        tracking=True,
        index=True,
    )

    active = fields.Boolean(
        string='Active',
        help='Controls whether this card is currently enabled. Inactive cards will not open any doors, even if they have access rights. Use this to temporarily disable a card without deleting it (e.g., during employee leave).',
        tracking=True,
        default=True,
    )

    cloud_card = fields.Boolean(
        string='Cloud Card',
        help='Cloud cards are managed centrally by the system and work with online controllers. Non-cloud cards are for offline/standalone controllers with their own database. Most cards should be cloud cards unless you have specific offline requirements.',
        tracking=True,
        default=True,
        required=True,
    )

    door_rel_ids = fields.One2many(
        'hr.rfid.card.door.rel',
        'card_id',
        string='Door list',
        help='Technical field linking this card to doors. The actual door access is determined by the card owner\'s access groups, not by direct card-to-door relationships.',
    )

    door_ids = fields.Many2many(
        'hr.rfid.door',
        string='Doors',
        compute='_compute_door_ids',
        help='List of all doors this card currently has access to, based on the owner\'s access groups and the card\'s active status. This is automatically calculated.',
    )

    door_count = fields.Char('Door Count', compute='_compute_door_ids', help='Total number of doors this card can open. Shown as a statistic on the card form.')

    pin_code = fields.Char(compute='_compute_pin_code', help='The PIN code associated with this card\'s owner. Used for doors that require both card and PIN for extra security.')

    barcode_number = fields.Char(compute='_compute_barcode_number', help='Hexadecimal representation of the card number, used for barcode printing and scanning.')
    is_barcode = fields.Boolean(compute='_compute_barcode_number', help='Indicates if this card is configured as a barcode card type.')

    _card_uniq = models.Constraint(
        'UNIQUE (number, company_id)',
        "Card number already exists!"
    )
    _card_int_uniq = models.Constraint(
        'UNIQUE (internal_number, company_id)',
        "Card internal number already exists!"
    )
    _check_card_owner = models.Constraint(
        'CHECK((contact_id IS NULL AND employee_id IS NOT NULL) OR (contact_id IS NOT NULL AND employee_id IS NULL))',
        'Card user and contact cannot both be set in the same time, and cannot both be empty.'
    )

    @api.depends('number','card_input_type')
    def _compute_internal_number(self):
        for c in self:
            if c.number and c.card_input_type:
                c._check_len_number()
                if c.card_input_type == 'w34s' and c.card_type != self.env.ref('hr_rfid.hr_rfid_card_type_8'):
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
        door_rel_ids = access_groups.sudo().mapped('all_door_ids')
        return [(rel.door_id, rel.time_schedule_id, rel.alarm_rights) for rel in door_rel_ids]

    def door_compatible(self, door_id):
        # door_id = self.env['hr.rfid.door'].sudo().browse(door_id.id)
        return self.card_type == door_id.card_type \
            and not (self.cloud_card and door_id.controller_id and door_id.controller_id.external_db)

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
                card.number = card.card_type.check_and_fix_card_numer(card.number)

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

            if not card.number.isdigit() and card.card_type != self.env.ref('hr_rfid.hr_rfid_card_type_8'):
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

            super().write(vals)

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
                    door_ids = card.get_owner().get_doors()
                    rel_env._remove_cards(card, door_ids)
                    # card.door_rel_ids.unlink()
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
                raise exceptions.UserError(_('Could not generate a unique barcode card number after %d attempts.', i))
            i += 1

    @api.model
    def _update_cards(self):
        now = fields.Datetime.now()
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
        help='Name for this card type (e.g., "Employee Card", "Visitor Pass", "Contractor Badge"). This helps categorize cards and control which doors they can access.',
        required=True,
        tracking=True,
    )
    card_ids = fields.One2many(
        'hr.rfid.card',
        'card_type',
        string='Cards',
        help='All RFID cards that belong to this card type. You can see which cards are using this type and manage them from here.',
        context={'active_test': False},
    )

    door_ids = fields.One2many(
        'hr.rfid.door',
        'card_type',
        string='Doors',
        help='Doors that are configured to accept this card type. Only cards of this type will be able to open these doors (assuming the card owner has proper access rights).',
    )

    def check_and_fix_card_numer(self, number):
        def normalize_plate(plate: str) -> str:
            mapping = {
                'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M',
                'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X',
                'У': 'Y',
                'а': 'A', 'в': 'B', 'е': 'E', 'к': 'K', 'м': 'M',
                'н': 'H', 'о': 'O', 'р': 'P', 'с': 'C', 'т': 'T', 'х': 'X',
                'у': 'Y',
            }
            result = []
            for ch in plate:
                if ch.isdigit():
                    result.append(ch)
                elif ch in mapping:
                    result.append(mapping[ch])
                elif 'A' <= ch <= 'Z' or 'a' <= ch <= 'z':
                    result.append(ch.upper())
            return ''.join(result)

        self.ensure_one()
        if self.id == self.env.ref('hr_rfid.hr_rfid_card_type_8').id:
            return normalize_plate(number)
        else:
            if len(number) < 10:
                zeroes = 10 - len(number)
                return (zeroes * '0') + number
            elif len(number) > 10:
                raise exceptions.UserError(_('Card number must be exactly 10 digits'))
            return number

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
            'view_mode': 'list',
            'res_model': 'hr.rfid.card',
            'views': [[False, "list"], [False, "form"]],
            'type': 'ir.actions.act_window',
            'context': {'active_test': False},
            # 'target': 'new',
        }
