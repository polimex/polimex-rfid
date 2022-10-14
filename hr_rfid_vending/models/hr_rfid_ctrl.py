from odoo import fields, models, api, _, exceptions


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
        default=0
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
        rows = self.env['hr.rfid.ctrl.vending.row']
        for ctrl in self:
            vend_rows_env.search([('controller_id', '=', ctrl.id)]).unlink()
            row_len = 8 * 2
            last_row = 18 * row_len

            for i in range(0, last_row, row_len):
                creation_dict = {
                    'row_num': str(int(i / row_len) + 1),
                    'controller_id': ctrl.id,
                }
                rows += vend_rows_env.create([creation_dict])
        return rows
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
