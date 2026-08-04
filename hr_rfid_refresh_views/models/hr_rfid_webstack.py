from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class HrRfidWebstack(models.Model):
    _name = 'hr.rfid.webstack'
    _inherit = ['hr.rfid.webstack', 'refresh.mixin']
    _description = 'Module'

    # Real-time refresh settings: Update views when webstacks are created or modified
    _refresh_on_create = True  # Refresh when new modules are connected
    _refresh_on_write = True   # Refresh when module status/settings change

    def get_company_ids(self):
        # A shared module concerns every company that uses it.
        return self.company_id | self.sudo().shared_company_ids
