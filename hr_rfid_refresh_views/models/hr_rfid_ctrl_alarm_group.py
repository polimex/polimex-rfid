from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class HrRfidCtrlAlarmGroup(models.Model):
    _name = 'hr.rfid.ctrl.alarm.group'
    _description = 'Alarm system groups'
    _inherit = ['hr.rfid.ctrl.alarm.group', 'refresh.mixin']

    # Real-time refresh settings: Update views when alarm groups are created or modified
    _refresh_on_create = True  # Refresh when new alarm groups are created
    _refresh_on_write = True   # Refresh when alarm group status/settings change
