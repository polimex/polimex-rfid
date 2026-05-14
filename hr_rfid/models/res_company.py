from odoo import fields, models, api


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    event_lifetime = fields.Integer(
        string='Event life time',
        default=365,
        help='Enter event lifetime. Older events will be deleted',
    )
    card_input_type = fields.Selection(
        selection=[
            ('w34','Wiegand 34 bit (5d+5d)'),
            ('w34s','Wiegand 34 bit (10d)'),
        ],
        default='w34',
        help="Format readers in this company report card numbers in — Wiegand 34 (5d+5d): facility code + card number separated; Wiegand 34 (10d): single 10-digit decimal. Set to match how cards are printed/sourced.",
    )


    @api.model_create_multi
    def create(self, values_list):
        res = super(ResCompany, self).create(values_list)
        self.env['hr.rfid.time.schedule'].set_company_ts()
        return res