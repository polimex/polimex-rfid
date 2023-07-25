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
        tracking=True,
        groups="hr_rfid.hr_rfid_group_officer"
    )

    hr_rfid_allowed_access_groups = fields.Many2many(
        'hr.rfid.access.group',
        string='Available Access Groups',
        help='Available access groups for employees in this department',
        ondelete='cascade',
        groups="hr_rfid.hr_rfid_group_officer"
    )

    @api.constrains('hr_rfid_default_access_group')
    def _check_hr_rfid_default_access_group(self):
        for dep in self:
            cur_acc_gr = dep.hr_rfid_default_access_group
            allowed_acc_gr_ids = dep.hr_rfid_allowed_access_groups

            if (len(cur_acc_gr) != 0) and (cur_acc_gr not in allowed_acc_gr_ids):
                raise exceptions.ValidationError('Default access group must be one of the access '
                                                 'groups in the list of allowed access groups!')

    @api.onchange('hr_rfid_allowed_access_groups')
    def _hr_rfid_allowed_access_groups_onchange(self):
        cur_acc_gr = self.hr_rfid_default_access_group
        if len(cur_acc_gr) != 0 and cur_acc_gr not in self.hr_rfid_allowed_access_groups:
            self.hr_rfid_default_access_group = None

    def write(self, vals):
        ret = super(HrDepartment, self).write(vals)

        if 'hr_rfid_allowed_access_groups' in vals:

            to_unlink = self.env['hr.rfid.access.group.employee.rel']
            for dep in self:
                acc_gr_rels = dep.mapped('member_ids').mapped('hr_rfid_access_group_ids')
                for rel in acc_gr_rels:
                    if rel.access_group_id not in dep.hr_rfid_allowed_access_groups:
                        to_unlink += rel
            to_unlink.unlink()

            if self.hr_rfid_default_access_group not in self.hr_rfid_allowed_access_groups:
                self.hr_rfid_default_access_group = None
            if len(self.hr_rfid_default_access_group) == 0 and len(self.hr_rfid_allowed_access_groups) > 0:
                self.hr_rfid_default_access_group = self.hr_rfid_allowed_access_groups[0]
                for emp in self.member_ids:
                    if len(emp.hr_rfid_access_group_ids) == 0:
                        emp.add_acc_gr(self.hr_rfid_default_access_group)


        return ret

    def unlink(self):
        for dep in self:
            map(lambda r: r.hr_rfid_access_group_ids.unlink(), dep.member_ids)

        res = super(HrDepartment, self).unlink()
        return res


class HrDepartmentAccGrWizard(models.TransientModel):
    _name = 'hr.department.acc.grs'
    _description = 'Add or remove access groups to the department'

    def _default_dep(self):
        return self.env['hr.department'].browse(self._context.get('active_ids'))

    def _get_current_access_group(self):
        return self._default_dep().hr_rfid_allowed_access_groups

    dep_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        default=_default_dep,
    )

    acc_grs = fields.Many2many(
        'hr.rfid.access.group',
        string='Department groups',
        default=_get_current_access_group,
    )

    def add_acc_grs(self):
        self.ensure_one()
        self.dep_id.hr_rfid_allowed_access_groups = self.acc_grs
        if self.dep_id.hr_rfid_default_access_group not in self.acc_grs:
            self.dep_id.hr_rfid_default_access_group = None
        if (len(self.acc_grs) > 0) and len(self.dep_id.hr_rfid_default_access_group) == 0:
            self.dep_id.hr_rfid_default_access_group = self.acc_grs[0]
            for emp in self.dep_id.member_ids:
                if len(emp.hr_rfid_access_group_ids) == 0:
                    emp.add_acc_gr(self.dep_id.hr_rfid_default_access_group)



class HrDepartmentDefAccGrWizard(models.TransientModel):
    _name = 'hr.department.def.acc.gr'
    _description = "Set up the the department's default access group"

    def _default_dep(self):
        return self.env['hr.department'].browse(self._context.get('active_ids'))

    dep_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        default=_default_dep,
    )

    def_acc_gr = fields.Many2one(
        'hr.rfid.access.group',
        string='New default access group',
        required=True,
    )

    def change_default_access_group(self):
        self.ensure_one()
        self.dep_id.hr_rfid_default_access_group = self.def_acc_gr

        for emp in self.dep_id.member_ids:
            if len(emp.hr_rfid_access_group_ids) == 0:
                emp.add_acc_gr(self.def_acc_gr)

    def change_and_apply_def_acc_gr(self):
        self.ensure_one()
        self.dep_id.hr_rfid_default_access_group = self.def_acc_gr

        for emp in self.dep_id.member_ids:
            emp.add_acc_gr(self.def_acc_gr)


class HrDepartmentMassAccGrsWiz(models.TransientModel):
    _name = 'hr.department.mass.wiz'
    _description = 'Add/remove multiple access groups from users in a department'

    def _default_dep(self):
        return self.env['hr.department'].browse(self._context.get('active_ids'))

    dep_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        default=_default_dep,
    )

    acc_gr_ids = fields.Many2many(
        'hr.rfid.access.group',
        string='Access Groups',
    )

    expiration = fields.Datetime(
        string='Expiration',
    )

    exclude_ids = fields.Many2many(
        'hr.employee',
        string='Employees to Exclude',
    )

    def add_acc_grs(self):
        self.ensure_one()

        employees = self.dep_id.member_ids

        # if self.exclude_employees is True:
        employees = employees - self.exclude_ids

        if self.expiration is False:
            employees.add_acc_gr(self.acc_gr_ids)
        else:
            employees.add_acc_gr(self.acc_gr_ids, self.expiration)

    def remove_acc_grs(self):
        self.ensure_one()

        employees = self.dep_id.member_ids

        # if self.exclude_employees is True:
        employees = employees - self.exclude_ids

        employees.remove_acc_gr(self.acc_gr_ids)


class HrDepartmentAddDefAccGrWizard(models.TransientModel):
    _name = 'hr.department.add.def.acc.grs'
    _description = 'Add access group and change to default'

    def _default_dep(self):
        return self.env['hr.department'].browse(self._context.get('active_ids'))

    dep_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        default=_default_dep,
    )

    acc_gr = fields.Many2one(
        'hr.rfid.access.group',
        string='Access group to add and set to default',
        required=True,
    )

    def_acc_grs = fields.Selection