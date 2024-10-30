from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class HRRFIDEvent(models.AbstractModel):
    _name = 'hr.rfid.event'
    _inherit = ['hr.rfid.event', 'refresh.mixin']
    _description = "Helper for RFID Events"

    _refresh_on_create = True
    _refresh_on_write = False

    def get_company_id(self):
        # check if model have field employee_id, contact_id, webstack_id
        if 'employee_id' in self._fields:
            return self.employee_id.company_id.id
        if 'contact_id' in self._fields:
            return self.contact_id.company_id.id
        if 'webstack_id' in self._fields:
            return self.webstack_id.company_id.id
        return self.env.company.id or 0
