# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AutoVacuum(models.AbstractModel):
    _inherit = 'ir.autovacuum'

    @api.model
    def power_on(self, *args, **kwargs):
        res = super(AutoVacuum, self).power_on(*args, **kwargs)
        self.env['hr_rfid.event_user'].garbage_collector(*args, **kwargs)
        self.env['hr.rfid.event.system'].garbage_collector(*args, **kwargs)
        return res
