from datetime import timedelta
from odoo import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)


action_selection = [
        ('1', 'Card Granted'),
        ('2', 'Card Denied'),
        ('3', 'Card Denied T/S'),
        ('4', 'Card Denied APB'),
        ('5', 'Zone Arm Denied'),
        ('6', 'Card Granted (no entry)'),
        ('7', 'Card Granted Insert'),
        ('8', 'Card Denied Insert'),
        ('9', 'Card Ejected'),
        ('10', 'Zone Arm'),
        ('11', 'Zone Disarm'),
        ('12', 'Hotel Button Pressed'),
        ('15', 'Zone Disarm Denied'),
        ('64', 'Request Instructions'),
    ]

class HrRfidUserEvent(models.Model):
    _name = 'hr.rfid.event.user'
    _inherit = ['hr.rfid.event', 'mail.thread']
    _description = "RFID User Event"
    _rec_names_search = ['name', 'event_time', 'employee_id', 'contact_id', 'door_id', 'reader_id', 'event_action']
    _order = 'event_time desc'

    name = fields.Char(
        compute='_compute_user_ev_name',
        help="Auto-generated event description combining person name, action, and location"
    )

    ctrl_addr = fields.Integer(
        string='Controller ID',
        help="Unique identifier for the controller within its webstack network. Used for internal communication and device identification."
    )

    workcode = fields.Char(
        string='Workcode (Raw)',
        help="Raw workcode number received from the RFID reader. This appears when the workcode hasn't been configured in the system. Configure workcodes in Settings > RFID > Workcodes to see meaningful labels instead.",
        default='-',
        readonly=True,
    )

    workcode_id = fields.Many2one(
        comodel_name='hr.rfid.workcode',
        string='Workcode',
        help="Associated workcode defining the type of work activity (e.g., start work, break, stop work). Used for time tracking and attendance management.",
        readonly=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help="The employee who triggered this access event. Automatically populated from the card assignment.",
        ondelete='cascade',
    )

    contact_id = fields.Many2one(
        'res.partner',
        string='Contact',
        help="The external contact (visitor, contractor) who triggered this access event. Used for non-employee access tracking.",
        ondelete='cascade',
    )

    door_id = fields.Many2one(
        'hr.rfid.door',
        string='Door',
        help="The access door where this event occurred. Represents the physical entry/exit point.",
        ondelete='cascade',
    )

    reader_id = fields.Many2one(
        'hr.rfid.reader',
        string='Reader',
        help="The RFID card reader device that captured this event. Can be an entry or exit reader.",
        required=True,
        ondelete='cascade',
    )

    alarm_line_id = fields.Many2one(
        'hr.rfid.ctrl.alarm',
        string='Alarm line',
        help="The alarm input/output line involved in this event. Used for security zone arming/disarming operations.",
        ondelete='cascade',
    )

    card_id = fields.Many2one(
        'hr.rfid.card',
        string='Card',
        help="The RFID card used to trigger this event. Links to the card's configuration and access rights.",
        ondelete='set null',
    )

    card_number = fields.Char(
        related='card_id.number',
        string='Card Number',
        help="The unique identification number of the RFID card used in this event."
    )

    command_id = fields.Many2one(
        'hr.rfid.command',
        string='Response',
        help="System command sent in response to this event (e.g., open door, deny access). Used for audit trail.",
        readonly=True,
        ondelete='set null',
        index=True,
    )

    event_time = fields.Datetime(
        string='Timestamp',
        help="Exact date and time when the access event occurred at the reader. Used for attendance tracking and security logs.",
        required=True,
        index=True,
    )

    event_action = fields.Selection(
        selection=action_selection,
        string='Action',
        help="The type of access event:\n• Card Granted: Access allowed\n• Card Denied: Access blocked (invalid rights)\n• Card Denied T/S: Access blocked (outside time schedule)\n• Card Denied APB: Anti-passback violation\n• Zone Arm/Disarm: Security zone control\n• Card Insert/Eject: Card reader operations\n• Request Instructions: Cloud card verification",
        required=True,
    )

    action_string = fields.Char(
        compute='_compute_user_ev_action_str',
        help="Human-readable description of the event action for display purposes."
    )

    more_json = fields.Char(
        string='More info about event in JSON',
        help="Additional technical details about the event in JSON format. Used for debugging and advanced analysis."
    )

    @api.autovacuum
    def _gc_user_events_life(self):
        """
        Clean up old user event records per company based on event_lifetime setting.

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
        has_more = False  # Track if any company hit max batch limit

        _logger.info(
            "[USER EVENTS] Starting GC across %d companies",
            len(companies)
        )

        for company in companies:
            if company.event_lifetime is None:
                _logger.debug(
                    "[USER EVENTS] Company %s has no event_lifetime set, skipping",
                    company.name
                )
                continue

            try:
                cutoff_date = fields.Datetime.now() - timedelta(days=int(company.event_lifetime))
                company_deleted = 0
                batch_num = 0

                _logger.info(
                    "[USER EVENTS] Company %s (ID: %d) - deleting events older than %s (%d days)",
                    company.name,
                    company.id,
                    cutoff_date,
                    company.event_lifetime
                )

                while batch_num < max_batches_per_company:
                    batch_num += 1

                    try:
                        # Company comes from: event.reader_id -> reader.controller_id -> controller.webstack_id -> webstack.company_id
                        self._cr.execute("""
                            DELETE FROM hr_rfid_event_user
                            WHERE id IN (
                                SELECT e.id
                                FROM hr_rfid_event_user e
                                INNER JOIN hr_rfid_reader r ON e.reader_id = r.id
                                INNER JOIN hr_rfid_ctrl c ON r.controller_id = c.id
                                INNER JOIN hr_rfid_webstack w ON c.webstack_id = w.id
                                WHERE e.event_time < %s
                                  AND w.company_id = %s
                                ORDER BY e.id
                                LIMIT %s
                            )
                        """, (cutoff_date, company.id, batch_size))

                        deleted_count = self._cr.rowcount

                        if deleted_count == 0:
                            break

                        # Commit after each batch (ir.autovacuum pattern)
                        self._cr.commit()

                        company_deleted += deleted_count
                        total_deleted += deleted_count

                        _logger.info(
                            "[USER EVENTS] Company %s batch %d: Deleted %d events (company total: %d)",
                            company.name,
                            batch_num,
                            deleted_count,
                            company_deleted
                        )

                        if deleted_count < batch_size:
                            break

                    except Exception as batch_error:
                        _logger.error(
                            "[USER EVENTS] Company %s batch %d error: %s",
                            company.name,
                            batch_num,
                            str(batch_error),
                            exc_info=True
                        )
                        self._cr.rollback()
                        break

                # Check if we hit max batches (may have more records to delete)
                if batch_num >= max_batches_per_company:
                    has_more = True
                    _logger.info(
                        "[USER EVENTS] Company %s hit max batch limit (%d), may have more events",
                        company.name,
                        max_batches_per_company
                    )

                if company_deleted > 0:
                    _logger.info(
                        "[USER EVENTS] Company %s completed: %d events deleted in %d batches",
                        company.name,
                        company_deleted,
                        batch_num
                    )

            except Exception as company_error:
                _logger.error(
                    "[USER EVENTS] Company %s fatal error: %s",
                    company.name,
                    str(company_error),
                    exc_info=True
                )
                self._cr.rollback()

        _logger.info(
            "[USER EVENTS] GC completed: %d total events deleted across %d companies (has_more=%s)",
            total_deleted,
            len(companies),
            has_more
        )

        # Return tuple for Odoo 19 autovacuum re-queue support
        # If has_more is True, this method will be re-queued for another run
        return total_deleted, has_more

    @api.depends('employee_id.name', 'contact_id.name', 'door_id.name', 'event_action')
    def _compute_user_ev_name(self):
        for record in self:
            if record.employee_id:
                name = record.employee_id.name or ''
            elif record.contact_id:
                name = record.contact_id.name or ''
            else:
                name = record.door_id.name or ''
            name += ' - ' if name != '' else ''
            if record.event_action != '64':
                name += record.get_event_action_text()
            else:
                name += _('Request Instructions')
            if record.door_id:
                name += ' @ ' + record.door_id.name
            record.name = name

    @api.depends('event_action')
    def _compute_user_ev_action_str(self):
        for record in self:
            record.action_string = _('Access {}').format(self.action_selection[int(record.event_action) - 1][1])

    @api.model_create_multi
    def create(self, vals_list):
        """
        Create RFID events with duplicate prevention.
        
        This method includes duplicate detection to handle common scenarios:
        1. Multiple controllers sending the same event
        2. Network issues causing retransmissions
        3. Out-of-order event processing from distributed systems
        
        Duplicates are detected within a 5-second time window based on:
        - Same card
        - Same reader
        - Same action
        - Similar timestamp
        
        :param vals_list: List of dictionaries with event data
        :return: Created event records (excluding duplicates)
        """
        cleaned_vals_list = []
        
        for vals in vals_list:
            # Only check for duplicates if we have the minimum required fields
            if all(key in vals for key in ['card_id', 'reader_id', 'event_time', 'event_action']):
                # Parse event time if it's a string
                event_time = vals.get('event_time')
                if isinstance(event_time, str):
                    event_time = fields.Datetime.from_string(event_time)
                
                # Define a 5-second window for duplicate detection
                # This accounts for clock drift between controllers and network delays
                time_window_start = event_time - timedelta(seconds=5)
                time_window_end = event_time + timedelta(seconds=5)
                
                # Search for existing events with same characteristics
                existing_event = self.search([
                    ('card_id', '=', vals.get('card_id')),
                    ('reader_id', '=', vals.get('reader_id')),
                    ('event_action', '=', vals.get('event_action')),
                    ('event_time', '>=', time_window_start),
                    ('event_time', '<=', time_window_end),
                ], limit=1)
                
                if existing_event:
                    _logger.warning(
                        'Duplicate event detected for card_id=%s, reader_id=%s, action=%s at %s. '
                        'Existing event_id=%s at %s. Skipping creation.',
                        vals.get('card_id'), vals.get('reader_id'), vals.get('event_action'), 
                        event_time, existing_event.id, existing_event.event_time
                    )
                    continue
            
            cleaned_vals_list.append(vals)
        
        # Create only non-duplicate events
        if not cleaned_vals_list:
            # Return empty recordset if all events were duplicates
            _logger.info('All %d events were duplicates. No new events created.', len(vals_list))
            return self.browse()
            
        # Log if some events were filtered
        if len(cleaned_vals_list) < len(vals_list):
            _logger.info('Filtered %d duplicate events out of %d total events.',
                        len(vals_list) - len(cleaned_vals_list), len(vals_list))
            
        records = super(HrRfidUserEvent, self).create(cleaned_vals_list)

        # Post-processing for created events
        for rec in records:
            # Auto-populate employee/contact from card if not provided
            if not rec.employee_id and not rec.contact_id and rec.card_id:
                rec.employee_id = rec.card_id.employee_id
                rec.contact_id = rec.card_id.contact_id

            # Auto-populate door from reader if not provided
            if not rec.door_id and rec.reader_id:
                rec.door_id = rec.reader_id.door_id

            # Validate event has proper associations (except vending events)
            if not rec.employee_id and not rec.contact_id and rec.event_action != '47':
                _logger.error('User event without employee, contact and card. FATAL for event id=%s', rec.id)
            
            # Process only granted access events for zone tracking
            if rec.event_action != '1':  # '1' == Granted
                continue

            if not rec.employee_id and not rec.contact_id:
                continue

            # Update zone presence based on reader type
            zones = rec.door_id.zone_ids
            if zones:
                # Reader type is In (entrance)
                if rec.reader_id.reader_type == '0':
                    zones.with_context(from_event=True).person_entered(rec.employee_id or rec.contact_id, rec)
                # Reader type is Out (exit)
                else:
                    zones.with_context(from_event=True).person_left(rec.employee_id or rec.contact_id, rec)
                zones.process_event(rec)
                continue

            # Handle workcode-based events (start/stop/break)
            if rec.reader_id.mode != '03':
                zones.person_went_through(rec)
            else:
                wc = rec.workcode_id
                if len(wc) == 0:
                    continue
                    
                # Simple workcode actions
                if wc.user_action == 'start':
                    rec.door_id.zone_ids.person_entered(rec.employee_id, rec)
                elif wc.user_action == 'break':
                    rec.door_id.zone_ids.person_left(rec.employee_id, rec)
                elif wc.user_action == 'stop':
                    # Complex logic to determine zone state based on event history
                    stack = []
                    last_events = self.search([
                        ('event_time', '>=', fields.Datetime.now() - timedelta(hours=12)),
                        ('employee_id', '=', rec.employee_id.id),
                        ('id', '!=', rec.id),
                        ('workcode_id', '!=', None),
                    ], order='event_time')
                    
                    # Build action stack to determine current state
                    for event in last_events:
                        action = event.workcode_id.user_action
                        if action == 'stop':
                            if len(stack) > 0:
                                stack.pop()
                        else:
                            stack.append(action)

                    # Apply opposite of last action
                    if len(stack) > 0:
                        if stack[-1] == 'start':
                            rec.door_id.zone_ids.person_left(rec.employee_id, rec)
                        else:
                            rec.door_id.zone_ids.person_entered(rec.employee_id, rec)
        return records

    def zone_process_event(self):
        for rec in self:
            zones = rec.door_id.zone_ids
            if zones:
                zones.process_event(rec)

    def button_show_employee_events(self):
        self.ensure_one()
        return {
            'name': _('Events for {}').format(self.employee_id.name),
            'view_mode': 'list,form',
            'res_model': self._name,
            'domain': [('employee_id', '=', self.employee_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }

    def button_show_contact_events(self):
        self.ensure_one()
        return {
            'name': _('Events for {}').format(self.contact_id.name),
            'view_mode': 'list,form',
            'res_model': self._name,
            'domain': [('contact_id', '=', self.contact_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }

    def button_show_card_events(self):
        self.ensure_one()
        return {
            'name': _('Events for {}').format(self.card_id.name),
            'view_mode': 'list,form',
            'res_model': self._name,
            'domain': [('card_id', '=', self.card_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }

    def button_show_door_events(self):
        self.ensure_one()
        return {
            'name': _('Events on {}').format(self.door_id.name),
            'view_mode': 'list,form',
            'res_model': self._name,
            'domain': [('door_id', '=', self.door_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }

    def button_show_reader_events(self):
        self.ensure_one()
        return {
            'name': _('Events on {}').format(self.reader_id.name),
            'view_mode': 'list,form',
            'res_model': self._name,
            'domain': [('reader_id', '=', self.reader_id.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }

    @api.model
    def last_event(self, door_ids=None, partner_id=None, employee_id=None, event_action=None, domain=None, limit=1):
        """ Get last event for user

            """
        if domain is None:
            domain = []
        if door_ids is not None:
            domain.append(
                ('door_id', 'in', door_ids.mapped('id'))
            )
        if partner_id is not None:
            domain.append(
                ('contact_id', '=', partner_id.id)
            )
        if employee_id is not None:
            domain.append(
                ('employee_id', '=', employee_id.id)
            )
        if event_action is not None:
            domain.append(
                ('event_action', '=', str(event_action))
            )
        return self.search(domain, limit=limit)
