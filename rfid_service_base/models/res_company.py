from odoo import fields, models, api


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, values_list):
        res = super(ResCompany, self).create(values_list)
        self.env.ref('rfid_service_base.seq_base_service_reservation').copy({'company_id': res.id})
        return res
