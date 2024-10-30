from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class HrRfidCtrlAlarmGroup(models.Model):
    _name = 'hr.rfid.ctrl.alarm.group'
    _description = 'Alarm system groups'
    _inherit = ['hr.rfid.ctrl.alarm.group', 'refresh.mixin']

    _refresh_on_create = True
    _refresh_on_write = True
