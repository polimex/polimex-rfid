# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    forgotten_badge_policy = fields.Selection(
        related='company_id.forgotten_badge_policy', readonly=False)
    forgotten_badge_penalty_hours = fields.Float(
        related='company_id.forgotten_badge_penalty_hours', readonly=False)
