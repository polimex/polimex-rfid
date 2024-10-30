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
        return self.empolyee_id and self.empolyee_id.company_id.id or self.contact_id and self.contact_id.company_id.id or self.webstack_id and self.webstack_id.company_id.id or 0