from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class HrRfidCommands(models.Model):
    # Commands we have queued up to send to the controllers
    _name = 'hr.rfid.command'
    _description = 'Command to controller'
    _inherit = ['hr.rfid.command', 'refresh.mixin']

    # Real-time refresh settings: Update views when commands are queued or processed
    _refresh_on_create = True  # Refresh when new commands are queued
    _refresh_on_write = True   # Refresh when command status changes (sent, executed, failed)

    def get_company_id(self):
        return self.webstack_id.company_id