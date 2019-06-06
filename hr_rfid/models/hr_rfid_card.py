# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions
from datetime import timedelta, datetime
from enum import Enum


class OwnerType(Enum):
    Employee = 1
    Contact = 2


class HrRfidCard(models.Model):
    _name = 'hr.rfid.card'
    _description = 'Card'
    _inherit = ['mail.thread']

    def _get_cur_employee_id(self):
        return self.env.context.get('employee_id', None)

    name = fields.Char(
        compute='_compute_card_name',
    )

    number = fields.Char(
        string='Card Number',
        required=True,
        limit=10,
        index=True,
        track_visibility='onchange',
    )

    card_type = fields.Many2one(
        'hr.rfid.card.type',
        string='Card type',
        help='Only doors that support this type will be able to open this card',
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_card_type_def').id,
        track_visibility='onchange',
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Card Owner (Employee)',
        ondelete='cascade',
        default=_get_cur_employee_id,
        track_visibility='onchange',
    )

    contact_id = fields.Many2one(
        'res.partner',
        string='Card Owner (Partner)',
        ondelete='cascade',
        default=0,
        track_visibility='onchange',
    )

    user_event_ids = fields.One2many(
        'hr.rfid.event.user',
        'card_id',
        string='Events',
        help='Events concerning this user',
    )

    activate_on = fields.Datetime(
        string='Activate on',
        help='Date and time the card will be activated on',
        track_visibility='onchange',
        default=lambda self: datetime.now(),
    )

    deactivate_on = fields.Datetime(
        string='Deactivate on',
        help='Date and time the card will be deactivated on',
        track_visibility='onchange',
    )

    card_active = fields.Boolean(
        string='Active',
        help='Whether the card is active or not',
        track_visibility='onchange',
        default=True,
    )

    # TODO Implement at some point
    # internal_number = fields.Char(
    #     limit=10,
    #     index=True
    # )

    def get_owner(self):
        if len(self.employee_id) == 1:
            return self.employee_id
        return self.contact_id

    def get_owner_type(self):
        if len(self.employee_id) == 1:
            return OwnerType.Employee
        return OwnerType.Contact

    @api.one
    def toggle_card_active(self):
        self.card_active = not self.card_active

    @api.multi
    @api.constrains('number')
    def _check_number(self):
        for card in self:
            if len(card.number) != 10:
                raise exceptions.ValidationError('Card number must be exactly 10 digits')

            try:
                for char in card.number:
                    int(char, 10)
            except ValueError:
                raise exceptions.ValidationError('Card number digits must be from 0 to 9')

    @api.multi
    def _compute_card_name(self):
        for record in self:
            record.name = record.number

    _sql_constraints = [ ('rfid_card_number_unique', 'unique(number)',
                          'Card numbers must be unique!') ]

    @api.multi
    def unlink(self):
        cmd_env = self.env['hr.rfid.command']

        for card in self:
            owner = card.get_owner()
            if card.card_active is True:
                for door_rel in owner.hr_rfid_access_group_id.all_door_ids:
                    door = door_rel.door_id
                    ts = door_rel.time_schedule_id
                    pin = owner.hr_rfid_pin_code
                    cmd_env.remove_card(door.id, ts.id, pin, card_id=card.id)
        return super(HrRfidCard, self).unlink()

    @api.multi
    def write(self, vals):
        cmd_env       = self.env['hr.rfid.command']
        new_number    = vals.get('number',      None)
        new_card_type = vals.get('card_type',   None)
        new_active    = vals.get('card_active', None)

        invalid_user_and_contact_msg = 'Card user and contact cannot both be set' \
                                       ' in the same time, and cannot both be empty.'

        for card in self:
            old_number = str(card.number)[:]
            old_owner = card.get_owner()
            old_owner_type = card.get_owner_type()
            old_active = card.card_active
            old_card_type_id = card.card_type.id

            super(HrRfidCard, card).write(vals)
            if (len(card.employee_id) == len(card.contact_id)
                    or (len(card.employee_id) > 0 and len(card.contact_id) > 0)):
                raise exceptions.ValidationError(invalid_user_and_contact_msg)

            if new_active == old_active and new_active is False:
                continue

            new_owner = card.get_owner()
            new_owner_type = card.get_owner_type()

            if new_owner_type != old_owner_type or new_owner != old_owner:
                for door_rel in old_owner.hr_rfid_access_group_id.all_door_ids:
                    door = door_rel.door_id
                    ts = door_rel.time_schedule_id
                    pin = old_owner.hr_rfid_pin_code
                    if door.card_type.id == old_card_type_id:
                        cmd_env.remove_card(door.id, ts.id, pin, card_number=old_number)
                for door_rel in new_owner.hr_rfid_access_group_id.all_door_ids:
                    door = door_rel.door_id
                    ts = door_rel.time_schedule_id
                    pin = old_owner.hr_rfid_pin_code
                    if door.card_type.id == card.card_type.id:
                        cmd_env.add_card(door.id, ts.id, pin, card.number)
                continue

            if new_number is not None and new_number != old_number:
                for door_rel in new_owner.hr_rfid_access_group_id.all_door_ids:
                    door = door_rel.door_id
                    ts = door_rel.time_schedule_id
                    pin = new_owner.hr_rfid_pin_code
                    if door.card_type.id == old_card_type_id:
                        cmd_env.remove_card(door.id, ts.id, pin, card_number=old_number)
                    if door.card_type.id == card.card_type.id:
                        cmd_env.add_card(door.id, ts.id, pin, card.id)
                continue

            if new_card_type is not None and new_card_type != old_card_type_id:
                for door_rel in new_owner.hr_rfid_access_group_id.all_door_ids:
                    door = door_rel.door_id
                    ts = door_rel.time_schedule_id
                    pin = new_owner.hr_rfid_pin_code
                    if door.card_type.id == old_card_type_id:
                        cmd_env.remove_card(door.id, ts.id, pin, card_number=old_number)
                    if door.card_type.id == card.card_type.id:
                        cmd_env.add_card(door.id, ts.id, pin, card_id=card.id)
                continue

            if new_active is not None and new_active != old_active:
                for door_rel in new_owner.hr_rfid_access_group_id.all_door_ids:
                    door = door_rel.door_id
                    ts = door_rel.time_schedule_id
                    pin = new_owner.hr_rfid_pin_code
                    if new_active is True:
                        cmd_env.add_card(door.id, ts.id, pin, card_id=card.id)
                    if new_active is False:
                        cmd_env.remove_card(door.id, ts.id, pin, card_id=card.id, ignore_active=True)

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        for val in vals:
            new_user      = val.get('employee_id',    None)
            new_contact   = val.get('contact_id', None)

            if new_user is not None and new_contact is not None:
                if new_user == new_contact or (new_user > 0 and new_contact > 0):
                    raise exceptions.ValidationError('Card user and contact cannot both be set '
                                                     'in the same time, and cannot both be empty.')

        records = self.env['hr.rfid.card']
        for val in vals:
            card = super(HrRfidCard, self).create([val])
            cmd_env = self.env['hr.rfid.command']
            records = records + card
            card_owner = card.get_owner()

            if card.card_active is True:
                for door_rel in card_owner.hr_rfid_access_group_id.all_door_ids:
                    door = door_rel.door_id
                    ts = door_rel.time_schedule_id
                    pin = card_owner.hr_rfid_pin_code
                    cmd_env.add_card(door.id, ts.id, pin, card_id=card.id)

        return records

    @api.model
    def _update_cards(self):
        cenv = self.env['hr.rfid.card']
        now = fields.datetime.now()
        str_before = str(now - timedelta(seconds=31))
        str_after  = str(now + timedelta(seconds=31))
        cards_to_activate = cenv.search([ ('activate_on', '<', str_after),
                                          ('activate_on', '>', str_before) ])
        cards_to_deactivate = cenv.search([ ('deactivate_on', '<', str_after),
                                            ('deactivate_on', '>', str_before) ])

        neutral_cards = cards_to_activate & cards_to_deactivate
        cards_to_activate = cards_to_activate - neutral_cards
        cards_to_deactivate = cards_to_deactivate - neutral_cards

        if len(neutral_cards) > 0:
            to_activate = neutral_cards.filtered(lambda c: c.activate_on >= c.deactivate_on)
            cards_to_activate = cards_to_activate + to_activate
            cards_to_deactivate = cards_to_deactivate + (neutral_cards - to_activate)

        cards_to_activate.write({'card_active': True})
        cards_to_deactivate.write({'card_active': False})


class HrRfidCardType(models.Model):
    _name = 'hr.rfid.card.type'
    _inherit = ['mail.thread']
    _description = 'Card Type'

    name = fields.Char(
        string='Type Name',
        help='Label to differentiate types with',
        required=True,
        track_visibility='onchange',
    )

    card_ids = fields.One2many(
        'hr.rfid.card',
        'card_type',
        string='Cards',
        help='Cards of this card type',
    )

    door_ids = fields.One2many(
        'hr.rfid.door',
        'card_type',
        string='Doors',
        help='Doors that will open to this card type',
    )

    _sql_constraints = [ ('rfid_card_type_unique', 'unique(name)', 'Card types must be unique!') ]

    @api.multi
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



































