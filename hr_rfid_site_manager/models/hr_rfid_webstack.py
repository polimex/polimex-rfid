from odoo import fields, models, api


class HrRFIDWebStack(models.Model):
    _inherit = 'hr.rfid.webstack'

    site_id = fields.Many2one('hr.rfid.site', string='Site', ondelete='set null')
