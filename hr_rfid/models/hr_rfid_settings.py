from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    event_lifetime = fields.Integer(string='Event life time', default=365, readonly=False,
                                    related='company_id.event_lifetime',
                                    help='Number of days to keep access events in the system. Events older than '
                                         'this will be automatically deleted to save storage space. Default is 365 days (1 year).')
    save_new_webstacks = fields.Boolean(string="Accept new Modules",
                                        help='Allow the system to automatically register new hardware modules when they connect. '
                                             'Enable this when adding new controllers to your system. Disable for security '
                                             'after all modules are registered. Note: Does not support Multi-Company setups.',
                                        default=False,
                                        config_parameter='hr_rfid.save_new_webstacks',)
    save_webstack_communications = fields.Boolean(string="Debug JSON communication",
                                        help='Save all communication between the system and hardware controllers to logs. '
                                             'Only enable this for troubleshooting hardware issues. It creates large log files '
                                             'and should be disabled during normal operation.',
                                        default=False,
                                        config_parameter='hr_rfid.save_webstack_communications',)
    module_hr_attendance_multi_rfid = fields.Boolean(string="Time & Attendance control",
                                                    help="Enable time tracking features using RFID cards. Employees can check in/out "
                                                         "by scanning their cards at designated readers.")
    module_hr_attendance_late = fields.Boolean(string="Time & Attendance additional calculations",
                                              help="Add advanced attendance calculations like late arrivals, early departures, "
                                                   "and overtime tracking to the basic time & attendance features.")
    module_hr_rfid_vending = fields.Boolean(string="Vending Control",
                                           help="Control vending machines with RFID cards. Allows employees to purchase "
                                                "items from vending machines using their access cards.")
    module_hr_rfid_realtime_dashboard = fields.Boolean(string="Realtime Dashboards",
                                                      help="Display live dashboards showing current access activity, "
                                                           "who's in each area, and real-time security monitoring.")
    module_rfid_pms_base = fields.Boolean(string="PMS Base functionality",
                                         help="Property Management System integration. Allows using RFID system "
                                              "for hotel room access and guest management.")
    module_hr_rfid_andromeda_import = fields.Boolean(string="Andromeda Import",
                                                    help="Import data from Andromeda access control systems. "
                                                         "Use this to migrate from an existing Andromeda installation.")

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

