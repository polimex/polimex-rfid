from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class HRRFIDEvent(models.AbstractModel):
    _name = 'hr.rfid.event'
    _inherit = ['hr.rfid.event', 'refresh.mixin']
    _description = "Helper for RFID Events"

    # Real-time refresh settings: Update views when new events are created (not on edits)
    _refresh_on_create = True   # Refresh when new RFID events occur (real-time monitoring)
    _refresh_on_write = False   # Don't refresh on event edits (events rarely change)

    def get_company_id(self):
        # check if model have field employee_id, contact_id, webstack_id
        # if 'employee_id' in self._fields:
        #     return self.employee_id.company_id.id
        # if 'contact_id' in self._fields:
        #     return self.contact_id.company_id.id
        if 'card_id' in self._fields:
            return self.card_id.company_id
        if 'webstack_id' in self._fields:
            return self.webstack_id.company_id
        if 'door_id' in self._fields:
            return self.door_id.company_id
