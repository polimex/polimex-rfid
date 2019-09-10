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

    hr_rfid_access_group_ids = fields.One2many(
        'hr.rfid.access.group.employee.rel',
        'employee_id',
        string='Access Groups',
        help='Which access groups the user is a part of',
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

    @api.multi
    def add_acc_gr(self, access_group, expiration=None):
        rel_env = self.env['hr.rfid.access.group.employee.rel']
        for emp in self:
            creation_dict = {
                'employee_id': emp.id,
                'access_group_id': access_group.id,
            }
            if expiration is not None and expiration is not False:
                creation_dict['expiration'] = str(expiration)
            rel_env.create(creation_dict)

    @api.multi
    def remove_acc_gr(self, access_group):
        rel_env = self.env['hr.rfid.access.group.employee.rel']
        for emp in self:
            rel_env.search([
                ('employee_id', '=', emp.id),
                ('access_group_id', '=', access_group.id)
            ]).unlink()

    @api.one
    def get_doors(self, excluding_acc_grs=None, including_acc_grs=None):
        if excluding_acc_grs is None:
            excluding_acc_grs = self.env['hr.rfid.access.group']
        if including_acc_grs is None:
            including_acc_grs = self.env['hr.rfid.access.group']

        acc_grs = self.hr_rfid_access_group_ids.mapped('access_group_id')
        acc_grs = acc_grs - excluding_acc_grs
        acc_grs = acc_grs + including_acc_grs
        return acc_grs.mapped('all_door_ids').mapped('door_id')

    @api.multi
    @api.constrains('hr_rfid_access_group_ids')
    def _check_access_group(self):
        for user in self:
            for acc_gr_rel in user.hr_rfid_access_group_ids:
                acc_gr = acc_gr_rel.access_group_id
                if acc_gr not in user.department_id.hr_rfid_allowed_access_groups:
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

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        command_env = self.env['hr.rfid.command']
        user = super(HrEmployee, self).create(vals)

        for acc_gr_rel in user.hr_rfid_access_group_ids:
            acc_gr = acc_gr_rel.access_group_id
            for door_rel in acc_gr.all_door_ids:
                door = door_rel.door_id
                for card in user.hr_rfid_card_ids:
                    command_env.add_card(door.id, door_rel.time_schedule_id.id,
                                         user.hr_rfid_pin_code, card_id=card.id)

        return user

    @api.multi
    def write(self, vals):
        cmd_env = self.env['hr.rfid.command']
        card_env = self.env['hr.rfid.card']

        for user in self:
            old_card_ids = None

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

                for acc_gr_rel in user.hr_rfid_access_group_ids:
                    acc_gr = acc_gr_rel.access_group_id
                    for door_rel in acc_gr.all_door_ids:
                        door = door_rel.door_id
                        for card_id in removed_cards:
                            card = card_env.browse(card_id)
                            cmd_env.remove_card(door.id, door_rel.time_schedule_id.id,
                                                user.hr_rfid_pin_code, card_id=card.id)
                        for card_id in added_cards:
                            card = card_env.browse(card_id)
                            cmd_env.add_card(door.id, door_rel.time_schedule_id.id,
                                             user.hr_rfid_pin_code, card_id=card.id)

            if 'hr_rfid_pin_code' in vals:
                for acc_gr_rel in user.hr_rfid_access_group_ids:
                    acc_gr = acc_gr_rel.access_group_id
                    for door_rel in acc_gr.all_door_ids:
                        door = door_rel.door_id
                        for card in user.hr_rfid_card_ids:
                            cmd_env.add_card(door.id, door_rel.time_schedule_id.id,
                                             user.hr_rfid_pin_code, card_id=card.id)

        return True


class HrEmployeeAccGrWizard(models.TransientModel):
    _name = 'hr.employee.acc.grs'
    _description = 'Add or remove access groups to or from the employee'

    def _default_user(self):
        return self.env['hr.employee'].browse(self._context.get('active_ids'))

    def _default_allowed_acc_grs(self):
        employee = self._default_user()
        cur_acc_grs = employee.hr_rfid_access_group_ids.mapped('access_group_id')
        if self._context.get('adding_acc_grs', False):
            return employee.department_id.hr_rfid_allowed_access_groups - cur_acc_grs
        return cur_acc_grs

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        default=_default_user,
    )

    allowed_acc_grs = fields.Many2many(
        'hr.rfid.access.group',
        'hr_employee_acc_grs_allowed_grs_rel',
        default=_default_allowed_acc_grs,
    )

    acc_gr_ids = fields.Many2many(
        'hr.rfid.access.group',
        'hr_employee_acc_grs_acc_gr_ids_rel',
        string='Access groups to add/remove',
        required=True,
    )

    expiration = fields.Datetime(
        string='Expiration',
        help='When the access groups will be removed from the employee.',
    )

    @api.multi
    def add_acc_grs(self):
        self.ensure_one()
        rel_env = self.env['hr.rfid.access.group.employee.rel']

        acc_gr_ids = rel_env.search([
            ('employee_id', '=', self.employee_id.id),
            ('access_group_id', 'in', self.acc_gr_ids.ids),
        ]).mapped('access_group_id')

        acc_gr_ids = self.acc_gr_ids - acc_gr_ids

        for acc_gr_id in acc_gr_ids:
            self.employee_id.add_acc_gr(acc_gr_id, self.expiration)

    @api.multi
    def rem_acc_grs(self):
        self.ensure_one()
        rel_env = self.env['hr.rfid.access.group.employee.rel']

        acc_gr_ids = rel_env.search([
            ('employee_id', '=', self.employee_id.id),
            ('access_group_id', 'in', self.acc_gr_ids.ids),
        ]).unlink()




