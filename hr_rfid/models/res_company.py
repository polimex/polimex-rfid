from odoo import fields, models, api


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    event_lifetime = fields.Integer(
        string='Event life time',
        default=365,
        help='Enter event lifetime. Older events will be deleted',
        groups="hr_rfid.hr_rfid_group_officer"
    )
    card_input_type = fields.Selection(
        selection=[
            ('w34','Wiegand 34 bit (5d+5d)'),
            ('w34s','Wiegand 34 bit (10d)'),
        ],
        default='w34'
    )


    @api.model_create_multi
    def create(self, values_list):
        res = super(ResCompany, self).create(values_list)
        self.env['hr.rfid.time.schedule'].set_company_ts()
        return res