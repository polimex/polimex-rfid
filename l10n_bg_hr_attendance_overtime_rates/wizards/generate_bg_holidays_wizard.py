# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class GenerateBgHolidaysWizard(models.TransientModel):
    _name = 'l10n.bg.generate.holidays.wizard'
    _description = 'Generate Bulgarian Public Holidays'

    year = fields.Integer(
        required=True,
        default=lambda self: fields.Date.context_today(self).year,
        help="Calendar year to generate the official Bulgarian public "
             "holidays for. Fixed dates plus the moving Orthodox-Easter "
             "cluster (Good Friday, Holy Saturday, Easter Monday) are added "
             "as company-wide Public Holidays.",
    )
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
        help="Company whose working calendar receives the holidays.",
    )

    def action_generate(self):
        self.ensure_one()
        created = self.company_id._generate_bg_public_holidays(self.year)
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Public Holidays %s', self.year),
            'res_model': 'resource.calendar.leaves',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)] if created else
                      [('resource_id', '=', False),
                       ('calendar_id', '=', self.company_id.resource_calendar_id.id)],
        }
