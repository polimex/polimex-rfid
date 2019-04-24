# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import logging

_logger = logging.getLogger(__name__)


class HrDepartment(models.Model):
    _inherit = "hr.department"

    hr_rfid_default_access_group = fields.Many2one(
        'hr.rfid.access.group',
        string='Default Access Group',
        help='Every user added to this department gets this access group by default',
        ondelete='set null',
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
                    if user.hr_rfid_access_group_id not in dep.hr_rfid_allowed_access_groups:
                        user.write({ 'hr_rfid_access_group_id': dep.hr_rfid_default_access_group })

        if 'hr_rfid_default_access_group' in vals:
            for dep in self:
                for user in dep.member_ids:
                    if len(user.hr_rfid_access_group_id) == 0:
                        user.write({ 'hr_rfid_access_group_id': dep.hr_rfid_default_access_group })

        return res

    @api.multi
    def unlink(self):
        for dep in self:
            for user in dep.member_ids:
                user.write({ 'hr_rfid_access_group_id': None })

        res = super(HrDepartment, self).unlink()
        return res

