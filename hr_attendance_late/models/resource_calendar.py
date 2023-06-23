from odoo import api, fields, models

class ResourceCalendar(models.Model):
    _name = 'resource.calendar'
    _inherit = 'resource.calendar'

    daily_ranges_are_shifts = fields.Boolean(default=False)
