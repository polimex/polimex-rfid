from odoo import fields, models

class HrAttendanceRfidSetings(models.TransientModel):
    _inherit = 'res.config.settings'

    max_attendance = fields.Integer(string='Max attendance', default='480',
                                    config_parameter='hr_attendance_multi_rfid.max_attendance',
                                    help='How many minutes to get people out automatically. (Checks every 30 minutes)')