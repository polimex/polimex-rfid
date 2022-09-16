from odoo import fields, models, api
from datetime import timedelta, datetime


class VendingEvents(models.Model):
    _name = 'hr.rfid.vending.event'
    _inherit = 'hr.rfid.event.user'
    _description = 'RFID Vending Event'
    _order = 'id desc'

    action_selection = [
        ('-1', 'Bad Data Error'),
        ('47', 'Purchase Complete'),
        ('48', 'Error'),  # TODO What type of error?
        ('49', 'Error'),  # TODO What type of error?
        ('50', 'Collect cash'),  # TODO What type of error?
        # ('64', 'Requesting User Balance'),
    ]

    # name = fields.Char(
    #     string='Document Name',
    #     readonly=True,
    #     default=lambda self: self.env['ir.sequence'].next_by_code('hr.rfid.vending.event.seq'),
    # )

    event_action = fields.Selection(
        selection_add=action_selection,
        ondelete={'-1': 'cascade',
                  '47': 'cascade',
                  '48': 'cascade',
                  '49': 'cascade',
                  '50': 'cascade'},
        string='Action',
        help='What happened to trigger the event',
    )

    # event_time = fields.Datetime(
    #     string='Timestamp',
    #     help='Time the event triggered',
    #     required=True,
    #     index=True,
    # )

    transaction_price = fields.Float(
        string='Transaction Price',
        default=-1,
    )

    item_sold = fields.Integer(
        string='Item Sold Number',
        group_operator='count_distinct'
    )

    # employee_id = fields.Many2one(
    #     'hr.employee',
    #     string='Employee',
    #     ondelete='set null',
    # )

    # card_id = fields.Many2one(
    #     'hr.rfid.card',
    #     string='Card',
    # )

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

    @api.autovacuum
    def _gc_delete_old_vending_events(self):
        event_lifetime = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.event_lifetime')
        if event_lifetime is None:
            return False

        lifetime = timedelta(days=int(event_lifetime))
        today = datetime.today()
        res = self.search([
            ('event_time', '<', today-lifetime)
        ])
        res.unlink()

        return True

    def _check_save_comms(self, vals):
        save_comms = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.save_webstack_communications') in ['true', 'True']
        if not save_comms:
            if 'input_js' in vals:
                vals.pop('input_js')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_save_comms(vals)
        return super(VendingEvents, self).create(vals_list)

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

    def _compute_user_ev_name(self):
        for record in self:
            if record.event_action == '47':
                name = record.item_sold_id and record.item_sold_id.name or ''
                if record.employee_id:
                    name += ' - %s' % record.employee_id.name
                    
                record.name = name
            else:
                record.name = super(VendingEvents, self)._compute_user_ev_name()
