# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from datetime import timedelta, datetime
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

    @api.multi
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

    @api.multi
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

    @api.multi
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

    @api.multi
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


class HrRfidVendingRow(models.Model):
    _name = 'hr.rfid.ctrl.vending.row'
    _description = 'Vending Machine Row'

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

    @api.multi
    def _compute_number_1(self):
        for row in self:
            row.item_number1 = 'Item #' + str((row.row_num - 1)*4 + 1) + ':'

    @api.multi
    def _compute_number_2(self):
        for row in self:
            row.item_number2 = 'Item #' + str((row.row_num - 1)*4 + 2) + ':'

    @api.multi
    def _compute_number_3(self):
        for row in self:
            row.item_number3 = 'Item #' + str((row.row_num - 1)*4 + 3) + ':'

    @api.multi
    def _compute_number_4(self):
        for row in self:
            row.item_number4 = 'Item #' + str((row.row_num - 1)*4 + 4) + ':'


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

    @api.multi
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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def write(self, vals):
        if 'list_price' not in vals:
            return super(ProductTemplate, self).write(vals)

        vend_rows_env = self.env['hr.rfid.ctrl.vending.row']
        vend_settings_env = self.env['hr.rfid.ctrl.vending.settings']

        # rec stands for record
        for rec in self:
            old_list_price = rec.list_price
            super(ProductTemplate, rec).write(vals)
            new_list_price = rec.list_price

            if old_list_price != new_list_price:
                ret = vend_rows_env.search([
                    '|', '|', '|',
                        ('item1', '=', rec.id),
                        ('item2', '=', rec.id),
                        ('item3', '=', rec.id),
                        ('item4', '=', rec.id),
                ])
                if len(ret) == 0:
                    continue

                wiz = vend_settings_env.with_context(active_ids=[ret.controller_id.id]).create({})
                wiz.save_settings()


class VendingEvents(models.Model):
    _name = 'hr.rfid.vending.event'
    _description = 'RFID Vending Event'
    _order = 'id desc'

    action_selection = [
        ('-1', 'Bad Data Error'),
        ('47', 'Purchase Complete'),
        ('48', 'Error'),  # TODO What type of error?
        ('49', 'Error'),  # TODO What type of error?
        ('64', 'Requesting User Balance'),
    ]

    name = fields.Char(
        string='Document Name',
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('hr.rfid.vending.event.seq'),
    )

    event_action = fields.Selection(
        selection=action_selection,
        string='Action',
        help='What happened to trigger the event',
        required=True,
    )

    event_time = fields.Datetime(
        string='Timestamp',
        help='Time the event triggered',
        required=True,
        index=True,
    )

    transaction_price = fields.Float(
        string='Transaction Price',
        default=-1,
    )

    item_sold = fields.Integer(
        string='Item Sold Number',
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        ondelete='set null',
    )

    card_id = fields.Many2one(
        'hr.rfid.card',
        string='Card',
    )

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        string='Vending Machine',
    )

    command_id = fields.Many2one(
        'hr.rfid.command',
        string='Response',
        readonly=True,
        ondelete='set null',
    )

    item_sold_id = fields.Many2one(
        'product.template',
        string='Item Sold',
        help='The item that was sold in the transaction',
        ondelete='set null',
    )

    input_js = fields.Char(
        string='Input JSON',
    )

    @api.model
    def _delete_old_events(self):
        event_lifetime = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.event_lifetime')
        if event_lifetime is None:
            return False

        lifetime = timedelta(days=int(event_lifetime))
        today = datetime.today()
        res = self.search([
            ('event_time', '<', today-lifetime)
        ])
        res.unlink()

        return self.env['hr.rfid.event.system'].delete_old_events()

    def _check_save_comms(self, vals):
        save_comms = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.save_webstack_communications')
        if save_comms != 'True':
            if 'input_js' in vals:
                vals.pop('input_js')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_save_comms(vals)
        return super(VendingEvents, self).create(vals_list)

    @api.multi
    def write(self, vals):
        self._check_save_comms(vals)
        return super(VendingEvents, self).write(vals)

    @api.model
    @api.returns('self',
                 upgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False:
                 value if count else self.browse(value),
                 downgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False:
                 value if count else value.ids)
    def search(self, *args, **kwargs):
        ret = super(VendingEvents, self).search(*args, **kwargs)

        if type(ret) == type(self):
            user = self.env.user
            has_customer = user.has_group('hr_rfid_vending.group_customer')
            has_operator = user.has_group('hr_rfid_vending.group_operator')

            if has_customer and not has_operator:
                ret = ret.filtered(lambda a: a.employee_id)

        return ret
