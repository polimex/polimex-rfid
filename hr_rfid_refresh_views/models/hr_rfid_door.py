from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


class HrRfidDoor(models.Model):
    _name = 'hr.rfid.door'
    _description = 'Door'
    _inherit = ['hr.rfid.door', 'refresh.mixin']

    # Real-time refresh settings: Update views when door settings change (not on creation)
    _refresh_on_create = False  # Don't refresh on door creation (less frequent)
    _refresh_on_write = True    # Refresh when door status/settings change

    def get_company_id(self):
        return self.webstack_id.company_id

    def get_company_ids(self):
        return self.webstack_id.get_company_ids()