from odoo import fields, models, api


class RFIDServiceMembers(models.TransientModel):
    _name = 'rfid.service.sale.wiz'
    _description = 'RFID Service Sale Wizard'

    def _get_partner_id(self):
        if self.env.context.get('partner', False):
            return self.env['res.partner'].browse(self._context.get("active_id", []))

    def _get_product_id(self):
        if self.env.context.get('product', False):
            return self.env['product.template'].browse(self._context.get("active_id", []))

    def _get_rfid_sale_id(self):
        if self.env.context.get('rfid_sale', False):
            return self.env['rfid.service.sale'].browse(self._context.get("active_id", []))

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        domain=[('is_company', '=', False)],
        default=_get_partner_id
    )
    product_id = fields.Many2one(
        comodel_name='product.template',
        default=_get_product_id,
    )
    sale_id = fields.Many2one(
        comodel_name='rfid.service.sale',
        default=_get_rfid_sale_id,
    )
    card_number = fields.Char(string='The card number', size=10, required=True)


