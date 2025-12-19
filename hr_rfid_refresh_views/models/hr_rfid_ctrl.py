from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class HrRfidController(models.Model):
    _name = 'hr.rfid.ctrl'
    _inherit = ['hr.rfid.ctrl', 'refresh.mixin']
    _description = 'Controller'

    # Real-time refresh settings: Update views when controllers are created or modified
    _refresh_on_create = True  # Refresh when new controllers are added
    _refresh_on_write = True   # Refresh when controller settings change

    def get_company_id(self):
        return self.webstack_id.company_id
