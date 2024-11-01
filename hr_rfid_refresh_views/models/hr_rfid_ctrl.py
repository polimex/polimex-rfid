from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class HrRfidController(models.Model):
    _name = 'hr.rfid.ctrl'
    _inherit = ['hr.rfid.ctrl', 'refresh.mixin']
    _description = 'Controller'

    _refresh_on_create = True
    _refresh_on_write = True
