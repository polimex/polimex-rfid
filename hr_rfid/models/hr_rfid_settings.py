from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    event_lifetime = fields.Integer(string='Event life time', default=365, readonly=False,
                                    related='company_id.event_lifetime',
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
    module_hr_rfid_realtime_dashboard = fields.Boolean(string="Realtime Dashboards")
    module_rfid_pms_base = fields.Boolean(string="PMS Base functionality")
    module_hr_rfid_andromeda_import = fields.Boolean(string="Andromeda Import")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        company = self.env.company
        res.update({
            'event_lifetime': company.event_lifetime,
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        company = self.env.company
        # Done this way to have all the values written at the same time,
        # to avoid recomputing the overtimes several times with
        # invalid company configurations
        fields_to_check = [
            'event_lifetime',
        ]
        if any(self[field] != company[field] for field in fields_to_check):
            company.write({field: self[field] for field in fields_to_check})

