from odoo import fields, models, api


class HrRfidReader(models.Model):
    _name = 'hr.rfid.reader'
    _inherit = 'hr.rfid.reader'

    camera_id = fields.Many2one(
        comodel_name="cctv.camera",
        string="Camera",
        help="ANPR camera assigned to this reader. When set, the door inherits the camera link and card assignments are mirrored to the camera's whitelist.",
    )
