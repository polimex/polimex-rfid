from odoo import fields, models, api

class HrRfidCtrlAlarmGroup(models.Model):
    _inherit = 'hr.rfid.ctrl.alarm.group'

    site_id = fields.Many2one(
        'hr.rfid.site', 
        string='Site', 
        ondelete='set null',
        help="Site where this alarm group is active. Used for organizing security systems "
             "by location and enabling site-wide alarm control operations."
    )
