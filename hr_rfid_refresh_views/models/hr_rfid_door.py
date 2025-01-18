from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


class HrRfidDoor(models.Model):
    _name = 'hr.rfid.door'
    _description = 'Door'
    _inherit = ['hr.rfid.door', 'refresh.mixin']

    _refresh_on_create = False
    _refresh_on_write = True

    def get_company_id(self):
        return self.webstack_id.company_id