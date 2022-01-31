from odoo import fields, models


class RfidSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    event_lifetime = fields.Integer(string='Event life time', default=365,
                                    config_parameter='hr_rfid.event_lifetime',
                                    help='Enter event lifetime. Older events will be deleted')
    save_new_webstacks = fields.Boolean(string="Accept new Modules",
                                        help='Permit automatic adding modules from communication. This feature do not support Multi Company.',
                                        default=False,
                                        config_parameter='hr_rfid.save_new_webstacks',)
    save_webstack_communications = fields.Boolean(string="Debug JSON communication",
                                        help='Log all hardware communication. Debug purpose only and work in debug mode',
                                        default=False,
                                        config_parameter='hr_rfid.save_webstack_communications',)
    module_hr_attendance_multi_rfid = fields.Boolean(string="Time & Attendance control")
    module_hr_attendance_late = fields.Boolean(string="Time & Attendance additional calculations")
    module_hr_rfid_vending = fields.Boolean(string="Vending Control")
    module_rfid_pms_base = fields.Boolean(string="PMS Base functionality")
    module_hr_rfid_andromeda_import = fields.Boolean(string="Andromeda Import")


