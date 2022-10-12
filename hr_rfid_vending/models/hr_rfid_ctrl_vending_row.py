from odoo import api, fields, models, exceptions, _



class HrRfidVendingRow(models.Model):
    _name = 'hr.rfid.ctrl.vending.row'
    _description = 'Vending Machine Row'
    _order = 'row_num'

    row_num = fields.Integer(required=True, readonly=True)
    controller_id = fields.Many2one('hr.rfid.ctrl', required=True, readonly=True, ondelete='cascade')

    item_number1 = fields.Char(string='#', compute='_compute_number_1')
    item_number2 = fields.Char(string='#', compute='_compute_number_2')
    item_number3 = fields.Char(string='#', compute='_compute_number_3')
    item_number4 = fields.Char(string='#', compute='_compute_number_4')
    item1  = fields.Many2one('product.template', string='Item#1')
    item2  = fields.Many2one('product.template', string='Item#2')
    item3  = fields.Many2one('product.template', string='Item#3')
    item4  = fields.Many2one('product.template', string='Item#4')

    def _compute_number_1(self):
        for row in self:
            row.item_number1 = 'Item #' + str((row.row_num - 1)*4 + 1) + ':'

    def _compute_number_2(self):
        for row in self:
            row.item_number2 = 'Item #' + str((row.row_num - 1)*4 + 2) + ':'

    def _compute_number_3(self):
        for row in self:
            row.item_number3 = 'Item #' + str((row.row_num - 1)*4 + 3) + ':'

    def _compute_number_4(self):
        for row in self:
            row.item_number4 = 'Item #' + str((row.row_num - 1)*4 + 4) + ':'
