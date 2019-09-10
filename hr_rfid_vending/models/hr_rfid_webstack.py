# -*- coding: utf-8 -*-
from odoo import api, models


class HrRfidControllerVending(models.Model):
    _inherit = 'hr.rfid.ctrl'

    @api.multi
    def write(self, vals):
        for ctrl in self:
            old_hw = ctrl.hw_version
            super(HrRfidControllerVending, ctrl).write(vals)

            new_hw = ctrl.hw_version


