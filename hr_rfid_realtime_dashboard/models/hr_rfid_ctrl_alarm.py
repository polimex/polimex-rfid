import logging

from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class HrRfidCtrlAlarm(models.Model):
    _name = 'hr.rfid.ctrl.alarm'
    _inherit = ['hr.rfid.ctrl.alarm']

    def write(self, vals):
        res = super(HrRfidCtrlAlarm, self).write(vals)
        res.refresh_views()
        return res
