# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import AccessError


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_hr_rfid_att_early_come = fields.Boolean(
        'Early come',
        help="Include a 'Count of employees who arrived early today' KPI in the digest email.",
    )
    kpi_hr_rfid_att_late = fields.Boolean(
        'Late',
        help="Include a 'Count of late arrivals' KPI in the digest email.",
    )
    kpi_hr_rfid_att_leave = fields.Boolean(
        'Early leave',
        help="Include a 'Count of employees who left early' KPI in the digest email.",
    )
    kpi_hr_rfid_att_overtime = fields.Boolean(
        'Overtime',
        help="Include a 'Count of employees who stayed past contract hours' KPI in the digest email.",
    )
    kpi_hr_rfid_att_extra = fields.Boolean(
        'Extra time',
        help="Include a 'Count of employees with extra unrecorded time' KPI in the digest email.",
    )
    kpi_hr_rfid_att_no_show = fields.Boolean(
        'No-show',
        help="Include a 'Count of employees who were scheduled but did not "
             "show up' KPI in the digest email.",
    )
    kpi_hr_rfid_att_early_come_value = fields.Integer(
        compute='_compute_kpi_hr_rfid_att_values',
        help="Live count of employees who checked in before their schedule start during the digest window.",
    )
    kpi_hr_rfid_att_late_value = fields.Integer(
        compute='_compute_kpi_hr_rfid_att_values',
        help="Live count of employees who checked in after their schedule start during the digest window.",
    )
    kpi_hr_rfid_att_leave_value = fields.Integer(
        compute='_compute_kpi_hr_rfid_att_values',
        help="Live count of employees who checked out before their schedule end during the digest window.",
    )
    kpi_hr_rfid_att_overtime_value = fields.Integer(
        compute='_compute_kpi_hr_rfid_att_values',
        help="Live count of employees with recorded overtime during the digest window.",
    )
    kpi_hr_rfid_att_extra_value = fields.Integer(
        compute='_compute_kpi_hr_rfid_att_values',
        help="Live count of employees with extra unrecorded time during the digest window.",
    )
    kpi_hr_rfid_att_no_show_value = fields.Integer(
        compute='_compute_kpi_hr_rfid_att_values',
        help="Live count of scheduled employees with no attendance (no-show) "
             "during the digest window.",
    )

    def _compute_kpi_hr_rfid_att_values(self):
        if not self.env.user.has_group('hr_attendance.group_hr_attendance_officer'):
            raise AccessError(_("Do not have access, skip this data for user's digest email"))
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            early_come_time =self.env['hr.attendance.extra'].search_count([
                ('early_come_time', '>', 0),
                ('for_date', '>=', start),
                ('for_date', '<', end),
                ('employee_id.company_id', '=', company.id),
            ])
            record.kpi_hr_rfid_att_early_come_value = early_come_time

            late = self.env['hr.attendance.extra'].search_count([
                ('late_time', '>', 0),
                ('for_date', '>=', start),
                ('for_date', '<', end),
                ('employee_id.company_id', '=', company.id),
            ])
            record.kpi_hr_rfid_att_late_value = late
            leave = self.env['hr.attendance.extra'].search_count([
                ('early_leave_time', '>', 0),
                ('for_date', '>=', start),
                ('for_date', '<', end),
                ('employee_id.company_id', '=', company.id),
            ])
            record.kpi_hr_rfid_att_leave_value = leave
            overtime = self.env['hr.attendance.extra'].search_count([
                ('overtime', '>', 0),
                ('for_date', '>=', start),
                ('for_date', '<', end),
                ('employee_id.company_id', '=', company.id),
            ])
            record.kpi_hr_rfid_att_overtime_value = overtime
            extra_time = self.env['hr.attendance.extra'].search_count([
                ('extra_time', '>', 0),
                ('for_date', '>=', start),
                ('for_date', '<', end),
                ('employee_id.company_id', '=', company.id),
            ])
            record.kpi_hr_rfid_att_extra_value = extra_time
            # No-show: core absence detection writes 1-second 'technical'
            # attendances for scheduled employees who never checked in. Count
            # distinct employees with such a record in the window.
            no_show_groups = self.env['hr.attendance']._read_group(
                domain=[
                    ('in_mode', '=', 'technical'),
                    ('check_in', '>=', start),
                    ('check_in', '<', end),
                    ('employee_id.company_id', '=', company.id),
                ],
                groupby=['employee_id'],
            )
            record.kpi_hr_rfid_att_no_show_value = len(no_show_groups)

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_hr_rfid_att_early_come_value'] = 'hr_attendance.hr_attendance_action&menu_id=%s' % self.env.ref('hr_attendance_late.menu_hr_attendance_extra').id
        res['kpi_hr_rfid_att_late'] = 'hr_attendance.hr_attendance_action&menu_id=%s' % self.env.ref('hr_attendance_late.menu_hr_attendance_extra').id
        res['kpi_hr_rfid_att_leave'] = 'hr_attendance.hr_attendance_action&menu_id=%s' % self.env.ref('hr_attendance_late.menu_hr_attendance_extra').id
        res['kpi_hr_rfid_att_overtime'] = 'hr_attendance.hr_attendance_action&menu_id=%s' % self.env.ref('hr_attendance_late.menu_hr_attendance_extra').id
        res['kpi_hr_rfid_att_extra_value'] = 'hr_attendance.hr_attendance_action&menu_id=%s' % self.env.ref('hr_attendance_late.menu_hr_attendance_extra').id
        res['kpi_hr_rfid_att_no_show_value'] = 'hr_attendance.hr_attendance_action&menu_id=%s' % self.env.ref('hr_attendance_late.menu_hr_attendance_extra').id
        return res
