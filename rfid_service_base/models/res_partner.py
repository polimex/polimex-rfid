# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, http, _
import re
from datetime import datetime


class ResPartner(models.Model):
    _inherit = ['res.partner']

    partner_rfid_sales_count = fields.Char(
        compute='_compute_partner_rfid_sales_count',
        groups="hr_rfid.hr_rfid_group_officer",
        help="Number of visitor service sales registered against this contact across all services. Used by the smart button to drive the user to the sales history.",
    )

    def _compute_partner_rfid_sales_count(self):
        for e in self:
            e.partner_rfid_sales_count = self.env['rfid.service.sale'].search_count([('partner_id', '=', e.id)])

    def action_rfid_sales(self):
        self.ensure_one()
        return {
            'name': _('RFID Sales for {}').format(self.name),
            'view_mode': 'tree,form',
            'res_model': 'rfid.service.sale',
            'domain': [('partner_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'help': _('''<p class="o_view_nocontent">
                    No Sales for this partner.
                </p>'''),
        }

