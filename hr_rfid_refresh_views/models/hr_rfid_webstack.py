from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class HrRfidWebstack(models.Model):
    _name = 'hr.rfid.webstack'
    _inherit = ['hr.rfid.webstack', 'refresh.mixin']
    _description = 'Module'

    _refresh_on_create = True
    _refresh_on_write = True
