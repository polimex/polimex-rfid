import json
from datetime import timedelta

from odoo import fields, models, api, exceptions, _

import logging
_logger = logging.getLogger(__name__)

# A repeating identical system event within this many seconds of the existing
# row's LAST occurrence is the same ongoing incident (grouped via occurrences);
# after a longer quiet gap the repeat is a NEW incident and gets its own row,
# so e.g. a forced door today never disappears into last week's record.
SYS_EV_DEDUP_WINDOW_SECONDS = 300

action_selection = [
        ('0', 'Unknown Event?'),
        ('1', 'DuressOK'),
        ('2', 'DuressError'),
        ('3', 'R1 Card OK'),  # User Event
        ('4', 'R1 Card Error'),  # User Event
        ('5', 'R1 T/S Error'),  # User Event
        ('6', 'R1 APB Error'),  # User Event
        ('7', 'R2 Card OK'),  # User Event
        ('8', 'R2 Card Error'),  # User Event
        ('9', 'R2 T/S Error'),  # User Event
        ('10', 'R2 APB Error'),  # User Event
        ('11', 'R3 Card OK'),  # User Event
        ('12', 'R3 Card Error'),  # User Event
        ('13', 'R3 T/S Error'),  # User Event
        ('14', 'R3 APB Error'),  # User Event
        ('15', 'R4 Card Ok'),  # User Event
        ('16', 'R4 Card Error'),  # User Event
        ('17', 'R4 T/S Error'),  # User Event
        ('18', 'R4 APB Error'),  # User Event
        ('19', 'Fire/Emergency'),
        ('20', 'Siren ON/OFF'),
        ('21', 'Exit button'),
        ('22', 'OpenDoor2 from In2'),  # deprecated
        ('23', 'OpenDoor3 from In3'),  # deprecated
        ('24', 'OpenDoor4 from In4'),  # deprecated
        ('25', 'Door Overtime'),
        ('26', 'Forced Door Open'),
        ('27', 'DELAY ZONE ON (if out) Z4,Z3,Z2,Z1'),
        ('28', 'DELAY ZONE OFF (if in) Z4,Z3,Z2,Z1'),
        ('29', 'External Control'),
        ('30', 'Power On event'),
        ('31', 'Open/Close Door From PC'),
        ('32', 'reserved'),
        ('33', 'Zone Arm/Disarm Denied'),  # User Event
        ('34', 'Zone Status'),
        ('35', 'Zone Arm/Disarm'),  # User Event
        ('36', 'Inserted Card'),  # User Event
        ('37', 'Ejected Card'),  # User Event
        ('38', 'Hotel Button Pressed'),  # User Event
        ('39', 'Unknown Plate'),  # System Event
        ('45', '1-W ERROR (wiring problems)'),
        ('47', 'Vending Purchase Complete'),
        ('48', 'Vending Error1'),
        ('49', 'Vending Error2'),
        ('50', 'Vending collect to card'),
        ('51', 'Temperature High'),
        ('52', 'Temperature Normal'),
        ('53', 'Temperature Low'),
        ('54', 'Temperature Error'),
        ('64', 'Cloud Card Request'),  # User Event
        ('99', 'System Event'),
    ]

