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

    # Order matters: the card is the authoritative owner of a user event; the
    # webstack owns a controller event; the door is the fallback that also
    # carries the company of camera-originated events (its company_id is
    # computed from the bound camera in polimex_ip_cam).
    _company_source_fields = ('card_id', 'webstack_id', 'door_id')

    def get_company_id(self):
        # Return the company from the first source that is actually populated.
        # A source field can exist in the schema yet be empty on the record
        # (e.g. webstack_id on a camera system event); short-circuiting on the
        # mere presence of the field would return an empty company and silently
        # skip the realtime refresh, so fall through empty sources instead.
        for field_name in self._company_source_fields:
            if field_name in self._fields:
                company = self[field_name].company_id
                if company:
                    return company
        return False
