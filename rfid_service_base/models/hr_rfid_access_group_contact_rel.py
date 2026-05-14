from odoo import fields, models, api


class HrRfidAccessGroupContactRel(models.Model):
    _name = 'hr.rfid.access.group.contact.rel'
    _inherit = ['hr.rfid.access.group.contact.rel']

    rfid_service_sale_id = fields.One2many(
        comodel_name='rfid.service.sale',
        inverse_name='access_group_contact_rel',
        help="Visitor service sales backed by this contact-to-access-group binding. Used to cascade state changes to all related sales when the underlying relation activates or expires.",
    )

    def _compute_state(self):
        super()._compute_state()
        self.filtered(lambda x: x.rfid_service_sale_id).rfid_service_sale_id._compute_state()
