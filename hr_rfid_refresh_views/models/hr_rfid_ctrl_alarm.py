from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


class HrRfidCtrlAlarm(models.Model):
    _name = 'hr.rfid.ctrl.alarm'
    _inherit = ['hr.rfid.ctrl.alarm', 'refresh.mixin']

    _refresh_on_create = False
    _refresh_on_write = True