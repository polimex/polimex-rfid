# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class ResPartner(models.Model):
    _inherit = 'res.partner'

    hr_rfid_pin_code = fields.Char(
        string='Contact pin code',
        help="Pin code for this contact, four zeroes means that the contact has no pin code.",
        limit=4,
        default='0000',
    )

    hr_rfid_access_group_id = fields.Many2one(
        'hr.rfid.access.group',
        string='Access Group',
        help='Which access group the contact is a part of',
    )

    hr_rfid_card_ids = fields.One2many(
        'hr.rfid.card',
        'contact_id',
        string='RFID Card',
        help='Cards owned by the employee',
    )

    hr_rfid_event_ids = fields.One2many(
        'hr.rfid.event.user',
        'contact_id',
        string='RFID Events',
        help='Events concerning this employee',
    )

    @api.multi
    @api.constrains('hr_rfid_pin_code')
    def _check_pin_code(self):
        for contact in self:
            pin = contact.hr_rfid_pin_code
            if len(pin) != 4:
                raise exceptions.ValidationError('Pin code must have exactly 4 characters')

            # If char is not a valid hex number, int(char, 16) will raise an error
            try:
                for char in str(pin):
                    int(char, 10)
            except ValueError:
                raise exceptions.ValidationError('Invalid pin code, digits must be from 0 to 9')

    # TODO Check if this shit even works
    # @api.model
    # @api.returns('self', lambda value: value.id)
    # def create(self, vals):
    #     command_env = self.env['hr.rfid.command']
    #     user = super(HrEmployee, self).create(vals)
    #
    #     for door_rel in user.hr_rfid_access_group_id.door_ids:
    #         door = door_rel.door_id
    #         for card in user.hr_rfid_card_ids:
    #             command_env.add_card(door.id, door_rel.time_schedule_id.id,
    #                                  user.hr_rfid_pin_code, card_id=card.id)
    #
    #     return user
    #
    # @api.multi
    # def write(self, vals):
    #     # TODO Change default access group when department is changed
    #     cmd_env = self.env['hr.rfid.command']
    #     acc_gr_env = self.env['hr.rfid.access.group']
    #     card_env = self.env['hr.rfid.card']
    #
    #     for user in self:
    #         prev_access_group_id = None
    #         old_card_ids = None
    #
    #         if 'hr_rfid_access_group_id' in vals:
    #             prev_access_group_id = user.hr_rfid_access_group_id.id
    #
    #         if 'hr_rfid_card_ids' in vals:
    #             old_card_ids = set()
    #             for card in user.hr_rfid_card_ids:
    #                 old_card_ids.add(card.id)
    #
    #         super(HrEmployee, user).write(vals)
    #
    #         if old_card_ids is not None:
    #             new_card_ids = set()
    #             for card in user.hr_rfid_card_ids:
    #                 new_card_ids.add(card.id)
    #
    #             added_cards = new_card_ids - old_card_ids
    #             removed_cards = old_card_ids - new_card_ids
    #
    #             for door_rel in user.hr_rfid_access_group_id.door_ids:
    #                 door = door_rel.door_id
    #                 for card_id in removed_cards:
    #                     card = card_env.browse(card_id)
    #                     cmd_env.remove_card(door.id, door_rel.time_schedule_id.id,
    #                                         user.hr_rfid_pin_code, card_id=card.id)
    #                 for card_id in added_cards:
    #                     card = card_env.browse(card_id)
    #                     cmd_env.add_card(door.id, door_rel.time_schedule_id.id,
    #                                      user.hr_rfid_pin_code, card_id=card.id)
    #
    #         if prev_access_group_id is not None:
    #             prev_acc_gr = acc_gr_env.browse(prev_access_group_id)
    #             for door_rel in prev_acc_gr.door_ids:
    #                 door = door_rel.door_id
    #                 for card in user.hr_rfid_card_ids:
    #                     cmd_env.remove_card(door.id, door_rel.time_schedule_id.id,
    #                                         user.hr_rfid_pin_code, card_id=card.id)
    #
    #             for door_rel in user.hr_rfid_access_group_id.door_ids:
    #                 door = door_rel.door_id
    #                 for card in user.hr_rfid_card_ids:
    #                     cmd_env.add_card(door.id, door_rel.time_schedule_id.id,
    #                                      user.hr_rfid_pin_code, card_id=card.id)
    #
    #         if 'hr_rfid_pin_code' in vals:
    #             for door_rel in user.hr_rfid_access_group_id.door_ids:
    #                 door = door_rel.door_id
    #                 for card in user.hr_rfid_card_ids:
    #                     cmd_env.add_card(door.id, door_rel.time_schedule_id.id,
    #                                      user.hr_rfid_pin_code, card_id=card.id)
    #
    #     return True
    #
    # @api.multi
    # def unlink(self):
    #     command_env = self.env['hr.rfid.command']
    #
    #     for user in self:
    #         for door_rel in user.hr_rfid_access_group_id.door_ids:
    #             door = door_rel.door_id
    #             for card in user.hr_rfid_card_ids:
    #                 command_env.remove_card(door.id, door_rel.time_schedule_id.id,
    #                                         user.hr_rfid_pin_code, card_id=card.id)
    #
    #     return super(HrEmployee, self).unlink()


