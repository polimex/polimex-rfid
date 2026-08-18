from odoo import fields, models, api


class HrRfidController(models.Model):
    _inherit = 'hr.rfid.ctrl'

    site_id = fields.Many2one(
        'hr.rfid.site',
        string='Site',
        ondelete='set null',
        help="Physical site where this controller is installed. Used for organizing "
             "controllers by location and for site-based access control and reporting."
    )
