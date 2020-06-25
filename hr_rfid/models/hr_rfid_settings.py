from odoo import fields, models


class RfidSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    event_lifetime = fields.Integer(string='Event life time', default=365,
                                    config_parameter='hr_rfid.event_lifetime',
                                    help='Enter event lifetime. Older events will be deleted')
    save_webstack_communications = fields.Selection([('True', 'On'),
                                                    ('False', 'Off'),
                                                    ],string='Save WebStack communication', default='False',
                                                    config_parameter='hr_rfid.save_webstack_communications',
                                                    help='Save WebStack communication')



