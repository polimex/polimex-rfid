from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


class HrRfidCtrlAlarm(models.Model):
    _name = 'hr.rfid.ctrl.alarm'
    _inherit = ['hr.rfid.ctrl.alarm', 'refresh.mixin']

    # Real-time refresh settings: Update views when alarm status changes
    _refresh_on_create = False  # Don't refresh on alarm creation (less frequent)
    _refresh_on_write = True    # Refresh when alarm state changes (armed/disarmed/triggered)

    def get_company_id(self):
        return self.controller_id.webstack_id.company_id

    def get_company_ids(self):
        return self.controller_id.webstack_id.get_company_ids()