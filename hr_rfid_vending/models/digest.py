# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import AccessError
from odoo.tools import float_round


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_hr_rfid_vending_refill = fields.Boolean('Auto refill amount')
    kpi_hr_rfid_vending_sale = fields.Boolean('Sales amount')
    kpi_hr_rfid_vending_sale_count = fields.Boolean('Sales count')
    kpi_hr_rfid_vending_refill_value = fields.Monetary(compute='_compute_kpi_hr_rfid_vending_values')
    kpi_hr_rfid_vending_sale_value = fields.Monetary(compute='_compute_kpi_hr_rfid_vending_values')
    kpi_hr_rfid_vending_sale_count_value = fields.Monetary(compute='_compute_kpi_hr_rfid_vending_values')

    def _compute_kpi_hr_rfid_vending_values(self):
        if not self.env.user.has_group('hr_rfid_vending.group_operator'):
            raise AccessError(_("Do not have access, skip this data for user's digest email"))
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            # vending_history = self.env['hr.rfid.vending.balance.history'].with_company(company).search([
            vending_history = self.env['hr.rfid.vending.balance.history'].search([
                ('create_date', '>=', start),
                ('create_date', '<', end),
                ('employee_id.company_id', 'in', [company.id]),
            ])
            record.kpi_hr_rfid_vending_refill_value = float_round(sum(h.balance_change for h in vending_history.filtered(lambda bh: bh.balance_change > 0)), 2)
            record.kpi_hr_rfid_vending_sale_value = float_round(abs(sum(h.balance_change for h in vending_history.filtered(lambda bh: bh.balance_change < 0))), 2)
            record.kpi_hr_rfid_vending_sale_count_value = len(vending_history.filtered(lambda bh: bh.balance_change < 0))

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_hr_rfid_vending_refill'] = 'hr_rfid_vending.hr_rfid_vending_balance_history_action&menu_id=%s' % self.env.ref('hr_rfid_vending.hr_rfid_vending_menu').id
        res['kpi_hr_rfid_vending_sale'] = 'hr_rfid_vending.hr_rfid_vending_balance_history_action&menu_id=%s' % self.env.ref('hr_rfid_vending.hr_rfid_vending_menu').id
        res['kpi_hr_rfid_vending_sale_count'] = 'hr_rfid_vending.hr_rfid_vending_balance_history_action&menu_id=%s' % self.env.ref('hr_rfid_vending.hr_rfid_vending_menu').id
        return res
