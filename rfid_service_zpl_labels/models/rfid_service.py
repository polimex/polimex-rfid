from random import randint

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class BaseRFIDService(models.Model):
    _name = 'rfid.service'
    _inherit = 'rfid.service'
    _description = 'RFID Service'

    label_template_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Label Template",
        domain=[("model", "=", "rfid.service.sale")],
        required=True,
        help="Select the label template to use for printing labels/wristbands. ",
    )
    
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'label_template_id' in fields_list:
            try:
                defaults['label_template_id'] = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband').id
            except ValueError:
                pass
        return defaults

