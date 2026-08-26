from odoo import api, fields, models, exceptions, _



class HrRfidVendingRow(models.Model):
    _name = 'hr.rfid.ctrl.vending.row'
    _description = 'Vending Machine Row'
    _order = 'row_num'

    row_num = fields.Integer(
        required=True, readonly=True,
        help="Row index inside the vending machine grid (1-based). Each row holds 4 item slots; the global item number is (row_num - 1) * 4 + slot.",
    )
    controller_id = fields.Many2one(
        'hr.rfid.ctrl', required=True, readonly=True, ondelete='cascade',
        help="Vending controller this row belongs to. Cascade on delete — rows do not survive their controller.",
    )

    item_number1 = fields.Char(
        string='Slot 1 Number', compute='_compute_number_1',
        help="Number the buyer presses on the machine keypad for the first slot of this row, computed from row_num (e.g. 'Item #1:' on row 1, 'Item #5:' on row 2).",
    )
    item_number2 = fields.Char(
        string='Slot 2 Number', compute='_compute_number_2',
        help="Number the buyer presses on the machine keypad for the second slot of this row.",
    )
    item_number3 = fields.Char(
        string='Slot 3 Number', compute='_compute_number_3',
        help="Number the buyer presses on the machine keypad for the third slot of this row.",
    )
    item_number4 = fields.Char(
        string='Slot 4 Number', compute='_compute_number_4',
        help="Number the buyer presses on the machine keypad for the fourth slot of this row.",
    )
    item1 = fields.Many2one(
        'product.template', string='Item#1',
        help="Product mapped to the first slot of this row. Determines the name shown on the controller's price screen.",
    )
    item2 = fields.Many2one(
        'product.template', string='Item#2',
        help="Product mapped to the second slot of this row.",
    )
    item3 = fields.Many2one(
        'product.template', string='Item#3',
        help="Product mapped to the third slot of this row.",
    )
    item4 = fields.Many2one(
        'product.template', string='Item#4',
        help="Product mapped to the fourth slot of this row.",
    )

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
