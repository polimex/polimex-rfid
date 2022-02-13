import datetime

from odoo import fields, models, api, exceptions
from dateutil.relativedelta import relativedelta

_intervalTypes = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}



class RFIDServiceSales(models.Model):
    _name = 'rfid.service.sale'
    _description = 'List of RFID Services sales'

    name = fields.Char(
        # default=lambda self: self.env['ir.sequence'].next_by_code('rfid.service.sale'),
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'In process'),
        ('expire', 'Expired'),
        ('cancel', 'Canceled')
        ], default='draft'
    )
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        domain=[('is_company', '=', False)],
    )
    product_id = fields.Many2one(
        comodel_name='product.template',
        required=True,
        domain=[('is_rfid_service', '=', True)],

    )
    card_number = fields.Char(
        string='The card number',
        size=10, required=True
    )
    activate_on = fields.Datetime(
        string='Activate on',
        help='Service Activation time',
        compute='_compute_expire_on'
    )
    expire_on = fields.Datetime(
        string='Expire on',
        help='Service Expiration time',
        compute='_compute_expire_on'
    )
    is_expired = fields.Boolean(
        compute='_compute_expire_on'
    )

    @api.depends('activate_on', 'product_id')
    def _compute_expire_on(self):
        for sale in self:
            sale.activate_on = min([fields.Datetime.now()]+[ag.get_start_timestamp(fields.Datetime.now()) for ag in sale.product_id.access_group_ids])
            sale.expire_on = max([fields.Datetime.now()]+[ag.get_end_timestamp(sale.activate_on) for ag in sale.product_id.access_group_ids])
            sale.is_expired = sale.expire_on < fields.Datetime.now()

    def confirm_action(self):
        for s in self:
            s.activate_on = fields.Datetime.now()
            if not s.partner_id:
                s.partner_id = self.env['res.partner'].with_context(activate_on=s.activate_on, deactivate_on=s.expire_on).generate_partner(
                    name=s.name,
                    parent_id=s.product_id.parent_id and s.product_id.parent_id.id or None,
                    card_number=s.card_number
                )
            elif s.card_number not in s.partner_id.card_ids.mapped('number'):
                s.partner_id.add_card_number(
                    card_number=s.card_number,
                    activate_on=s.activate_on,
                    expire_on=s.expire_on
                )
            for ag_rel in s.product_id.access_group_ids:
                start, end = ag_rel.calculate_activate_expire(s.activate_on)
                s.partner_id.add_access_group(
                    access_group_id=ag_rel.access_group_id.id,
                    activate_on=ag_rel.get_start_timestamp(s.activate_on),
                    expire_on=ag_rel.get_end_timestamp(s.activate_on),
                    visits=ag_rel.visit_count
                )
            s.state = 'active'

                # .with_context({
                # 'activate_on': fields.Datetime.now(),  # !!!!!!!!!!!!!!!!!!!!!!!!!!
                # 'deactivate_on': fields.Datetime.now()  # !!!!!!!!!!!!!!!!!!!!!!!!!!
                # })
                #     if not vals.get('partner_id', False):
                #         self.env['product.template'].browse(vals['product_id']).mapped(
                #             'access_group_ids.access_group_id.id')
                #
                #     partner_id = self.env['res.partner'].with_context({
                #         'activate_on': fields.Datetime.now(),  # !!!!!!!!!!!!!!!!!!!!!!!!!!
                #         'deactivate_on': fields.Datetime.now()  # !!!!!!!!!!!!!!!!!!!!!!!!!!
                #     }).generate_partner(
                #         name=vals['name'],
                #         card_number=vals['card_number'],
                #         access_group_ids=
                #
                #     )
                #     vals['partner_id'] = partner_id.id

    def cancel_action(self):
        for s in self:
            product_ag_rel_ids = s.partner_id.hr_rfid_access_group_ids.filtered(lambda ag: ag.access_group_id.id in s.product_id.access_group_ids.mapped('access_group_id.id'))
            # remove access groups for this service
            product_ag_rel_ids.unlink()
            # remove cards for this service
            s.partner_id.hr_rfid_card_ids.filtered(lambda c: s.card_number in c.number ).unlink()
            s.state = 'cancel'
    @api.model
    def create(self, vals):
        if not vals.get('name', False):
            vals['name'] = self.env['ir.sequence'].next_by_code('rfid.service.sale')
        return super().create(vals)

    def unlink(self):
        for s in self:
            if s.state == 'cancel':
                super(RFIDServiceSales, s).unlink()
            else:
                raise exceptions.ValidationError('First stop service before try to delete')


