# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import AccessError


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_hr_rfid_denied = fields.Boolean('Denied Events')
    kpi_hr_rfid_granted = fields.Boolean('Granted Events')
    kpi_hr_rfid_system = fields.Boolean('System Events')
    kpi_hr_rfid_command = fields.Boolean('Commands executed')
    kpi_hr_rfid_card = fields.Boolean('Active cards')
    kpi_hr_rfid_denied_value = fields.Integer(compute='_compute_kpi_hr_rfid_values')
    kpi_hr_rfid_granted_value = fields.Integer(compute='_compute_kpi_hr_rfid_values')
    kpi_hr_rfid_system_value = fields.Integer(compute='_compute_kpi_hr_rfid_values')
    kpi_hr_rfid_command_value = fields.Integer(compute='_compute_kpi_hr_rfid_values')
    kpi_hr_rfid_card_value = fields.Integer(compute='_compute_kpi_hr_rfid_values')

    def _compute_kpi_hr_rfid_values(self):
        if not self.env.user.has_group('hr_rfid.hr_rfid_group_officer'):
            raise AccessError(_("Do not have access, skip this data for user's digest email"))
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            denied_events = self.env['hr.rfid.event.user'].search_count([
                ('event_action', 'in', ['2', '3', '4', '5', '8', '15']),
                ('create_date', '>=', start),
                ('create_date', '<', end),
                '|',
                '|', ('employee_id.company_id', 'in', [company.id]),
                ('employee_id.company_id', '=', False),
                '|', ('contact_id.company_id', 'in', [company.id]),
                ('contact_id.company_id', '=', False)
            ])
            record.kpi_hr_rfid_denied_value = denied_events
            granted_events = self.env['hr.rfid.event.user'].search_count([
                ('event_action', 'in', ['1', '6', '7', '9', '10', '11', '12']),
                ('create_date', '>=', start),
                ('create_date', '<', end),
                '|',
                '|', ('employee_id.company_id', 'in', [company.id]),
                ('employee_id.company_id', '=', False),
                '|', ('contact_id.company_id', 'in', [company.id]),
                ('contact_id.company_id', '=', False)
            ])
            record.kpi_hr_rfid_granted_value = granted_events
            system_events = self.env['hr.rfid.event.system'].search_count([
                ('create_date', '>=', start),
                ('create_date', '<', end),
                ('webstack_id.company_id', 'in', [company.id]),
            ])
            record.kpi_hr_rfid_system_value = system_events
            commands = self.env['hr.rfid.command'].search_count([
                ('create_date', '>=', start),
                ('create_date', '<', end),
                ('webstack_id.company_id', 'in', [company.id]),
            ])
            record.kpi_hr_rfid_command_value = commands
            cards = self.env['hr.rfid.card'].search_count([
                ('create_date', '>=', start),
                ('create_date', '<', end),
                ('company_id', '=', company.id),
            ])
            record.kpi_hr_rfid_card_value = cards

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_hr_rfid_denied'] = 'hr_rfid.hr_rfid_event_user_action&menu_id=%s' % self.env.ref('hr_rfid.hr_rfid_root_menu').id
        res['kpi_hr_rfid_granted'] = 'hr_rfid.hr_rfid_event_user_action&menu_id=%s' % self.env.ref('hr_rfid.hr_rfid_root_menu').id
        res['kpi_hr_rfid_system'] = 'hr_rfid.hr_rfid_event_user_action&menu_id=%s' % self.env.ref('hr_rfid.hr_rfid_root_menu').id
        res['kpi_hr_rfid_command'] = 'hr_rfid.hr_rfid_event_user_action&menu_id=%s' % self.env.ref('hr_rfid.hr_rfid_root_menu').id
        res['kpi_hr_rfid_card'] = 'hr_rfid.hr_rfid_card_action&menu_id=%s' % self.env.ref('hr_rfid.hr_rfid_root_menu').id
        return res
