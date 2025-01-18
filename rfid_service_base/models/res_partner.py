# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, http, _
import re
from datetime import datetime


class ResPartner(models.Model):
    _inherit = ['res.partner']

    partner_rfid_sales_count = fields.Char(
        compute='_compute_partner_rfid_sales_count',
        groups="rfid_service_base.group_card_user"
    )

    def _compute_partner_rfid_sales_count(self):
        for e in self:
            e.partner_rfid_sales_count = self.env['rfid.service.sale'].search_count([('partner_id', '=', e.id)])

    def action_rfid_sales(self):
        self.ensure_one()
        return {
            'name': _('RFID Sales for {}').format(self.name),
            'view_mode': 'list,form',
            'res_model': 'rfid.service.sale',
            'domain': [('partner_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'help': _('''<p class="o_view_nocontent">
                    No Sales for this partner.
                </p>'''),
        }

