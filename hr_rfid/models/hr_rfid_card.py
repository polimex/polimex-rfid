# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class HrRfidCard(models.Model):
    _name = 'hr.rfid.card'
    _description = 'Information about cards'

    def _get_cur_employee_id(self):
        return self.env.context.get('employee_id', None)

    name = fields.Char(
        compute='_compute_card_name',
    )

    number = fields.Char(
        string='Card Number',
        required=True,
        limit=10,
        index=True
    )

    card_type = fields.Many2one(
        'hr.rfid.card.type',
        string='Card type',
        help='Only doors that support this type will be able to open this card',
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_card_type_def').id,
    )

    user_id = fields.Many2one(
        'hr.employee',
        string='Card Owner',
        required=True,
        ondelete='cascade',
        default=_get_cur_employee_id,
    )

    user_event_ids = fields.One2many(
        'hr.rfid.event.user',
        'card_id',
        string='Events',
        help='Events concerning this user',
    )

    # TODO Implement at some point
    # internal_number = fields.Char(
    #     limit=10,
    #     index=True
    # )

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
            for door_rel in card.user_id.hr_rfid_access_group_id.door_ids:
                door = door_rel.door_id
                cmd_env.remove_card(door.id, door_rel.time_schedule_id.id,
                                    card.user_id.hr_rfid_pin_code, card_id=card.id)

        return super(HrRfidCard, self).unlink()

    @api.multi
    def write(self, vals):
        cmd_env = self.env['hr.rfid.command']
        new_number = vals.get('number', None)
        new_user = vals.get('user_id', None)
        new_card_type = vals.get('card_type', None)

        for card in self:
            old_number = None
            old_user = None
            old_card_type_id = None

            if new_number is not None and new_user is not None:
                old_number = str(card.number)[:]
                old_user = card.user_id
            elif new_number is not None:
                old_number = str(card.number)[:]
            elif new_user is not None:
                old_user = card.user_id

            if new_card_type is not None:
                old_card_type_id = card.card_type.id

            super(HrRfidCard, card).write(vals)

            if new_number is not None and new_user is not None:
                for door_rel in old_user.hr_rfid_access_group_id.door_ids:
                    door = door_rel.door_id
                    cmd_env.remove_card(door.id, door_rel.time_schedule_id.id,
                                        old_user.hr_rfid_pin_code, card_number=old_number)
                for door_rel in card.user_id.hr_rfid_access_group_id.door_ids:
                    door = door_rel.door_id
                    cmd_env.add_card(door.id, door_rel.time_schedule_id.id,
                                     card.user_id.hr_rfid_pin_code, card_id=card.id)

            elif new_number is not None:
                for door_rel in card.user_id.hr_rfid_access_group_id.door_ids:
                    door = door_rel.door_id
                    cmd_env.remove_card(door.id, door_rel.time_schedule_id.id,
                                        card.user_id.hr_rfid_pin_code, card_number=old_number)
                    cmd_env.add_card(door.id, door_rel.time_schedule_id.id,
                                     card.user_id.hr_rfid_pin_code, card_id=card.id)

            elif new_user is not None:
                for door_rel in old_user.hr_rfid_access_group_id.door_ids:
                    door = door_rel.door_id
                    cmd_env.remove_card(door.id, door_rel.time_schedule_id.id,
                                        old_user.hr_rfid_pin_code, card_id=card.id)
                for door_rel in card.user_id.hr_rfid_access_group_id.door_ids:
                    door = door_rel.door_id
                    cmd_env.add_card(door.id, door_rel.time_schedule_id.id,
                                     card.user_id.hr_rfid_pin_code, card_id=card.id)

            if new_card_type is not None:
                for door_rel in card.user_id.hr_rfid_access_group_id.door_ids:
                    door = door_rel.door_id
                    if door.card_type.id == old_card_type_id:
                        cmd_env.remove_card(door.id, door_rel.time_schedule_id.id,
                                            card.user_id.hr_rfid_pin_code, card_id=card.id)
                    cmd_env.add_card(door.id, door_rel.time_schedule_id.id,
                                     card.user_id.hr_rfid_pin_code, card_id=card.id)

        return True

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        card = super(HrRfidCard, self).create(vals)
        cmd_env = self.env['hr.rfid.command']

        for door_rel in card.user_id.hr_rfid_access_group_id.door_ids:
            door = door_rel.door_id
            cmd_env.add_card(door.id, door_rel.time_schedule_id.id, card.user_id.hr_rfid_pin_code,
                             card_id=card.id)

        return card


class HrRfidCardType(models.Model):
    _name = 'hr.rfid.card.type'

    name = fields.Char(
        string='Type Name',
        help='Label to differentiate types with',
        required=True,
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



































