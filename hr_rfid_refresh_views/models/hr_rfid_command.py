from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)
class HrRfidCommands(models.Model):
    # Commands we have queued up to send to the controllers
    _name = 'hr.rfid.command'
    _description = 'Command to controller'
    _inherit = ['hr.rfid.command', 'refresh.mixin']

    _refresh_on_create = True
    _refresh_on_write = True

    def get_company_id(self):
        return self.webstack_id.company_id.id