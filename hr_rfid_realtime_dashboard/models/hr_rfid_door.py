from odoo import fields, models, api, _, exceptions, SUPERUSER_ID

class HrRfidDoor(models.Model):
    _name = 'hr.rfid.door'
    _description = 'Door'
    _inherit = ['hr.rfid.door']

    def write(self, vals):
        res = super(HrRfidDoor, self).write(vals)
        res.refresh_views()
        return res

