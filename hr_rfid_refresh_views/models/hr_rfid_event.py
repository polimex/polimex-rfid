from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class HRRFIDEvent(models.AbstractModel):
    _name = 'hr.rfid.event'
    _inherit = ['hr.rfid.event', 'refresh.mixin']
    _description = "Helper for RFID Events"

    _refresh_on_create = True
    _refresh_on_write = False

    # Order matters: card = authoritative owner of a user event; webstack owns a
    # controller event; door is the fallback that carries the company for
    # controller-less events. (backport 139e5c1)
    _company_source_fields = ('card_id', 'webstack_id', 'door_id')

    def get_company_id(self):
        # Return the company from the first source that is actually POPULATED.
        # A source field can exist in the schema yet be empty on the record, so
        # short-circuiting on the mere presence of the field returned an empty
        # company and skipped the per-company realtime refresh notification.
        for field_name in self._company_source_fields:
            if field_name in self._fields:
                company = self[field_name].company_id
                if company:
                    return company
        return False
