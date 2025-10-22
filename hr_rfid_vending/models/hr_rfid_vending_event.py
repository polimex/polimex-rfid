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
        string='Event Type',
        help="""Type of vending machine event that occurred.
        
• Purchase Complete (47): Successful product purchase transaction
• Collect cash (50): Cash collection or management event
• Error (48/49): Various machine error conditions
• Bad Data Error (-1): Communication or data parsing error
        
Most common events are successful purchases (47).""",
    )

    # event_time = fields.Datetime(
    #     string='Timestamp',
    #     help='Time the event triggered',
    #     required=True,
    #     index=True,
    # )

    transaction_price = fields.Float(
        string='Transaction Amount',
        default=-1,
        help="""Amount charged for this vending transaction.
        
• Currency: Uses machine's configured currency/pricelist
• Source: Price determined by product configuration and machine pricelist
• Balance impact: This amount is deducted from employee's vending balance
• Value -1: Indicates no transaction amount (for non-purchase events)
        
Shows the actual cost of the purchased item."""
    )

    item_sold = fields.Integer(
        string='Item Slot Number',
        aggregator='count_distinct',
        help="""Physical slot/position number in the vending machine where the item was located.
        
• Hardware reference: Corresponds to machine's physical product slots
• Configuration: Used to map physical slots to products
• Maintenance: Helps identify which machine sections are most used
• Restocking: Useful for inventory management and restocking planning
        
This is the machine's internal slot identifier, not the product ID."""
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
        help="""RFID controller/vending machine where this event occurred.
        
• Location tracking: Identifies which machine was used
• Machine management: Links events to specific hardware units
• Reporting: Enables machine-specific sales and usage analysis
• Maintenance: Helps track machine performance and issues
        
Useful for multi-machine installations and location-based reporting."""
    )

    command_id = fields.Many2one(
        'hr.rfid.command',
        string='System Response',
        readonly=True,
        ondelete='set null',
        index=True,
        help="""System command sent to the vending machine in response to this event.

• Communication: Links events to system responses and commands
• Debugging: Useful for troubleshooting communication issues
• Audit trail: Shows system's response to vending events
• Technical: Primarily used for system administration and debugging

Mostly relevant for technical users and system troubleshooting."""
    )

    item_sold_id = fields.Many2one(
        'product.template',
        string='Product Purchased',
        help="""Product that was purchased in this vending transaction.
        
• Product tracking: Links sales events to specific products
• Inventory: Helps track which products are selling well
• Reporting: Enables product-specific sales analysis
• Pricing: Connected to product price and pricelist settings
        
Empty for non-purchase events (errors, cash collection, etc.).""",
        ondelete='set null',
    )

    input_js = fields.Char(
        string='Raw Event Data',
        help="""Original JSON data received from the vending machine hardware.
        
• Debugging: Raw communication data for technical troubleshooting
• Audit: Complete record of machine communication
• Privacy: Only saved if 'Save Webstack Communications' is enabled
• Technical: Primarily for system administrators and developers
        
Contains technical details about the hardware communication."""
    )

    @api.autovacuum
    def _gc_delete_old_vending_events(self):
        for c in self.env['res.company'].search([]):
            if c.event_lifetime is None:
                return False
            lifetime = timedelta(days=int(c.event_lifetime))
            today = fields.Date.today()
            res = self.with_company(c).search([
                ('event_time', '<', today - lifetime)
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
