# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions


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
    def add_acc_gr(self, access_groups, expiration=None):
        rel_env = self.env['hr.rfid.access.group.employee.rel']
        for emp in self:
            for acc_gr in access_groups:
                rel = rel_env.search([
                    ('employee_id', '=', emp.id),
                    ('access_group_id', '=', acc_gr.id),
                ])
                if rel:
                    rel.expiration = expiration
                    continue
                emp.check_for_ts_inconsistencies_when_adding(acc_gr)
                creation_dict = {
                    'employee_id': emp.id,
                    'access_group_id': acc_gr.id,
                }
                if expiration is not None and expiration is not False:
                    creation_dict['expiration'] = str(expiration)
                rel_env.create(creation_dict)

    @api.multi
    def remove_acc_gr(self, access_groups):
        rel_env = self.env['hr.rfid.access.group.employee.rel']
        rel_env.search([
            ('employee_id', 'in', self.ids),
            ('access_group_id', 'in', access_groups.ids)
        ]).unlink()

    @api.one
    @api.returns('hr.rfid.door')
    def get_doors(self, excluding_acc_grs=None, including_acc_grs=None):
        if excluding_acc_grs is None:
            excluding_acc_grs = self.env['hr.rfid.access.group']
        if including_acc_grs is None:
            including_acc_grs = self.env['hr.rfid.access.group']

        acc_grs = self.hr_rfid_access_group_ids.mapped('access_group_id')
        acc_grs = acc_grs - excluding_acc_grs
        acc_grs = acc_grs + including_acc_grs
        return acc_grs.mapped('all_door_ids').mapped('door_id')

    @api.one
    def check_for_ts_inconsistencies_when_adding(self, new_acc_grs):
        acc_gr_door_rel_env = self.env['hr.rfid.access.group.door.rel']
        acc_grs = self.hr_rfid_access_group_ids.mapped('access_group_id')
        for acc_gr1 in acc_grs:
            for acc_gr2 in new_acc_grs:
                door_rels1 = acc_gr1.all_door_ids
                door_rels2 = acc_gr2.all_door_ids
                acc_gr_door_rel_env.check_for_ts_inconsistencies(door_rels1, door_rels2)

    @api.one
    def check_for_ts_inconsistencies(self):
        acc_gr_door_rel_env = self.env['hr.rfid.access.group.door.rel']
        acc_grs = self.hr_rfid_access_group_ids.mapped('access_group_id')
        for i in range(len(acc_grs)):
            for j in range(i+1, len(acc_grs)):
                door_rels1 = acc_grs[i].all_door_ids
                door_rels2 = acc_grs[j].all_door_ids
                acc_gr_door_rel_env.check_for_ts_inconsistencies(door_rels1, door_rels2)

    @api.multi
    @api.constrains('hr_rfid_access_group_ids')
    def _check_access_group(self):
        for user in self:
            user.check_for_ts_inconsistencies()

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

    @api.multi
    def write(self, vals):
        for user in self:
            old_pin_code = user.hr_rfid_pin_code[:]
            old_dep = user.department_id

            super(HrEmployee, user).write(vals)

            new_pin_code = user.hr_rfid_pin_code
            new_dep = user.department_id

            if old_dep != new_dep:
                new_dep_acc_grs = new_dep.hr_rfid_allowed_access_groups
                for acc_gr_rel in user.hr_rfid_access_group_ids:
                    if acc_gr_rel.access_group_id not in new_dep_acc_grs:
                        acc_gr_rel.unlink()
                if new_dep.hr_rfid_default_access_group:
                    user.add_acc_gr(new_dep.hr_rfid_default_access_group)

            if old_pin_code != new_pin_code:
                user.hr_rfid_card_ids.mapped('door_rel_ids').pin_code_changed()

    @api.multi
    def unlink(self):
        for emp in self:
            emp.hr_rfid_card_ids.unlink()
        return super(HrEmployee, self).unlink()


class HrEmployeeDoors(models.TransientModel):
    _name = 'hr.rfid.employee.doors.wiz'
    _description = "Display doors employee has access to"

    def _default_employee(self):
        return self.env['hr.employee'].browse(self._context.get('active_ids'))

    def _default_doors(self):
        return self._default_employee().get_doors()

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        default=_default_employee,
    )

    door_ids = fields.Many2many(
        'hr.rfid.door',
        string='Doors',
        required=True,
        default=_default_doors,
    )
