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
        help="Company whose people get the holidays - everybody in it, "
             "whatever working schedule they are on.",
    )

    def action_generate(self):
        """Fill the year in and show the company's public holidays of it.

        The whole year, not only the days just made: an official day another
        public holiday of the company already holds is not added, and the
        holiday that holds it is in the list in its place.
        """
        self.ensure_one()
        self.company_id._generate_bg_public_holidays(self.year)
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Public Holidays %s', self.year),
            'res_model': 'resource.calendar.leaves',
            'view_mode': 'list,form',
            'domain': self.company_id._bg_public_holidays_domain(self.year),
        }
