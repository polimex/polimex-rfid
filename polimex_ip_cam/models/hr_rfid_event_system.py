import json
from datetime import timedelta

from odoo import fields, models, api, exceptions, _

import logging
_logger = logging.getLogger(__name__)


class HrRfidSystemEvent(models.Model):
    _name = 'hr.rfid.event.system'
    _inherit = 'hr.rfid.event.system'

    camera_id = fields.Many2one(
        comodel_name='cctv.camera',
        string='Camera',
        ondelete='cascade',
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
    # Може да добавите и други специфични полета, например:
    anpr_confidence = fields.Integer(
        string='Confidence Level',
        help="The confidence level of the event"
    )
