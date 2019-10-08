# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions
import logging

_logger = logging.getLogger(__name__)


class HrDepartment(models.Model):
    _inherit = "hr.department"

    hr_rfid_default_access_group = fields.Many2one(
        'hr.rfid.access.group',
        string='Default Access Group',
        help='Every user added to this department gets this access group by default',
        ondelete='set null',
        track_visibility='onchange',
    )

    hr_rfid_allowed_access_groups = fields.Many2many(
        'hr.rfid.access.group',
        string='Rfid Access Group',
        help='Which access group the department uses to gain permissions to Rfid doors',
        ondelete='set null',
    )

    @api.multi
    @api.constrains('hr_rfid_default_access_group')
    def _check_hr_rfid_default_access_group(self):
        for dep in self:
            cur_acc_gr = dep.hr_rfid_default_access_group
            allowed_acc_gr_ids = dep.hr_rfid_allowed_access_groups

            if len(cur_acc_gr) != 0 and cur_acc_gr not in allowed_acc_gr_ids:
                raise exceptions.ValidationError('Default access group must be one of the access '
                                                 'groups in the list of allowed access groups!')

    @api.onchange('hr_rfid_allowed_access_groups')
    def _hr_rfid_allowed_access_groups_onchange(self):
        cur_acc_gr = self.hr_rfid_default_access_group
        if len(cur_acc_gr) != 0 and cur_acc_gr not in self.hr_rfid_allowed_access_groups:
            self.hr_rfid_default_access_group = None

    @api.multi
    def write(self, vals):
        res = super(HrDepartment, self).write(vals)

        if 'hr_rfid_allowed_access_groups' in vals:
            for dep in self:
                for user in dep.member_ids:
                    for acc_gr_rel in user.hr_rfid_access_group_ids:
                        acc_gr = acc_gr_rel.access_group_id
                        if acc_gr not in dep.hr_rfid_allowed_access_groups:
                            acc_gr_rel.unlink()

        return res

    @api.multi
    def unlink(self):
        for dep in self:
            map(lambda r: r.hr_rfid_access_group_ids.unlink(), dep.member_ids)

        res = super(HrDepartment, self).unlink()
        return res

    @api.one
    def remove_def_acc_gr(self):
        self.hr_rfid_default_access_group -= self.hr_rfid_default_access_group


class HrDepartmentAccGrWizard(models.TransientModel):
    _name = 'hr.department.acc.grs'
    _description = 'Add or remove access groups to the department'

    def _default_dep(self):
        return self.env['hr.department'].browse(self._context.get('active_ids'))

    dep_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        default=_default_dep,
    )

    acc_grs = fields.Many2many(
        'hr.rfid.access.group',
        string='Access groups to add/remove',
        required=True,
    )

    @api.multi
    def add_acc_grs(self):
        self.ensure_one()
        self.dep_id.hr_rfid_allowed_access_groups |= self.acc_grs

    @api.multi
    def del_acc_grs(self):
        self.ensure_one()
        if self.dep_id.hr_rfid_default_access_group in self.acc_grs:
            self.dep_id.hr_rfid_default_access_group = None
        self.dep_id.hr_rfid_allowed_access_groups -= self.acc_grs


class HrDepartmentDefAccGrWizard(models.TransientModel):
    _name = 'hr.department.def.acc.gr'
    _description = "Set up the the department's default access group"

    def _default_dep(self):
        return self.env['hr.department'].browse(self._context.get('active_ids'))

    dep_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        default=_default_dep
    )

    def_acc_gr = fields.Many2one(
        'hr.rfid.access.group',
        string='New default access group',
        required=True,
    )

    @api.multi
    def change_default_access_group(self):
        self.ensure_one()
        self.dep_id.hr_rfid_default_access_group = self.def_acc_gr

    @api.multi
    def change_and_apply_def_acc_gr(self):
        self.ensure_one()
        self.dep_id.hr_rfid_default_access_group = self.def_acc_gr

        for emp in self.dep_id.member_ids:
            if len(emp.hr_rfid_access_group_ids) == 0:
                emp.add_acc_gr(self.def_acc_gr)
