# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from datetime import timedelta, datetime
from enum import Enum
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

    number = fields.Char(
        string='Card Number',
        required=True,
        size=10,
        index=True,
        tracking=True,
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
        default=lambda self: datetime.now(),
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

    _sql_constraints = [
        ('card_uniq', 'unique (number, company_id)', _("Card number already exists!")),
    ]

    # @api.model
    # def default_get(self, fields):
    #     res = super(HrRfidCard, self).default_get(fields)
    #     if not 'employee_id' in res.keys() and self.env.context.get('default_employee_id', None):
    #         res['employee_id'] = self.env.context.get('default_employee_id', None)
    #     if not 'contact_id' in res.keys() and self.env.context.get('default_contact_id', None):
    #         res['contact_id'] = self.env.context.get('default_contact_id', None)
    #     return res

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
            access_groups = owner.hr_rfid_access_group_ids.mapped('access_group_id')
        else:
            owner = self.get_owner()
            valid_access_groups = owner.hr_rfid_access_group_ids.mapped('access_group_id')
            if access_groups not in valid_access_groups:
                return []
        door_rel_ids = access_groups.mapped('all_door_ids')
        return [(rel.door_id, rel.time_schedule_id, rel.alarm_rights) for rel in door_rel_ids]

    def door_compatible(self, door_id):
        return self.card_type == door_id.card_type \
               and not (self.cloud_card is True and door_id.controller_id.external_db is True)

    def card_ready(self):
        return self.active

    @api.onchange('activate_on', 'number')
    def _check_activate_on(self):
        for c in self:
            c.active = c.activate_on and c.activate_on <= fields.Datetime.now()
            # c.active = c.activate_on and (c.activate_on + timedelta(seconds=30)) <= fields.Datetime.now()

    @api.depends('employee_id', 'contact_id')
    def _compute_pin_code(self):
        for card in self:
            card.pin_code = card.get_owner().hr_rfid_pin_code

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
            dupes = self.search([('number', '=', card.number), ('card_type', '=', card.card_type.id), ('company_id', '=', card.company_id.id)])
            # dupes = self.end['hr.rfid.card'].with_company(card.company_id).search([('number', '=', card.number), ('card_type', '=', card.card_type.id)])
            if len(dupes) > 1:
                raise exceptions.ValidationError(_('Card number must be unique for every card type!'))

            if len(card.number) > 10:
                raise exceptions.ValidationError(_('Card number must be exactly 10 digits'))

            # if len(card.number) < 10:
            #     zeroes = 10 - len(card.number)
            #     card.number = (zeroes * '0') + card.number

            try:
                for char in card.number:
                    int(char, 10)
            except ValueError:
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
            card = super(HrRfidCard, self).create([val])
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
            old_number = str(card.number)[:]
            old_owner = card.get_owner()
            old_active = card.active
            old_card_type_id = card.card_type
            old_cloud = card.cloud_card

            super(HrRfidCard, card).write(vals)

            if len(card.employee_id) > 0 and len(card.contact_id) > 0:
                raise exceptions.ValidationError(invalid_user_and_contact_msg)

            if len(card.employee_id) == 0 and len(card.contact_id) == 0:
                raise exceptions.ValidationError(invalid_user_and_contact_msg)

            if old_number != card.number:
                card.door_rel_ids.card_number_changed(old_number)

            if old_owner != card.get_owner():
                old_owner_doors = old_owner.get_doors()
                new_owner_doors = card.get_owner().get_doors()
                removed_doors = old_owner_doors - new_owner_doors
                added_doors = new_owner_doors - old_owner_doors
                for door in removed_doors:
                    rel_env.remove_rel(card, door)
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

    def unlink(self):
        for card in self:
            card.door_rel_ids.unlink()
        return super(HrRfidCard, self).unlink()

    @api.model
    def _update_cards(self):
        now = fields.datetime.now()
        str_before = str(now - timedelta(seconds=31))
        str_after = str(now + timedelta(seconds=31))
        cards_to_activate = self.env['hr.rfid.card'].search(['|', ('active', '=', True), ('active', '=', False),
                                         ('activate_on', '<', str_after),
                                         ('activate_on', '>', str_before)])
        cards_to_deactivate = self.env['hr.rfid.card'].search(['|', ('active', '=', True), ('active', '=', False),
                                           ('deactivate_on', '<', str_after),
                                           ('deactivate_on', '>', str_before)])

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

    def return_action_doors(self):
        self.ensure_one()
        domain = [('id', 'in', [d.id for d in self.door_ids])]
        res = self.env['ir.actions.act_window']._for_xml_id('hr_rfid.hr_rfid_door_action')
        res.update(
            context=dict(self.env.context, group_by=False),
            domain=domain
        )
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
