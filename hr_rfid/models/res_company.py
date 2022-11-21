from odoo import fields, models, api


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    event_lifetime = fields.Integer(string='Event life time', default=365,
                                    help='Enter event lifetime. Older events will be deleted')

    @api.model_create_multi
    def create(self, values_list):
        res = super(ResCompany, self).create(values_list)
        self.env['hr.rfid.time.schedule'].set_company_ts()
        return res