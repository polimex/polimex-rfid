from odoo import fields, models, api


class HrRfidReader(models.Model):
    _inherit = 'hr.rfid.reader'

    camera_id = fields.Many2one(
        comodel_name="cctv.camera",
        string="Camera",
    )
