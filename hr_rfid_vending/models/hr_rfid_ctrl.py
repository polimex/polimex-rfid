from odoo import fields, models, api, _, exceptions

# Vending firmwares that keep the price table Odoo writes and report the price
# of every sale: 16 and 20. The MDB firmware (21) keeps its prices in the
# machine and its sale events carry the credit left, not the price, so Odoo
# cannot book its sales yet and gives it no credit.
PRICE_TABLE_HW_VERSIONS = ('16', '20')


class HrRfidControllerVending(models.Model):
    _name = 'hr.rfid.ctrl'
    _inherit = 'hr.rfid.ctrl'

    show_price_timeout = fields.Integer(
        string='Price Display Timeout',
        help="""Duration (in seconds) that product prices remain visible on the vending machine screen.
        
• Purpose: Control how long prices are displayed after selection
• Hardware: Automatically computed from controller's IO table configuration
• User experience: Longer timeouts give users more time to see prices
• Power saving: Shorter timeouts save screen power and reduce wear
        
This value is read from the vending machine's hardware settings.""",
        compute='_compute_show_price_timeout',
    )

    scale_factor = fields.Integer(
        string='Price Scale Factor',
        help="""Multiplier used to convert currency amounts to vending machine units.
        
• Purpose: Convert monetary values to hardware-compatible format
• Hardware: Automatically computed from controller's IO table configuration
• Calculation: Used internally for balance and price conversions
• Example: Scale factor of 100 means 1.50 currency = 150 machine units
        
This value is read from the vending machine's hardware settings.""",
        compute='_compute_scale_factor',
    )

    cash_contained = fields.Float(
        string='Cash in Machine',
        help="""Current amount of physical cash stored in the vending machine.
        
• Purpose: Track cash accumulation from sales for collection purposes
• Updates: Automatically increased with each cash purchase
• Collection: Reduced when cash is physically collected from machine
• Management: Use cash collection wizard to record cash removal
        
Helps manage cash flow and collection schedules for vending operations.""",
        default=0
    )

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Product Pricelist',
        help="""Pricelist used to determine product prices for this vending machine.
        
• Purpose: Set custom pricing for different vending machine locations
• Flexibility: Different machines can have different pricing strategies
• Integration: Works with Odoo's standard pricelist functionality
• Examples: Discounted prices for staff areas, premium pricing for visitor areas
        
Leave empty to use default product prices."""
    )

    is_vending = fields.Boolean(
        string='Is a Vending Machine',
        compute='_compute_vending_flags',
        help="Set when the controller runs a vending firmware: it works with card "
             "balances and vending counters instead of doors.",
    )

    has_vending_price_table = fields.Boolean(
        string='Prices Set in Odoo',
        compute='_compute_vending_flags',
        help="Set when the machine sells at the prices entered in Odoo. Machines "
             "that keep their own prices (MDB) do not show the Prices button.",
    )

    @api.depends('hw_version')
    def _compute_vending_flags(self):
        for ctrl in self:
            ctrl.is_vending = ctrl.is_vending_ctrl()
            ctrl.has_vending_price_table = ctrl._vending_has_price_table()

    def _vending_has_price_table(self):
        self.ensure_one()
        return self.hw_version in PRICE_TABLE_HW_VERSIONS

    @api.model
    def _convert_balance_to_ctrl(self, balance):
        self.ensure_one()
        # Balance in machine units: whole cents first, then whole units the
        # cents pay for. In floats 1.15 * 100 / 5 is 22.999..., and int()
        # would offer one unit less than the balance covers.
        cents = int(round(balance * 100))
        balance = cents // self.scale_factor if self.scale_factor > 0 else 0
        if balance > 0xFF:
            balance = 0xFF
        b1 = (balance & 0xF0) // 0x10
        b2 = balance & 0x0F
        return '%02X%02X' % (b1, b2), balance


    def _compute_show_price_timeout(self):
        for ctrl in self:
            if not ctrl.io_table or not ctrl.is_vending_ctrl():
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
            if not ctrl.io_table or not ctrl.is_vending_ctrl():
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
            super(HrRfidControllerVending, ctrl).write(vals)

            # The rows are the price table; a machine that keeps its own
            # prices has none to edit.
            if not ctrl._vending_has_price_table():
                continue

            if 'io_table' in vals:
                vend_rows_env = self.env['hr.rfid.ctrl.vending.row'].sudo()
                vend_rows = vend_rows_env.search([('controller_id', '=', ctrl.id)])
                if len(vend_rows) > 0:
                    continue
                ctrl.create_vending_rows()
