from odoo import fields, models, api


class HrRFIDWebStack(models.Model):
    _inherit = 'hr.rfid.webstack'

    site_id = fields.Many2one(
        'hr.rfid.site',
        string='Site',
        ondelete='set null',
        help="Physical site where this communication module (webstack) is installed. "
             "Used for organizing network infrastructure and site-based management."
    )
