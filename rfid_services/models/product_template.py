# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Product(models.Model):
    _inherit = 'product.template'

    is_rfid_service = fields.Boolean(default=False)

    access_group_ids = fields.One2many(
        comodel_name='rfid.service.product.ag.rel',
        inverse_name='product_id'
    )
    parent_id = fields.Many2one(
        string='Master partner',
        help='The main company where automaticly generated partners will belongs to.',
        comodel_name='res.partner',
        domain=[('is_company', '=', True)],
    )

