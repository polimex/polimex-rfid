from odoo import fields, models, api


class Company(models.Model):
    _name = "res.company"
    _inherit = "res.company"
    _description = 'Company'

    realtime_refresh = fields.Boolean(
        help='Realtime Refresh of views based on hardware events',
        default=False
    )
