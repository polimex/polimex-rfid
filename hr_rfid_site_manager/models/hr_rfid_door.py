from odoo import fields, models, api


class HrRFIDDoor(models.Model):
    _inherit = 'hr.rfid.door'

    site_id = fields.Many2one('hr.rfid.site', string='Site' , ondelete='set null')
