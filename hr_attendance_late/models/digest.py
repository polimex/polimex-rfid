# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import AccessError


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_hr_rfid_att_late = fields.Boolean('Late')
    kpi_hr_rfid_att_leave = fields.Boolean('Early leave')
    kpi_hr_rfid_att_overtime = fields.Boolean('Overtime')
    kpi_hr_rfid_att_late_value = fields.Integer(compute='_compute_kpi_hr_rfid_att_values')
    kpi_hr_rfid_att_leave_value = fields.Integer(compute='_compute_kpi_hr_rfid_att_values')
    kpi_hr_rfid_att_overtime_value = fields.Integer(compute='_compute_kpi_hr_rfid_att_values')

    def _compute_kpi_hr_rfid_att_values(self):
        if not self.env.user.has_group('hr_rfid.hr_rfid_group_officer'):
            raise AccessError(_("Do not have access, skip this data for user's digest email"))
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            late = self.env['hr.attendance'].search_count([
                ('late', '>', 0),
                ('check_in', '>=', start),
                ('check_in', '<', end),
                ('employee_id.company_id', '=', company.id),
            ])
            record.kpi_hr_rfid_att_late_value = late
            leave = self.env['hr.attendance'].search_count([
                ('early', '>', 0),
                ('check_in', '>=', start),
                ('check_in', '<', end),
                ('employee_id.company_id', '=', company.id),
            ])
            record.kpi_hr_rfid_att_leave_value = leave
            overtime = self.env['hr.attendance'].search_count([
                ('overtime', '>', 0),
                ('check_in', '>=', start),
                ('check_in', '<', end),
                ('employee_id.company_id', '=', company.id),
            ])
            record.kpi_hr_rfid_att_overtime_value = overtime

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_hr_rfid_att_late'] = 'hr_attendance.hr_attendance_action&menu_id=%s' % self.env.ref('hr_attendance.menu_hr_attendance_root').id
        res['kpi_hr_rfid_att_leave'] = 'hr_attendance.hr_attendance_action&menu_id=%s' % self.env.ref('hr_attendance.menu_hr_attendance_root').id
        res['kpi_hr_rfid_att_overtime'] = 'hr_attendance.hr_attendance_action&menu_id=%s' % self.env.ref('hr_attendance.menu_hr_attendance_root').id
        return res
