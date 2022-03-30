from odoo import fields, models, api, _

import logging
_logger = logging.getLogger(__name__)


class HrRfidUserEvent(models.Model):
    _name = 'hr.rfid.event.user'
    _inherit = "hr.rfid.event.user"

    def create(self, vals_list):
        res = super(HrRfidUserEvent, self).create(vals_list)
        res.refresh_views()
        return res

    def write(self, vals):
        res = super(HrRfidUserEvent, self).write(vals)
        self.refresh_views()
        return res
