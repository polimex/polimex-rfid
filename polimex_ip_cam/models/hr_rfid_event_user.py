from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class HrRfidEventUser(models.Model):
    _name = 'hr.rfid.event.user'
    _inherit = 'hr.rfid.event.user'

    camera_id = fields.Many2one(
        comodel_name='cctv.camera',
        string='Camera',
        ondelete='cascade',
        index=True,
        help="Camera to use"
    )
    license_plate = fields.Char(
        string='License Plate',
        help="The license plate recognized by the camera"
    )
    snapshot = fields.Image(
        string='Snapshot',
        help="The snapshot of the camera"
    )
    anpr_confidence = fields.Integer(
        string='Confidence Level',
        help="The confidence level of the event"
    )
