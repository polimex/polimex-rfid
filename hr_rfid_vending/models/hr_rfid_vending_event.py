from odoo import fields, models, api
from datetime import timedelta, datetime

import logging
_logger = logging.getLogger(__name__)


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
        """
        Clean up old vending event records per company based on event_lifetime setting.

        Follows Odoo 19 core patterns:
        - Direct SQL for performance (similar to res.users._gc_user_logs)
        - Batching with commits (similar to ir.autovacuum pattern)
        - Per-company processing with error isolation
        - Returns (done, remaining) tuple for re-queue support

        Returns:
            tuple: (total_deleted, has_more) - if has_more is True, method will be re-queued
        """
        batch_size = 1000
        max_batches_per_company = 20

        companies = self.env['res.company'].search([])
        total_deleted = 0
        has_more = False  # Track if any company hit max batch limit (for re-queue)

        _logger.info(
            "[VENDING EVENTS] Starting GC across %d companies",
            len(companies)
        )

        for company in companies:
            if company.event_lifetime is None:
                _logger.debug(
                    "[VENDING EVENTS] Company %s has no event_lifetime set, skipping",
                    company.name
                )
                continue

            try:
                cutoff_date = fields.Datetime.now() - timedelta(days=int(company.event_lifetime))
                company_deleted = 0
                batch_num = 0

                _logger.info(
                    "[VENDING EVENTS] Company %s (ID: %d) - deleting events older than %s (%d days)",
                    company.name,
                    company.id,
                    cutoff_date,
                    company.event_lifetime
                )

                while batch_num < max_batches_per_company:
                    batch_num += 1

                    try:
                        # Company comes from: event.controller_id -> controller.webstack_id -> webstack.company_id
                        self.env.cr.execute("""
                            DELETE FROM hr_rfid_vending_event
                            WHERE id IN (
                                SELECT e.id
                                FROM hr_rfid_vending_event e
                                INNER JOIN hr_rfid_ctrl c ON e.controller_id = c.id
                                INNER JOIN hr_rfid_webstack w ON c.webstack_id = w.id
                                WHERE e.event_time < %s
                                  AND w.company_id = %s
                                ORDER BY e.id
                                LIMIT %s
                            )
                        """, (cutoff_date, company.id, batch_size))

                        deleted_count = self.env.cr.rowcount

                        if deleted_count == 0:
                            break

                        # Commit after each batch (ir.autovacuum pattern)
                        self.env.cr.commit()

                        company_deleted += deleted_count
                        total_deleted += deleted_count

                        _logger.info(
                            "[VENDING EVENTS] Company %s batch %d: Deleted %d events (company total: %d)",
                            company.name,
                            batch_num,
                            deleted_count,
                            company_deleted
                        )

                        if deleted_count < batch_size:
                            break

                    except Exception as batch_error:
                        _logger.error(
                            "[VENDING EVENTS] Company %s batch %d error: %s",
                            company.name,
                            batch_num,
                            str(batch_error),
                            exc_info=True
                        )
                        self.env.cr.rollback()
                        break

                # Check if we hit max batches (may have more records to delete)
                if batch_num >= max_batches_per_company:
                    has_more = True
                    _logger.info(
                        "[VENDING EVENTS] Company %s hit max batch limit (%d), may have more events",
                        company.name,
                        max_batches_per_company
                    )

                if company_deleted > 0:
                    _logger.info(
                        "[VENDING EVENTS] Company %s completed: %d events deleted in %d batches",
                        company.name,
                        company_deleted,
                        batch_num
                    )

            except Exception as company_error:
                _logger.error(
                    "[VENDING EVENTS] Company %s fatal error: %s",
                    company.name,
                    str(company_error),
                    exc_info=True
                )
                self.env.cr.rollback()

        _logger.info(
            "[VENDING EVENTS] GC completed: %d total events deleted across %d companies (has_more=%s)",
            total_deleted,
            len(companies),
            has_more
        )

        # Return tuple for Odoo 19 autovacuum re-queue support
        # If has_more is True, this method will be re-queued for another run
        return total_deleted, has_more

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
    def search(self, *args, **kwargs):
        ret = super(VendingEvents, self).search(*args, **kwargs)

        if type(ret) == type(self):
            user = self.env.user
            if user:
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
