from odoo import fields, models, api, _


class EmergencyGroup(models.Model):
    _name = 'hr.rfid.ctrl.emergency.group'
    _inherit = ['hr.rfid.ctrl.emergency.group']

    def _internal_state_change_call(self, state):
        return #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        doors = self.env['hr.rfid.door']
        for g in self:
            doors += g.controller_ids.door_ids
        doors.refresh_views()
