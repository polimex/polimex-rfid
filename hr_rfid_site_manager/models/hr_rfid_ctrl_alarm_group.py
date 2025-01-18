from odoo import fields, models, api

class HrRfidCtrlAlarmGroup(models.Model):
    _inherit = 'hr.rfid.ctrl.alarm.group'

    site_id = fields.Many2one('hr.rfid.site', string='Site', ondelete='set null')
