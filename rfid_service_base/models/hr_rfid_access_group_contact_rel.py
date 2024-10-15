from odoo import fields, models, api


class HrRfidAccessGroupContactRel(models.Model):
    _inherit = ['hr.rfid.access.group.contact.rel']

    rfid_service_sale_id = fields.One2many(
        comodel_name='rfid.service.sale',
        inverse_name='access_group_contact_rel'
    )

    def _compute_state(self):
        super()._compute_state()
        self.filtered(lambda x: x.rfid_service_sale_id).rfid_service_sale_id._compute_state()
