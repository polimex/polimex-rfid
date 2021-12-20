from odoo import fields, models


class RfidSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    event_lifetime = fields.Integer(string='Event life time', default=365,
                                    config_parameter='hr_rfid.event_lifetime',
                                    help='Enter event lifetime. Older events will be deleted')
    module_hr_rfid_vending = fields.Boolean(string="Vending Control")
    module_rfid_pms_base = fields.Boolean(string="PMS Base functionality")
    module_hr_rfid_andromeda_import = fields.Boolean(string="Andromeda Import")


