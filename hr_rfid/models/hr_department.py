# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions
import logging

_logger = logging.getLogger(__name__)


class HrDepartment(models.Model):
    _inherit = "hr.department"

    hr_rfid_default_access_group = fields.Many2one(
        'hr.rfid.access.group',
        string='Default Access Group',
        help='New employees in this department will automatically receive this access group. '
             'This ensures they have the basic door access needed for their work area from day one.',
        ondelete='set null',
        tracking=True,
        groups="hr_rfid.hr_rfid_group_officer"
    )

    hr_rfid_allowed_access_groups = fields.Many2many(
        'hr.rfid.access.group',
        string='Available Access Groups',
        help='Define which access groups can be assigned to employees in this department. '
             'This helps maintain security by limiting access options to relevant areas only. '
             'For example, IT department can access server rooms, while HR can access personnel files.',
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
    _description = 'Department Access Group Configuration'

    def _default_dep(self):
        return self.env['hr.department'].browse(self.env.context.get('active_ids'))

    def _get_current_access_group(self):
        return self._default_dep().hr_rfid_allowed_access_groups

    dep_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        default=_default_dep,
        help="Department this wizard run targets. Set automatically from the selected record(s); read-only for the user.",
    )

    acc_grs = fields.Many2many(
        'hr.rfid.access.group',
        string='Department Access Groups',
        help='Select all access groups that should be available for employees in this department. '
             'Only these groups can be assigned to department members.',
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
    _description = 'Set Department Default Access Group'

    def _default_dep(self):
        return self.env['hr.department'].browse(self.env.context.get('active_ids'))

    dep_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        default=_default_dep,
        help="Department this wizard run targets. Set automatically from the selected record(s); read-only for the user.",
    )

    def_acc_gr = fields.Many2one(
        'hr.rfid.access.group',
        string='New Default Access Group',
        help='Choose the access group that new employees will automatically receive. '
             'This should include the basic areas they need to access for their daily work.',
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
    _description = 'Bulk Access Group Management for Department'

    def _default_dep(self):
        return self.env['hr.department'].browse(self.env.context.get('active_ids'))

    dep_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        default=_default_dep,
        help="Department this wizard run targets. Set automatically from the selected record(s); read-only for the user.",
    )

    acc_gr_ids = fields.Many2many(
        'hr.rfid.access.group',
        string='Access Groups',
        help='Select one or more access groups to add or remove from department employees. '
             'This is useful for granting temporary access or updating permissions in bulk.',
    )

    expiration = fields.Datetime(
        string='Access Expiration',
        help='Set an expiration date for these access rights (optional). '
             'Perfect for temporary projects, visitor access, or time-limited assignments. '
             'Leave empty for permanent access.',
    )

    exclude_ids = fields.Many2many(
        'hr.employee',
        string='Exclude Employees',
        help='Select specific employees who should NOT receive these access changes. '
             'Useful when updating an entire department except for a few individuals.',
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
    _description = 'Add and Set Default Access Group'

    def _default_dep(self):
        return self.env['hr.department'].browse(self.env.context.get('active_ids'))

    dep_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        default=_default_dep,
        help="Department this wizard run targets. Set automatically from the selected record(s); read-only for the user.",
    )

    acc_gr = fields.Many2one(
        'hr.rfid.access.group',
        string='New Access Group',
        help='This access group will be added to the department\'s available groups '
             'AND set as the default for new employees. Existing employees without '
             'access groups will also receive this group.',
        required=True,
    )

    def_acc_grs = fields.Selection