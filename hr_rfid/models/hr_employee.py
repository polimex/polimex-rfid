# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    hr_rfid_pin_code = fields.Char(
        string='User pin code',
        help="Pin code for this user, four zeroes means that the user has no pin code.",
        limit=4,
        default='0000',
        track_visibility='onchange',
    )

    hr_rfid_access_group_id = fields.Many2one(
        'hr.rfid.access.group',
        string='Access Group',
        help='Which access group the user is a part of',
        track_visibility='onchange',
    )

    hr_rfid_card_ids = fields.One2many(
        'hr.rfid.card',
        'employee_id',
        string='RFID Card',
        help='Cards owned by the employee',
    )

    hr_rfid_event_ids = fields.One2many(
        'hr.rfid.event.user',
        'employee_id',
        string='RFID Events',
        help='Events concerning this employee',
    )

    @api.onchange('department_id')
    def _onchange_department_access_group(self):
        self.hr_rfid_access_group_id = self.department_id.hr_rfid_default_access_group

    @api.multi
    @api.constrains('hr_rfid_access_group_id')
    def _check_access_group(self):
        for user in self:
            if user.hr_rfid_access_group_id.id is False:
                continue

            valid_access_group = False
            for acc_gr in user.department_id.hr_rfid_allowed_access_groups:
                if acc_gr.id == user.hr_rfid_access_group_id.id:
                    valid_access_group = True
                    break

            if valid_access_group is False:
                raise exceptions.ValidationError('Access group must be one of the access '
                                                 'groups assigned to the department!')

    @api.multi
    @api.constrains('hr_rfid_pin_code')
    def _check_pin_code(self):
        for user in self:
            pin = user.hr_rfid_pin_code
            if len(pin) != 4:
                raise exceptions.ValidationError('Pin code must have exactly 4 characters')

            # If char is not a valid decimal number, int(char, 10) will raise an error
            try:
                for char in str(pin):
                    int(char, 10)
            except ValueError:
                raise exceptions.ValidationError('Invalid pin code, digits must be from 0 to 9')

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        records = self.env['hr.employee']
        for vals in vals_list:
            command_env = self.env['hr.rfid.command']
            user = super(HrEmployee, self).create([vals])
            records += user

            for door_rel in user.hr_rfid_access_group_id.all_door_ids:
                door = door_rel.door_id
                for card in user.hr_rfid_card_ids:
                    command_env.add_card(door.id, door_rel.time_schedule_id.id,
                                         user.hr_rfid_pin_code, card_id=card.id)

        return records

    @api.multi
    def write(self, vals):
        cmd_env = self.env['hr.rfid.command']
        acc_gr_env = self.env['hr.rfid.access.group']
        card_env = self.env['hr.rfid.card']

        for user in self:
            prev_access_group_id = None
            old_card_ids = None

            if 'hr_rfid_access_group_id' in vals:
                prev_access_group_id = user.hr_rfid_access_group_id.id

            if 'hr_rfid_card_ids' in vals:
                old_card_ids = set()
                for card in user.hr_rfid_card_ids:
                    old_card_ids.add(card.id)

            super(HrEmployee, user).write(vals)

            if old_card_ids is not None:
                new_card_ids = set()
                for card in user.hr_rfid_card_ids:
                    new_card_ids.add(card.id)

                added_cards = new_card_ids - old_card_ids
                removed_cards = old_card_ids - new_card_ids

                for door_rel in user.hr_rfid_access_group_id.all_door_ids:
                    door = door_rel.door_id
                    for card_id in removed_cards:
                        card = card_env.browse(card_id)
                        cmd_env.remove_card(door.id, door_rel.time_schedule_id.id,
                                            user.hr_rfid_pin_code, card_id=card.id)
                    for card_id in added_cards:
                        card = card_env.browse(card_id)
                        cmd_env.add_card(door.id, door_rel.time_schedule_id.id,
                                         user.hr_rfid_pin_code, card_id=card.id)

            if prev_access_group_id is not None:
                prev_acc_gr = acc_gr_env.browse(prev_access_group_id)
                for door_rel in prev_acc_gr.all_door_ids:
                    door = door_rel.door_id
                    for card in user.hr_rfid_card_ids:
                        cmd_env.remove_card(door.id, door_rel.time_schedule_id.id,
                                            user.hr_rfid_pin_code, card_id=card.id)

                for door_rel in user.hr_rfid_access_group_id.all_door_ids:
                    door = door_rel.door_id
                    for card in user.hr_rfid_card_ids:
                        cmd_env.add_card(door.id, door_rel.time_schedule_id.id,
                                         user.hr_rfid_pin_code, card_id=card.id)

            if 'hr_rfid_pin_code' in vals:
                for door_rel in user.hr_rfid_access_group_id.all_door_ids:
                    door = door_rel.door_id
                    for card in user.hr_rfid_card_ids:
                        cmd_env.add_card(door.id, door_rel.time_schedule_id.id,
                                         user.hr_rfid_pin_code, card_id=card.id)

        return True

    @api.multi
    def unlink(self):
        command_env = self.env['hr.rfid.command']

        for user in self:
            for door_rel in user.hr_rfid_access_group_id.all_door_ids:
                door = door_rel.door_id
                for card in user.hr_rfid_card_ids:
                    command_env.remove_card(door.id, door_rel.time_schedule_id.id,
                                            user.hr_rfid_pin_code, card_id=card.id)

        return super(HrEmployee, self).unlink()