class HrRfidSystemEvent(models.Model):
    _name = 'hr.rfid.event.system'
    _inherit = ['hr.rfid.event', 'mail.thread']
    _description = 'RFID System Event'
    _order = 'timestamp desc'

    name = fields.Char(
        compute='_compute_sys_ev_name',
        help="Auto-generated system event description combining event type and location"
    )

    webstack_id = fields.Many2one(
        'hr.rfid.webstack',
        string='Module',
        help="The RFID webstack module (network interface) where this system event occurred. Webstacks manage communication between controllers and the server.",
        ondelete='cascade',
    )

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        string='Controller',
        help="The RFID controller device that generated this system event. Controllers manage doors, readers, and alarms.",
        ondelete='cascade',
    )

    door_id = fields.Many2one(
        'hr.rfid.door',
        string='Door',
        help="The specific door involved in this system event (e.g., forced open, overtime). May be empty for controller-wide events.",
        ondelete='cascade',
    )

    alarm_line_id = fields.Many2one(
        'hr.rfid.ctrl.alarm',
        string='Alarm line',
        help="The alarm input/output line that triggered this event. Used for security sensors, fire alarms, and emergency systems.",
        ondelete='cascade',
    )

    siren = fields.Boolean(
        help="Indicates whether the siren/alarm is currently active. True = Siren ON (alarm condition), False = Siren OFF (normal state).",
        default=False
    )

    timestamp = fields.Datetime(
        string='Timestamp',
        help="Exact date and time when this system event was detected. Critical for security audits and troubleshooting.",
        required=True,
        index=True,
    )

    occurrences = fields.Integer(
        string='Occurrences',
        help="Count of how many times this identical event has occurred. System groups repeated events to reduce log clutter.",
        default=1,
    )

    last_occurrence = fields.Datetime(
        string='Last occurrence',
        help="Date and time of the most recent occurrence when the same event happened multiple times."
    )

    event_nums = list(map(lambda a: a[0], action_selection))

    event_action = fields.Selection(
        selection=action_selection,
        string='Event Type',
        default='99',
        help="Type of system event:\n• Power On: Controller started\n• Door Overtime: Door held open too long\n• Forced Door: Door opened without authorization\n• Fire/Emergency: Emergency alarm triggered\n• Exit Button: Manual door release\n• Temperature: Environmental monitoring\n• Wiring Error: Hardware malfunction\n• Unknown Card/Plate: Unregistered access attempt"
    )

    error_description = fields.Char(
        string='Description',
        help="Detailed explanation of the error or event condition. Provides context for troubleshooting system issues.",
    )

    card_number = fields.Char(
        string='Card number from this event',
        readonly=True,
        help="RFID card number that triggered this system event. Only populated for card-related errors (unknown card, etc.)."
    )

    input_js = fields.Char(
        string='Input JSON',
        help="Raw JSON data received from the controller. Contains technical details for debugging. Only stored when system debugging is enabled."
    )

    is_card_event = fields.Boolean(
        compute='_compute_is_card_event',
        help="Indicates if this system event is related to an unknown/denied card, allowing card registration from the event."
    )

    @api.depends('event_action')
    def _compute_is_card_event(self):
        for e in self:
            e.is_card_event = e.event_action in ['4', '8', '12', '16', '64']

    @api.autovacuum
    def _gc_events_life(self):
        """
        Clean up old system event records per company based on event_lifetime setting.

        Follows Odoo core patterns:
        - Direct SQL for performance (similar to res.users._gc_user_logs)
        - Batching with commits (similar to ir.autovacuum pattern)
        - Per-company processing with error isolation
        """
        batch_size = 1000
        max_batches_per_company = 20

        companies = self.env['res.company'].search([])
        total_deleted = 0

        _logger.info(
            "[SYSTEM EVENTS] Starting GC across %d companies",
            len(companies)
        )

        for company in companies:
            if company.event_lifetime is None:
                _logger.debug(
                    "[SYSTEM EVENTS] Company %s has no event_lifetime set, skipping",
                    company.name
                )
                continue

            try:
                cutoff_date = fields.Datetime.now() - timedelta(days=int(company.event_lifetime))
                company_deleted = 0
                batch_num = 0

                _logger.info(
                    "[SYSTEM EVENTS] Company %s (ID: %d) - deleting events older than %s (%d days)",
                    company.name,
                    company.id,
                    cutoff_date,
                    company.event_lifetime
                )

                while batch_num < max_batches_per_company:
                    batch_num += 1

                    try:
                        # Company comes from: event.webstack_id -> webstack.company_id
                        self._cr.execute("""
                            DELETE FROM hr_rfid_event_system
                            WHERE id IN (
                                SELECT e.id
                                FROM hr_rfid_event_system e
                                INNER JOIN hr_rfid_webstack w ON e.webstack_id = w.id
                                WHERE e.timestamp < %s
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
                            "[SYSTEM EVENTS] Company %s batch %d: Deleted %d events (company total: %d)",
                            company.name,
                            batch_num,
                            deleted_count,
                            company_deleted
                        )

                        if deleted_count < batch_size:
                            break

                    except Exception as batch_error:
                        _logger.error(
                            "[SYSTEM EVENTS] Company %s batch %d error: %s",
                            company.name,
                            batch_num,
                            str(batch_error),
                            exc_info=True
                        )
                        self._cr.rollback()
                        break

                if company_deleted > 0:
                    _logger.info(
                        "[SYSTEM EVENTS] Company %s completed: %d events deleted in %d batches",
                        company.name,
                        company_deleted,
                        batch_num
                    )

            except Exception as company_error:
                _logger.error(
                    "[SYSTEM EVENTS] Company %s fatal error: %s",
                    company.name,
                    str(company_error),
                    exc_info=True
                )
                self._cr.rollback()

        _logger.info(
            "[SYSTEM EVENTS] GC completed: %d total events deleted across %d companies",
            total_deleted,
            len(companies)
        )

        return True

    @api.depends('webstack_id.name', 'controller_id.name', 'timestamp')
    def _compute_sys_ev_name(self):
        for record in self:
            key_val_dict = dict(record._fields['event_action'].selection)
            record.name = key_val_dict[record.event_action] + ' on ' + str(record.webstack_id.name) + '/' + str(
                record.controller_id.name)
            #               ' at ' + str(record.timestamp)

    def _check_save_comms(self, vals):
        save_comms = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.save_webstack_communications') in [
            'true', 'True']
        if not save_comms:
            if 'input_js' not in vals:
                return

            if 'error_description' in vals and vals['error_description'] == 'Could not find the card':
                try:
                    js = json.loads(vals['input_js'])
                    vals['input_js'] = js['event']['card']
                finally:
                    return
            else:
                vals.pop('input_js')

    def _check_duplicate_sys_ev(self, vals):
        """Group a repeating identical system event into its existing row.

        "Identical" = same module, controller, door, alarm line, action,
        description and raw payload. A repeat within
        SYS_EV_DEDUP_WINDOW_SECONDS of the row's last occurrence is the same
        ongoing incident: bump ``occurrences`` and slide ``last_occurrence``
        (a door held open pings every few seconds -> one row). A repeat after
        a longer quiet gap is a NEW incident and must get its own row.

        Note: the previous implementation compared the new door/alarm line
        against the candidate's CONTROLLER id and matched only the single
        newest event of the module, with no time limit - door-level events
        (forced/held door) were never grouped, and fixing the field comparison
        alone would have let a new break-in silently vanish into an old row.
        """
        if 'webstack_id' not in vals or not vals.get('timestamp'):
            return False
        window_start = fields.Datetime.to_datetime(vals['timestamp']) \
            - timedelta(seconds=SYS_EV_DEDUP_WINDOW_SECONDS)
        dupe = self.env['hr.rfid.event.system'].search([
            ('webstack_id', '=', vals['webstack_id']),
            ('controller_id', '=', vals.get('controller_id', False)),
            ('door_id', '=', vals.get('door_id', False)),
            ('alarm_line_id', '=', vals.get('alarm_line_id', False)),
            ('event_action', '=', vals.get('event_action', False)),
            ('error_description', '=', vals.get('error_description', False)),
            ('input_js', '=', vals.get('input_js', False)),
            ('last_occurrence', '>=', window_start),
        ], limit=1, order='last_occurrence desc')

        if not dupe:
            return False

        dupe.write({
            'last_occurrence': vals['timestamp'],
            'occurrences': dupe.occurrences + 1,
        })
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = self.env['hr.rfid.event.system']

        for vals in vals_list:
            if 'event_action' in vals and vals['event_action'] not in self.event_nums:
                vals['event_action'] = '0'

            self._check_save_comms(vals)

            if self._check_duplicate_sys_ev(vals):
                continue

            if 'last_occurrence' not in vals:
                vals['last_occurrence'] = vals['timestamp']
            record = super(HrRfidSystemEvent, self).create([vals])
            if record.door_id and record.door_id.zone_ids:
                record.door_id.zone_ids.process_event(record)
            elif not record.door_id and record.controller_id and record.controller_id.door_ids:
                zone_ids = record.controller_id.door_ids and record.controller_id.door_ids.zone_ids
                zone_ids.process_event(record)
            records += record

            if 'siren' in vals and 'event_action' in vals and vals.get('event_action') == '20':
                for e in records.with_context(no_output=True):
                    e.controller_id.siren_state = vals.get('siren')

        return records

    def zone_process_event(self):
        for rec in self:
            zones = rec.door_id.zone_ids if rec.door_id else None
            if zones:
                zones.process_event(rec)
            elif not rec.door_id and rec.controller_id and rec.controller_id.door_ids:
                zone_ids = rec.controller_id.door_ids.zone_ids
                zone_ids.process_event(rec)

    def write(self, vals):
        self._check_save_comms(vals)
        return super(HrRfidSystemEvent, self).write(vals)


class HrRfidSystemEventWizard(models.TransientModel):
    _name = 'hr.rfid.event.sys.wiz'
    _description = 'Add card to employee/contact'

    def _default_sys_ev(self):
        return self.env['hr.rfid.event.system'].browse(self._context.get('active_ids'))

    def _default_card_number(self):
        sys_ev = self._default_sys_ev()

        if type(sys_ev.card_number) != type(''):
            raise exceptions.ValidationError(_('System event does not have a card number in it'))

        if sys_ev.card_number:
            return sys_ev.card_number
        try:
            js = json.loads(sys_ev.input_js)
            card_number = js['event']['card']
            return card_number
        except :
            raise exceptions.ValidationError(_('System event does not have a card number in it'))

    sys_ev_id = fields.Many2one(
        'hr.rfid.event.system',
        string='System event',
        required=True,
        default=_default_sys_ev,
        ondelete='cascade',
        help="The system event containing the unknown card information to be registered."
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Card owner (employee)',
        help="Select the employee who will own this card. Choose either an employee OR a contact, not both."
    )

    contact_id = fields.Many2one(
        'res.partner',
        string='Card owner (contact)',
        help="Select the external contact (visitor/contractor) who will own this card. Choose either a contact OR an employee, not both."
    )

    card_number = fields.Char(
        string='Card Number',
        default=_default_card_number,
        help="The RFID card number extracted from the system event. This will be registered in the system."
    )

    card_type = fields.Many2one(
        'hr.rfid.card.type',
        string='Card type',
        help="Select the card technology type (e.g., Mifare, EM, HID). Only doors configured for this card type will accept it.",
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_card_type_def').id,
    )

    activate_on = fields.Datetime(
        string='Activate on',
        help="Date and time when the card becomes active. Set to a future date for scheduled activation.",
        default=lambda self: fields.Datetime.now(),
    )

    deactivate_on = fields.Datetime(
        string='Deactivate on',
        help="Optional expiration date for the card. Leave empty for permanent cards. Useful for temporary visitors or contractors.",
    )

    active = fields.Boolean(
        string='Active',
        help="Enable this card immediately. Uncheck to create an inactive card that can be activated later.",
        default=True,
    )

    cloud_card = fields.Boolean(
        string='Cloud Card',
        help="Cloud cards are managed centrally by the server. They work with online controllers but not with standalone/external database controllers.",
        default=True,
        required=True,
    )

    def add_card(self):
        self.ensure_one()

        if len(self.contact_id) == len(self.employee_id):
            raise exceptions.ValidationError(
                'Card cannot have both or neither a contact owner and an employee owner.'
            )

        card_env = self.env['hr.rfid.card']
        new_card = {
            'number': self.card_number,
            'card_type': self.card_type.id,
            'activate_on': self.activate_on,
            'deactivate_on': self.deactivate_on,
            'active': self.active,
            'cloud_card': self.cloud_card,
        }
        if len(self.contact_id) > 0:
            new_card['contact_id'] = self.contact_id.id
        else:
            new_card['employee_id'] = self.employee_id.id
        card_env.create(new_card)
