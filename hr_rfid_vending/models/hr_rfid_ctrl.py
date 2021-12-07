from odoo import fields, models, api, _, exceptions
from decimal import Decimal



class HrRfidControllerVending(models.Model):
    _inherit = 'hr.rfid.ctrl'

    show_price_timeout = fields.Integer(
        string='Vending "Show Price" Timeout',
        help='After how long the vending machine will stop showing the product price on the screen',
        compute='_compute_show_price_timeout',
    )

    scale_factor = fields.Integer(
        string='Vending Scale Factor',
        compute='_compute_scale_factor',
    )

    cash_contained = fields.Float(
        string='Cash Contained',
        help='The amount of cash the vending machine currently contains',
    )

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
    )

    def _compute_show_price_timeout(self):
        for ctrl in self:
            if not ctrl.io_table or ctrl.io_table == '' or ctrl.hw_version != '16':
                ctrl.show_price_timeout = 0
                continue

            # (8*2) = each row is 8 numbers, each number is 2 symbols
            # 0x13 is the row number that contains the scale factor, -1 for index reasons
            # 7*2 = skip first 6 numbers, each number is 2 symbols
            index = (8*2)*(0x13-1) + 6*2
            spt = ctrl.io_table[index+1] + ctrl.io_table[index+3]
            ctrl.show_price_timeout = int(spt, 16)

    def _compute_scale_factor(self):
        for ctrl in self:
            if not ctrl.io_table or ctrl.io_table == '' or ctrl.hw_version != '16':
                ctrl.scale_factor = 0
                continue

            # (8*2) = each row is 8 numbers, each number is 2 symbols
            # 0x14 is the row number that contains the scale factor, -1 for index reasons
            # 7*2 = skip first 6 numbers, each number is 2 symbols
            index = (8*2)*(0x14-1) + 6*2
            sf = ctrl.io_table[index+1] + ctrl.io_table[index+3]
            ctrl.scale_factor = int(sf, 16)

    def create_vending_rows(self):
        vend_rows_env = self.env['hr.rfid.ctrl.vending.row'].sudo()

        for ctrl in self:
            vend_rows_env.search([('controller_id', '=', ctrl.id)]).unlink()
            row_len = 8 * 2
            last_row = 18 * row_len

            for i in range(0, last_row, row_len):
                creation_dict = {
                    'row_num': str(int(i / row_len) + 1),
                    'controller_id': ctrl.id,
                }
                vend_rows_env.create([creation_dict])

    def write(self, vals):
        for ctrl in self:
            # If it's not a vending machine
            super(HrRfidControllerVending, ctrl).write(vals)

            if ctrl.hw_version != '16':
                continue

            if 'io_table' in vals:
                vend_rows_env = self.env['hr.rfid.ctrl.vending.row'].sudo()
                vend_rows = vend_rows_env.search([('controller_id', '=', ctrl.id)])
                if len(vend_rows) > 0:
                    continue
                ctrl.create_vending_rows()


class HrRfidVendingSettingsWiz(models.TransientModel):
    _name = 'hr.rfid.ctrl.vending.settings'
    _description = 'Vending Machine Settings'

    def _default_ctrl(self):
        return self.env['hr.rfid.ctrl'].browse(self._context.get('active_ids'))

    def _default_io_rows(self):
        ctrl = self._default_ctrl()
        ret = self.env['hr.rfid.ctrl.vending.row'].search([('controller_id', '=', ctrl.id)])
        if len(ret) == 0:
            ctrl.create_vending_rows()
        ret = self.env['hr.rfid.ctrl.vending.row'].search([('controller_id', '=', ctrl.id)])
        return ret

    def _default_show_price_timeout(self):
        ctrl = self._default_ctrl()
        return ctrl.show_price_timeout

    def _default_scale_factor(self):
        ctrl = self._default_ctrl()
        return ctrl.scale_factor

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        default=_default_ctrl,
        required=True,
        ondelete='cascade',
    )

    vending_row_ids = fields.Many2many(
        'hr.rfid.ctrl.vending.row',
        string='Item/Price',
        default=_default_io_rows,
        required=True,
    )

    show_price_timeout = fields.Integer(
        string='Show Price Timeout',
        help='After how long the vending machine will stop showing the product price on the screen',
        default=_default_show_price_timeout,
        required=True,
    )

    scale_factor = fields.Integer(
        string='Scale Factor',
        default=_default_scale_factor,
        required=True,
    )

    def save_settings(self):
        self.ensure_one()

        def raise_invalid_number(position):
            raise exceptions.ValidationError(
                _('The value of %s is invalid. Must be between 0 and 255') % position
            )

        if self.scale_factor < 0 or self.scale_factor > 255:
            raise_invalid_number('the scale number')
        if self.show_price_timeout < 0 or self.show_price_timeout > 255:
            raise_invalid_number('"show price" timeout')

        vend_rows = self.vending_row_ids.sorted(lambda r: r.row_num)

        if len(vend_rows) == 0:
            raise exceptions.ValidationError(
                "Trying to save settings while we have no rows, this shouldn't be possible???"
            )

        new_io_table = ''

        for row in vend_rows:
            items = [ row.item4, row.item3, row.item2, row.item1 ]
            for item in items:
                if len(item) == 0:
                    new_io_table += '0F0F'
                    continue

                price = None

                if self.controller_id.pricelist_id:
                    price = self.controller_id.pricelist_id.get_product_price(item, 1, None)

                if price is None:
                    price = Decimal(str(item.list_price))

                price *= 100
                price /= self.scale_factor
                price = int(price)
                if price < 0 or price > 255:
                    raise exceptions.ValidationError(
                        _('item %s: %f is not a valid price. Must be between %f and %f')
                        % (item.name, item.list_price, 0*(self.scale_factor/100), 255*(self.scale_factor/100))
                    )
                new_io_table += '%02X%02X' % (int((price & 0xF0) / 0x10), price & 0x0F)

        spt1 = int((self.show_price_timeout & 0xF0) / 0x10)
        spt2 = self.show_price_timeout & 0x0F
        sf1 = int((self.scale_factor & 0xF0) / 0x10)
        sf2 = self.scale_factor & 0x0F

        new_io_table += '000000000000%02X%02X' % (spt1, spt2)
        new_io_table += '000000000000%02X%02X' % (sf1, sf2)
        self.controller_id.change_io_table(new_io_table)
