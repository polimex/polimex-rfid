from odoo import fields, models, api, exceptions, _, SUPERUSER_ID
from odoo.addons.hr_rfid.controllers import polimex

import logging

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HrRfidControllerOutputTS(models.Model):
    _name = 'hr.rfid.ctrl.output.ts'
    _description = 'Output TS for Controllers'
    _controller_output_unique = models.Constraint(
        'UNIQUE(controller_id, output_number)',
        'Output must be unique!'
    )
    output_number = fields.Integer(
        string="Output number",
        default=1,
        required=True,
        help="Physical output number on the controller (1, 2, 3, etc.). Each output can control different devices like door locks, alarms, or lights."
    )
    time_schedule_id = fields.Many2one(
        comodel_name='hr.rfid.time.schedule',
        required=True,
        help="Time schedule that controls when this output will be active. The output will automatically turn on/off based on the schedule."
    )
    controller_id = fields.Many2one(
        comodel_name='hr.rfid.ctrl',
        required=True,
        ondelete='cascade',
        help="Controller that owns this output-to-time-schedule binding. Cascade on delete — the row disappears with its controller.",
    )
    output_count = fields.Integer(
        related='controller_id.outputs',
        help="Number of physical outputs reported by the controller. Used to validate that output_number stays in range.",
    )
    max_ts = fields.Integer(
        related='controller_id.time_schedules',
        help="Highest time-schedule slot the controller supports. Used to validate that the assigned schedule fits the controller's capacity.",
    )
    time_schedule_number = fields.Integer(
        related='time_schedule_id.number',
        help="Numeric slot of the linked time schedule, shown for quick reference in lists.",
    )

    @api.constrains('output_number', 'time_schedule_id')
    def _constrains_output_number_ts(self):
        for rel in self:
            if rel.output_number < 0 or rel.output_number > rel.output_count:
                raise exceptions.ValidationError(
                    _('Output number %(out)d not in range from 1 to %(to)d', out=rel.output_number,
                      to=rel.output_count))
            if rel.time_schedule_id.number < 1 or rel.output_number > rel.max_ts:
                raise exceptions.ValidationError(
                    _('Time Schedule number  %(ts)d not in range from 1 to %(to)d', ts=rel.time_schedule_id.number,
                      to=rel.max_ts))

    def name_get(self):
        def get_names(rel):
            return _('Output %d working with TS %s') % (rel.output_number, rel.time_schedule_id.name)

        return [(rel.id, get_names(rel)) for rel in self]


class HrRfidCtrlInputMask(models.Model):
    _name = 'hr.rfid.ctrl.input.mask'
    _description = 'Input Mask for Controllers'
    _order = 'i_number'
    _controller_input_mask_unique = models.Constraint(
        'UNIQUE(controller_id, i_number)',
        'Input must be unique!'
    )

    i_number = fields.Integer(
        string='Number', 
        required=True, 
        readonly=True,
        help="Physical input number on the controller. Each input can monitor different sensors or switches."
    )
    i_mask = fields.Boolean(
        string='Mask (NC/NO)', 
        required=True,
        help="Input type configuration: Checked = Normally Closed (NC), Unchecked = Normally Open (NO). NC means the circuit is closed when inactive, NO means the circuit is open when inactive."
    )
    controller_id = fields.Many2one(
        comodel_name='hr.rfid.ctrl',
        required=True,
        ondelete='cascade',
        help="Controller that owns this input-mask row. Cascade on delete — the row disappears with its controller.",
    )
    input_count = fields.Integer(
        related='controller_id.inputs',
        help="Total number of physical inputs on the controller — used to display only the masks the hardware actually has.",
    )

    @api.model
    def _generate_input_masks(self, ctrl_id, masks):
        im_ids = self.search([('controller_id', '=', ctrl_id.id)])
        if im_ids:
            im_ids._update_input_masks(masks)
        else:
            self.sudo().create([{
                'i_number': i + 1,
                'controller_id': ctrl_id.id,
                'i_mask': masks & (1 << i) != 0} for i in range(ctrl_id.inputs)])

    def _update_input_masks(self, masks):
        for im in self:
            if masks:
                im.i_mask = masks & (1 << im.i_number - 1) != 0

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('from_controller', False):
            for i in self:
                i.controller_id.write_input_masks_cmd()

class HrRfidController(models.Model):
    _name = 'hr.rfid.ctrl'
    _inherit = ['mail.thread', 'balloon.mixin']
    _description = 'Controller'
    _rfid_controller_unique = models.Constraint(
        'UNIQUE(serial_number, hw_version)',
        'Serial numbers must be unique!'
    )
    _order = 'webstack_id, ctrl_id'

    name = fields.Char(
        string='Name',
        help='A descriptive name for this controller (e.g., "Main Entrance Controller", "2nd Floor Access Control"). This helps identify the controller quickly in lists and reports.',
        required=True,
        index=True,
        tracking=True,
    )

    ctrl_id = fields.Integer(
        string='ID behind IP Module',
        help='Unique identifier for this controller when multiple controllers are connected to the same IP module. Usually 0-7 for RS485 connections. This allows up to 8 controllers per IP module.',
        index=True,
    )

    hw_version = fields.Selection(
        selection=polimex.HW_TYPES,
        string='Hardware Type',
        help='Hardware model of the controller. Different models support different features: door access control, alarm systems, relay control, temperature monitoring, turnstiles, or vending machines.',
    )

    serial_number = fields.Char(
        string='Serial',
        help='Factory-assigned unique serial number. This 4-character code is used for hardware identification and warranty tracking.',
        size=4,
        tracking=True,
    )

    sw_version = fields.Char(
        string='Version',
        help='Firmware version running on the controller. Format: X.YZ where X is major version, Y is minor version, Z is patch. Higher versions may support additional features.',
        size=3,
        tracking=True,
    )

    inputs = fields.Integer(
        string='Inputs',
        help='Number of physical input connections available on this controller. Inputs are used to connect sensors, buttons, switches, or alarm detectors.',
    )
    inputs_mask = fields.Integer(
        help='Binary mask that defines the type of each input (NC/NO). Each bit represents one input: 1 = Normally Closed, 0 = Normally Open.',
    )
    input_mask_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.input.mask',
        inverse_name='controller_id',
        string='Input Masks',
        help="Per-input NC/NO configuration. One row per physical input. Toggling a row sends a write_input_masks command to the controller.",
    )
    input_states = fields.Integer(
        help='Current state of all inputs as a binary value. Each bit represents one input: 1 = Active/Triggered, 0 = Inactive. Used to monitor real-time sensor states.',
    )
    outputs = fields.Integer(
        string='Outputs',
        help='Number of physical output connections (relays) available on this controller. Outputs control devices like door locks, alarms, lights, or other equipment.',
    )
    output_states = fields.Integer(
        help='Current state of all outputs as a binary value. Each bit represents one output: 1 = On/Active, 0 = Off/Inactive. Shows which devices are currently activated.',
    )
    output_ts_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.output.ts',
        inverse_name='controller_id',
        string="Output's Time schedules",
        help="Control the Output's Time schedules of the controller.\n"
             "You can add PLC-like logic for all controller's outputs.\n"
             "Choose the output number and the Time Schedule code.\n"
             "The relay will open working hours and closed in non-working hours",
    )
    relay_output_mask = fields.Boolean(
        help='Relay output configuration for relay controllers. When enabled, relay outputs operate in Normally Closed (NC) mode - they are closed when inactive. When disabled, they operate in Normally Open (NO) mode - they are open when inactive.',
        default=False,
    )
    readers = fields.Integer(
        string='Readers',
        help='Number of RFID card readers that can be connected to this controller. Each reader can scan access cards at different locations (e.g., entry/exit points).'
    )

    time_schedules = fields.Integer(
        string='Time Schedules',
        help='Maximum number of time schedules this controller can store. Time schedules define when access is allowed, when outputs activate, or when certain rules apply.',
    )

    io_table_lines = fields.Integer(
        string='IO Table Lines',
        help='Number of programmable logic lines in the I/O table. Each line can contain rules that link inputs to outputs, creating automated responses (e.g., "if door sensor triggered, activate alarm").',
    )

    alarm_lines = fields.Integer(
        string='Alarm Lines',
        help='Number of dedicated alarm zone inputs on this controller. Each zone can monitor different areas or sensors for security purposes.',
        default=0
    )

    alarm_line_states = fields.Char(
        string='Alarm Line States',
        help='Real-time status of each alarm zone as hexadecimal values. Shows if zones are armed/disarmed, triggered, normal, or in fault condition.',
    )

    alarm_lines_setup = fields.Char(
        help='Configuration data for alarm zones in hexadecimal format. Defines which zones are enabled, their AC/DC monitoring settings, and sensor event reporting.',
        default='000000'
    )

    alarm_sensor_events = fields.Boolean(
        string='Alarm Sensor Events',
        help='When enabled, the controller reports all sensor state changes as events, even when the alarm is disarmed. Useful for monitoring sensor activity for maintenance or security analysis.',
        default=False,
        tracking=True,
    )

    # ignore_alarm_line_states_event_on_disarm = fields.Boolean(
    #     string='Ignore Alarm Line States Event on Disarm',
    #     help='If the controller uses the "Alarm Sensor Events" feature, the system will not store event on every alarm line state change when the line is disarmed.',
    #
    siren_state = fields.Boolean(
        help='Current state of the alarm siren. True = Siren is active/sounding, False = Siren is silent. Automatically controlled by alarm triggers.',
        compute='_compute_siren_state',
        inverse='_set_siren_state',
        tracking=True
    )

    emergency_group_id = fields.Many2one(
        comodel_name='hr.rfid.ctrl.emergency.group',
        tracking=True,
        help='Emergency group this controller belongs to. When any controller in the group enters emergency mode, all controllers in the group will also activate emergency mode.'
    )

    emergency_state = fields.Selection([
        ('off', 'No Emergency'),
        ('soft', 'Group Emergency'),
        ('hard', 'Hardware Emergency'),
    ], compute='_compute_emergency_state',
        tracking=True,
        inverse='_inverse_emergency_state',
        help='Emergency mode status:\n- No Emergency: Normal operation\n- Group Emergency: Activated by software/group trigger, all doors unlock\n- Hardware Emergency: Activated by physical emergency button, cannot be overridden remotely')

    mode = fields.Integer(
        string='Controller Mode',
        help='Operating mode that defines how many doors/devices this controller manages and how they are configured. Different hardware models support different modes.',
        tracking=True
    )

    mode_selection = fields.Selection(
        string='Controller mode',
        selection=[('0', 'Unknown'), ('1', 'One door'), ('2', 'Two doors')],
        required=True,
        compute='_compute_controller_mode',
        inverse='_inverse_controller_mode',
        help='Door control mode for standard access controllers. One door mode uses all resources for a single door, two door mode splits resources between two doors.'
    )

    mode_selection_4 = fields.Selection(
        string='Doors mode',
        selection=[('0', 'Unknown'), ('2', 'Two doors'), ('3', 'Three doors'), ('4', 'Four doors')],
        required=True,
        compute='_compute_controller_mode',
        inverse='_inverse_controller_mode_4',
        help='Door control mode for advanced access controllers that support up to 4 doors. Each door can have independent access rules and schedules.'
    )

    mode_selection_31 = fields.Selection(
        string='Relays mode',
        selection=[('0', 'Unknown'), ('1', '1 x 32 Relays'), ('2', '2 x 16 Relays'), ('3', '1 x 512 Relays')],
        readonly=False,
        required=True,
        compute='_compute_controller_mode_31',
        inverse='_inverse_controller_mode_31',
        help='Relay configuration mode:\n- 1 x 32: Single bank of 32 relays\n- 2 x 16: Two independent banks of 16 relays each\n- 1 x 512: Extended mode supporting up to 512 relay addresses'
    )

    external_db = fields.Boolean(
        string='External DB',
        help='Enable external database mode. When active, the controller can receive card data from an external system instead of storing cards in its internal memory. Useful for large installations.',
        default=False,
        tracking=True
    )

    relay_time_factor = fields.Selection(
        [('0', '1 second'), ('1', '0.1 seconds')],
        string='Relay Time Factor',
        default='0',
        tracking=True,
        help='Time unit for relay activation duration. When set to "1 second", relay timers count in seconds. When set to "0.1 seconds", timers count in deciseconds for more precise control.'
    )

    dual_person_mode = fields.Boolean(
        string='Dual Person Mode',
        default=False,
        tracking=True,
        help='Security feature requiring two authorized persons to badge within a time window to grant access. Commonly used for high-security areas like server rooms or vaults.'
    )

    max_cards_count = fields.Integer(
        string='Maximum Cards',
        help='Maximum number of access cards this controller can store in its internal memory. Depends on the controller model and memory capacity. External DB mode bypasses this limit.',
    )

    cards_count = fields.Integer(
        help='Current number of access cards stored in the controller\'s memory. When this approaches the maximum, consider enabling external DB mode or removing unused cards.',
        default=0
    )

    max_events_count = fields.Integer(
        string='Maximum Events',
        help='Maximum number of access events (card swipes, door openings, alarms) the controller can store before overwriting old events. Events should be regularly downloaded to prevent data loss.',
    )

    hotel_readers = fields.Integer(
        string='Hotel readers',
        help='Number of hotel-style card readers connected. These readers support card insertion detection and guest service buttons (e.g., "Do Not Disturb", "Make Up Room").',
        default=0
    )
    hotel_readers_card_presence = fields.Integer(
        string='Hotel readers card presence',
        help='Binary representation of which hotel readers currently have a card inserted. Each bit represents one reader: 1 = card present, 0 = no card. Used for energy saving systems.',
        default=0
    )
    hotel_readers_buttons_pressed = fields.Integer(
        string='Hotel readers buttons pressed',
        help='Binary representation of which service buttons are currently pressed on hotel readers. Each bit represents a button state. Typically used for guest service requests.',
        default=0
    )

    # Warning, don't change this field manually unless you know how to create a
    # command to change the io table for the controller or are looking to avoid exactly that.
    # You can use the change_io_table method to automatically create a command
    io_table = fields.Char(
        string='Input/Output Table',
        help='Programmable logic table in hexadecimal format. Defines automated responses linking inputs to outputs (e.g., "when input 1 triggers, activate output 3 for 5 seconds"). Advanced feature for custom automation.',
    )

    webstack_id = fields.Many2one(
        'hr.rfid.webstack',
        string='Module',
        help='IP communication module (webstack) this controller is connected to. The webstack provides network connectivity and manages communication between the server and controllers.',
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    door_ids = fields.One2many(
        comodel_name='hr.rfid.door',
        inverse_name='controller_id',
        string='Controlled Doors',
        help='Doors managed by this controller. Each door has its own reader, lock, and access rules. The number of doors depends on the controller mode.'
    )

    reader_ids = fields.One2many(
        comodel_name='hr.rfid.reader',
        inverse_name='controller_id',
        string='Controlled Readers',
        help='RFID card readers connected to this controller. Readers scan access cards and send the data to the controller for access decisions. Usually 1-2 readers per door (entry/exit).',
    )

    alarm_line_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.alarm',
        inverse_name='controller_id',
        string='Controlled Alarm Lines',
        help='Security alarm zones monitored by this controller. Each line can connect to different sensors (motion, door contact, glass break, etc.) and trigger appropriate responses.',
    )
    read_b3_cmd = fields.Boolean(
        string='Read Controller Status',
        default=False,
        index=True,
        help='When enabled, the system will periodically read the controller status (inputs, outputs, alarms). Useful for real-time monitoring but increases network traffic.'
    )
    sensor_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.th',
        inverse_name='controller_id',
        string='Sensors',
        help='Temperature and humidity sensors connected to this controller. Used for environmental monitoring in server rooms, warehouses, or other climate-sensitive areas.',
    )

    temperature = fields.Float(
        string='Temperature',
        default=0,
        help='Current temperature reading from the controller\'s internal or primary external sensor in Celsius. Updated when status is read.'
    )

    humidity = fields.Float(
        string='Humidity',
        default=0,
        help='Current relative humidity percentage from the controller\'s internal or primary external sensor. Updated when status is read.'
    )

    # Temperature Controller
    event_interval = fields.Integer(
        help="Interval in minutes for automatic temperature/humidity event reporting. Set to 0 to disable automatic reporting. Valid range: 0-99 minutes. The controller will send readings at this interval.",
        compute="_compute_event_interval",
        inverse="_inverse_event_interval"
    )

    def _inverse_event_interval(self):
        for c in self.filtered(lambda ctrl: ctrl.hw_version == '22'):
            io_line = c._get_io_line(1)
            io_line[4] = c.event_interval
            c._set_io_line(1, io_line)

    @api.depends('io_table')
    def _compute_event_interval(self):
        for c in self.filtered(lambda ctrl: ctrl.hw_version == '22'):
            io_line = c._get_io_line(1)
            c.event_interval = len(io_line) > 0 and io_line[4] or 0

    @api.constrains('event_interval')
    def _check_value(self):
        if self.event_interval > 99 or self.event_interval < 0:
            raise ValidationError(_('Valid interval range is 0-99 min.'))

    high_temperature = fields.Float(
        help="Upper temperature threshold in Celsius. When exceeded, the controller triggers a high temperature alarm event. Valid range: -55 to 125°C. Use for overheating protection."
    )

    @api.constrains('high_temperature')
    def _check_value(self):
        if self.high_temperature > 125 or self.high_temperature < -55:
            raise ValidationError(_('Valid High Temperature range is -55 .. 125 ℃'))

    low_temperature = fields.Float(
        help="Lower temperature threshold in Celsius. When temperature drops below this value, the controller triggers a low temperature alarm event. Valid range: -55 to 125°C. Use for freeze protection."
    )

    @api.constrains('low_temperature')
    def _check_value(self):
        if self.low_temperature > 125 or self.low_temperature < -55:
            raise ValidationError(_('Valid Low Temperature range is -55 .. 125 ℃'))

    hysteresis = fields.Float(
        help="Temperature hysteresis (dead band) in Celsius to prevent alarm flickering. The temperature must change by this amount before the alarm state changes. Valid range: 0.5 to 9°C. Example: If high temp is 30°C with 2°C hysteresis, alarm triggers at 30°C but clears only when temp drops below 28°C."
    )

    @api.constrains('hysteresis')
    def _check_value(self):
        if self.low_temperature > 9 or self.low_temperature < 0.5:
            raise ValidationError(_('Valid Low Temperature range is 0.5 .. 9 ℃'))

    system_voltage = fields.Float(
        string='System Voltage',
        default=0,
        help='Current voltage level of the controller\'s internal power supply in VDC. Normal range is typically 11-14V for 12V systems. Low voltage may indicate power supply issues.'
    )

    input_voltage = fields.Float(
        string='Input Voltage',
        default=0,
        help='Voltage level supplied to the controller from the external power source in VDC. Should match the controller\'s specifications (usually 12-24V). Monitor for power stability.'
    )

    last_f0_read = fields.Datetime(
        string='Last System Information Update',
        help='Date and time when the controller\'s system information (hardware details, capabilities, firmware version) was last retrieved. Updates when F0 command is executed.'
    )

    commands_count = fields.Char(
        string='Commands count', 
        compute='_compute_counts',
        help='Total number of commands (pending and executed) for this controller. High numbers may indicate communication issues if commands are not being processed.'
    )
    system_event_count = fields.Char(
        string='System Events count', 
        compute='_compute_counts',
        help='Number of system events (errors, status changes, communication issues) logged by this controller. Review these events to monitor controller health.'
    )
    user_event_count = fields.Char(
        string='User events count', 
        compute='_compute_counts',
        help='Number of user access events (card swipes, access granted/denied, door forced) recorded by this controller\'s readers. Shows access activity level.'
    )
    readers_count = fields.Char(
        string='Readers count', 
        compute='_compute_counts',
        help='Number of card readers configured for this controller. Typically matches the number of doors multiplied by 2 (one reader per side of each door).'
    )
    doors_count = fields.Char(
        string='Doors count', 
        compute='_compute_counts',
        help='Number of doors managed by this controller. Depends on the controller mode: single door, two doors, or up to four doors for advanced models.'
    )
    alarm_line_count = fields.Char(
        string='Alarm line count', 
        compute='_compute_counts',
        help='Number of alarm zones configured for this controller. Each zone can monitor different security sensors and trigger specific responses.'
    )

    default_io_table = fields.Char(
        compute='_compute_default_io_table',
        help='Factory default I/O table configuration for this controller model and mode. Used as a template when resetting or initializing the I/O logic table.'
    )

    @api.constrains('mode')
    def _check_mode(self):
        for ctrl in self:
            if ctrl.mode == 0:
                raise exceptions.ValidationError(_('The controller mode value is invalid. Please check it!'))

    @api.depends('input_states')
    def _compute_emergency_state(self):
        for c in self:
            if c.inputs > 0:
                soft = c._get_input_state(14)
                hard = c._get_input_state(c.inputs)
                c.emergency_state = (soft and 'soft') or (hard and 'hard') or 'off'
            else:
                c.emergency_state = 'off'

    def _inverse_emergency_state(self):
        for c in self.with_user(SUPERUSER_ID):
            if c.emergency_state != 'hard':
                c.change_output_state(99, c.emergency_state == 'soft' and 1 or 0)
                c._update_input_state(14, c.emergency_state == 'soft' and 1 or 0)

    @api.depends('mode')
    def _compute_controller_mode(self):
        for c in self:
            if c.mode <= 2:
                c.mode_selection = str(c.mode)
                c.mode_selection_4 = '2'  # Fake
            else:
                c.mode_selection = '1'  # Fake
                c.mode_selection_4 = str(c.mode)

    @api.depends('mode')
    def _compute_controller_mode_31(self):
        for c in self:
            if c.is_relay_ctrl():
                c.mode_selection_31 = str(c.mode)
            else:
                c.mode_selection_31 = '1'

    def _inverse_controller_mode_31(self):
        for ctrl in self:
            ctrl.change_controller_mode(int(ctrl.mode_selection_31))

    def _inverse_controller_mode_4(self):
        for ctrl in self:
            ctrl.change_controller_mode(int(ctrl.mode_selection_4))

    def _inverse_controller_mode(self):
        for ctrl in self:
            ctrl.change_controller_mode(int(ctrl.mode_selection))

    @api.depends('reader_ids', 'door_ids', 'alarm_line_ids')
    def _compute_counts(self):
        for a in self:
            a.commands_count = self.env['hr.rfid.command'].search_count([('controller_id', '=', a.id)])
            a.system_event_count = self.env['hr.rfid.event.system'].search_count([('controller_id', '=', a.id)])
            a.readers_count = len(a.reader_ids)
            a.doors_count = len(a.door_ids)
            a.alarm_line_count = len(a.alarm_line_ids)
            a.user_event_count = self.env['hr.rfid.event.user'].search_count(
                [('reader_id', 'in', a.reader_ids.mapped('id'))])

    @api.depends('output_states')
    def _compute_siren_state(self):
        for c in self:
            siren_out = (c.alarm_lines == 1) and 4 or 10
            c.siren_state = c._get_output_state(siren_out)

    def _set_siren_state(self):
        for c in self:
            siren_out = (c.alarm_lines == 1) and 4 or 10
            if not self.env.context.get('no_output', False):
                c.change_output_state(siren_out, int(c.siren_state), 99)
            c._update_output_state(siren_out, c.siren_state)

    @api.depends('hw_version')
    def _compute_default_io_table(self):
        for c in self:
            empty_io_table = ''.join(['0000000000000000' for i in range(0, c.io_table_lines)])
            default_io_table = polimex.get_default_io_table(int(c.hw_version), int(c.mode))
            c.default_io_table = default_io_table or empty_io_table

    def return_action_to_open(self):
        """ This opens the xml view specified in xml_id for the current app """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        dom = self.env.context.get('dom')
        key = self.env.context.get('key')
        op = self.env.context.get('op')
        if dom:
            domain = dom
        elif key and op:
            domain = [(key, op, self.id)]
        elif xml_id == 'hr_rfid_event_user_action':
            domain = [('reader_id', 'in', self.reader_ids.mapped('id'))]
        else:
            domain = [('controller_id', '=', self.id)]
        model = 'hr_rfid'
        if xml_id:
            res = self.env['ir.actions.act_window']._for_xml_id(model + '.' + xml_id)
            res.update(
                context=dict(self.env.context, default_controller_id=self.id, group_by=False),
                domain=domain
            )
            return res
        return False

    @api.model
    def update_ctrl_alarm_lines(self):
        ctrl_ids = self.env['hr.rfid.ctrl'].sudo().search([('alarm_lines', '>', 0), ('alarm_line_ids', '=', False)])
        ctrl_ids._setup_alarm_lines()
        ctrl_ids.read_alarm_lines_setup()
        return True

    def button_reload_cards(self):
        cmd_env = self.env['hr.rfid.command'].with_user(SUPERUSER_ID)
        self._base_command('DC', '0303')
        self._base_command('DC', '0404')

        for door in self.door_ids:
            self.env['hr.rfid.card.door.rel'].reload_door_rels(door)
        return self.balloon_success(
            title=_("Controller cards reload"),
            message=_("This will take time. For more information check controller's commands")
        )

    def _get_alarm_line_state(self, zone_number):
        self.ensure_one()
        # zone_states = [
        #     'unknown',
        #     'disabled'
        #     'short',
        #     'normal',
        #     's1',
        #     's2',
        #     's12',
        #     'open',
        #     'arm',
        #     'disarm',
        #     'no_alarm',
        # ]
        if not self.alarm_line_states or self.alarm_line_states == '0':
            return 'no_alarm', 'unknown'
        try:
            state = int(self.alarm_line_states[(zone_number - 1) * 2:(zone_number - 1) * 2 + 2], 16)
        except Exception as e:
            print(self.name, zone_number, e)
        res_state = 'disabled'
        if state & 1 == 1: res_state = 'short'
        if state & 2 == 2: res_state = 'normal'
        if state & 4 == 4: res_state = 's1'
        if state & 8 == 8: res_state = 's2'
        if state & 16 == 16: res_state = 's12'
        if state & 32 == 32: res_state = 'open'

        if state & 64 == 64:
            return 'arm', res_state
        else:
            return 'disarm', res_state

    def _get_io_line(self, line_number: int):
        self.ensure_one()
        if not self.is_relay_ctrl() and self.io_table:
            if not (0 < line_number < self.io_table_lines + 1):
                raise "Invalid IO Line number"
            line = self.io_table[16 * (line_number - 1):16 * (line_number - 1) + 16]
            return [int(line[i * 2:i * 2 + 2], 16) for i in reversed(range(0, 8))]
        else:
            return []

    def _set_io_line(self, line_number: int, line: [int]):
        self.ensure_one()
        if not (0 < line_number < self.io_table_lines + 1):
            raise "Invalid IO Line number"
        self.change_io_table(''.join([f"{line[i]:02X}" for i in reversed(range(0, 8))]), line_number)

    def change_io_table(self, new_io_table, line=0, no_command=False):
        cmd_data = f"{line:02d}" + new_io_table
        for ctrl in self:
            if ctrl.io_table == new_io_table:
                continue

            if ((ctrl.io_table_lines * 8 * 2) != len(new_io_table) and line == 0) or (
                    line != 0 and len(new_io_table) != 16):
                pass
                raise exceptions.ValidationError(
                    _('IO table lengths are different, this should never happen????')
                )
            if line == 0:
                ctrl.io_table = new_io_table
                if not no_command:
                    ctrl.write_io_table_cmd(cmd_data)
            else:  # line != 0 !!!
                self.io_table = self.io_table or self.default_io_table
                io_table = self.io_table[16 * (line - 1): 16 * (line - 1) + 16]
                if io_table == new_io_table:
                    continue
                io_table = self.io_table[:16 * (line - 1)] + new_io_table + self.io_table[16 * (line - 1) + 16:]
                ctrl.io_table = io_table
                if not no_command:
                    ctrl.write_io_table_cmd(cmd_data)

    def is_alarm_ctrl(self, hw_version=None):
        if hw_version:
            return hw_version in ['10', '11']
        elif self:
            self.ensure_one()
            return self.alarm_lines > 0

    def is_relay_ctrl(self, hw_version=None):
        if hw_version:
            return hw_version in ['30', '31', '32']
        elif self:
            self.ensure_one()
            return self.hw_version in ['30', '31', '32']

    def is_vending_ctrl(self, hw_version=None):
        if hw_version:
            return hw_version in ['16']
        elif self:
            self.ensure_one()
            return self.hw_version in ['16']

    def is_turnstile_ctrl(self, hw_version=None):
        if hw_version:
            return hw_version in ['9']
        elif self:
            self.ensure_one()
            return self.hw_version in ['9']

    def is_temperature_ctrl(self, hw_version=None):
        if hw_version:
            return hw_version in ['22']
        elif self:
            self.ensure_one()
            return self.hw_version in ['22']

    def get_ctrl_model_name(self, hw_id):
        tmp = -1
        if hw_id:
            tmp = hw_id
        elif self:
            self.ensure_one()
            tmp = self.hw_version
        for m in polimex.HW_TYPES:
            if m[0] == tmp:
                return m[1]
        return _('Unknown')

    def re_read_ctrl_info(self):
        for ctrl in self:
            ctrl.read_controller_information_cmd(ctrl)
        return self.balloon_success(
            title=_("Refresh Controller information"),
            message=_("This will take time. For more information check controller's commands")
        )

    def write(self, vals):
        from_controller = self.env.context.get('from_controller', False)
        for ctrl in self:
            old_ext_db = ctrl.external_db
            old_alarm_lines_setup = ctrl.alarm_lines_setup
            super(HrRfidController, ctrl).write(vals)
            new_ext_db = ctrl.external_db
            if 'alarm_sensor_events' in vals.keys():
                ctrl.write_alarm_line_setup()
            if 'alarm_lines_setup' in vals.keys() and vals['alarm_lines_setup'] != old_alarm_lines_setup:
                ctrl.update_alarm_lines_setup()
            if 'alarm_line_states' in vals.keys():
                ctrl.alarm_line_ids._compute_states()

            # if old_ext_db != new_ext_db or 'dual_person_mode' in vals.keys() or 'relay_time_factor' in vals.keys():
            if not from_controller and ('external_db' in vals.keys() or 'dual_person_mode' in vals.keys() or 'relay_time_factor' in vals.keys()):
                ctrl.write_controller_mode()
            if (
                    'high_temperature' in vals or 'low_temperature' in vals or 'hysteresis' in vals) and not self.env.context.get(
                'readed', False):
                ctrl.temp_range_cmd(
                    ctrl.high_temperature,
                    ctrl.low_temperature,
                    ctrl.hysteresis
                )
        if not from_controller and 'output_ts_ids' in vals.keys():
            self.write_output_ts()
        if not from_controller and ("input_mask_ids" in vals.keys() or "relay_output_mask" in vals.keys()):
            new_mask = sum((1 << i) for i, bit in enumerate(self.input_mask_ids) if bit.i_mask)
            self.write_input_masks_cmd(new_mask)

    def sys_event(self, error_description, event_action, input_json):
        for ctrl in self:
            self.env['hr.rfid.event.system'].sudo().create({
                'webstack_id': ctrl.webstack_id.id,
                'controller_id': ctrl.id,
                'timestamp': fields.Datetime.now(),
                'event_action': event_action,
                'error_description': error_description,
                'input_js': input_json,
            })

    def enabled_alarm_lines(self):
        return self.alarm_line_ids.filtered(lambda l: l.state != 'disabled')

    #  Helper functionality

    def _setup_alarm_lines(self):
        for ctrl in self.filtered(lambda c: (len(c.alarm_line_ids) == 0) and (c.alarm_lines > 0)):
            line_ids = self.env['hr.rfid.ctrl.alarm'].sudo().create([
                {
                    'line_number': i + 1,
                    'name': _('Alarm Line {} on {}').format(i + 1, ctrl.name),
                    'controller_id': ctrl.id,
                    'control_output': ctrl.alarm_lines == 1 and (4 + i + 1) or (10 + i + 1),
                } for i in range(ctrl.alarm_lines)]
            )
            ctrl.sudo().write({'alarm_line_ids': [(4, line, 0) for line in line_ids.mapped('id')]})
            if ctrl.alarm_lines == 1:
                ctrl.door_ids[0].write({'alarm_line_ids': [(4, line_ids[0].id, 0)]})
            else:
                if ctrl.mode == 2:
                    ctrl.door_ids[0].write({'alarm_line_ids': [(4, line_ids[0].id, 0), (4, line_ids[1].id, 0)]})
                    ctrl.door_ids[1].write({'alarm_line_ids': [(4, line_ids[2].id, 0), (4, line_ids[3].id, 0)]})
                if ctrl.mode == 3:
                    ctrl.door_ids[0].write({'alarm_line_ids': [(4, line_ids[0].id, 0), (4, line_ids[1].id, 0)]})
                    ctrl.door_ids[1].write({'alarm_line_ids': [(4, line_ids[2].id, 0)]})
                    ctrl.door_ids[2].write({'alarm_line_ids': [(4, line_ids[3].id, 0)]})
                if ctrl.mode == 4:
                    ctrl.door_ids[0].write({'alarm_line_ids': [(4, line_ids[0].id, 0)]})
                    ctrl.door_ids[1].write({'alarm_line_ids': [(4, line_ids[1].id, 0)]})
                    ctrl.door_ids[2].write({'alarm_line_ids': [(4, line_ids[2].id, 0)]})
                    ctrl.door_ids[3].write({'alarm_line_ids': [(4, line_ids[3].id, 0)]})

    def _get_input_state(self, input_number):
        self.ensure_one()
        return (self.input_states & pow(2, input_number - 1)) == pow(2, input_number - 1)

    def _update_input_state(self, input_number, state: bool):
        for c in self.with_user(SUPERUSER_ID):
            if state:
                c.input_states = c.input_states | pow(2, input_number - 1)
            elif (c.input_states & pow(2, input_number - 1)) == pow(2, input_number - 1):
                c.input_states = c.input_states - pow(2, input_number - 1)

    def _get_output_state(self, output_number):
        self.ensure_one()
        return self.output_states & (2 ** (output_number - 1)) == (2 ** (output_number - 1))

    def _update_output_state(self, output_number, state):
        '''
        Output Number from 1
        State 0 or 1, True or False
        '''
        for c in self.with_user(SUPERUSER_ID):
            if state:  # !=0
                if c.output_states and (2 ** (output_number - 1)) != (2 ** (output_number - 1)):
                    c.output_states += (2 ** (output_number - 1))
            elif c.output_states and (2 ** (output_number - 1)) == (2 ** (output_number - 1)):
                c.output_states -= (2 ** (output_number - 1))

    def convert_int_to_cmd_data_for_output_control(self, data):
        self.ensure_one()
        if not self.is_relay_ctrl():
            cmd_data = '{:02X}'.format(data)
        else:
            cmd_data = '%03d%03d%03d%03d' % (
                (data >> (3 * 8)) & 0xFF,
                (data >> (2 * 8)) & 0xFF,
                (data >> (1 * 8)) & 0xFF,
                (data >> (0 * 8)) & 0xFF,
            )
            cmd_data = ''.join(['0' + ch for ch in cmd_data])
        return cmd_data

    def create_output_data_for_relay_control(self, out_number: int):
        self.ensure_one()
        if self.is_relay_ctrl():
            if self.mode in [1, 2]:
                data = 1 << (out_number - 1)
                # if self.reader_ids.number == 2 and self.mode == 2:
                #     data *= 0x10000
            elif self.mode == 3:
                data = out_number
            else:
                raise exceptions.ValidationError(_('Controller %s has mode=%d, which is not supported!')
                                                 % (self.name, self.mode))
        else:
            data = out_number

        return self.convert_int_to_cmd_data_for_output_control(data)

    def _find_th_sensor(self, sensor_number: int = None, internal_number: int = None):
        self.ensure_one()
        if sensor_number is None and internal_number is None:
            return
        th_id = None
        if sensor_number is not None:
            th_id = self.env['hr.rfid.ctrl.th'].with_context(active_test=False).search([
                ('controller_id', '=', self.id),
                ('sensor_number', '=', sensor_number),
            ])
        elif internal_number is not None:
            th_id = self.env['hr.rfid.ctrl.th'].with_context(active_test=False).search([
                ('controller_id', '=', self.id),
                ('internal_number', '=', internal_number),
            ])
        return th_id

    def update_th(self, sensor_number: int = None, internal_number: int = None, data_dict: dict = {}):
        '''
        sensor_number:int any number!. system sensor(integrated) number 0
        data_dict: expect {'t':float, 'h':float}
        '''
        for c in self:
            th_id = c._find_th_sensor(sensor_number, internal_number)
            if not th_id and sensor_number is not None:
                th_id = self.env['hr.rfid.ctrl.th'].create([{
                    'name': _('T&H Sensor {} on {}').format(sensor_number, c.name),
                    'controller_id': c.id,
                    'sensor_number': sensor_number
                }])

            if not th_id:
                _logger.error('Receiving data for Temperature and/or Humidity but can not find the sensor in DB')
                return

            new_dict = {}
            if 't' in data_dict:
                new_dict.update({'temperature': data_dict['t']})
                # if sensor_number == 0:
                c.temperature = data_dict['t']
            if 'h' in data_dict:
                new_dict.update({'humidity': data_dict['h']})
                # if sensor_number == 0:
                c.humidity = data_dict['h']
            if new_dict:
                th_id.write(new_dict)
                return th_id

    def decode_door_number_for_relay(self, data):
        self.ensure_one()
        pcs_str = [data[i * 6:i * 6 + 6] for i in range(4)]  # ['000000', '000000', '000000', '000101']
        pcs_int = []
        for pcs in pcs_str:
            pcs_int.append(int(''.join(str(int(pcs[i * 2: i * 2 + 2])) for i in range(3))))
        return int(''.join([str(p) for p in pcs_int]))

    def update_alarm_lines_setup(self, new_data=None):
        for c in self.filtered(lambda ctrl: ctrl.alarm_lines_setup != '').with_context({'from_controller':True}):
            ctrlB0 = []
            data = new_data or c.alarm_lines_setup
            if len(data) == 6:
                c.alarm_sensor_events = bool(1 if (int(data[4:6], 16) & (1 << 4)) == 1 else 0)
                for number in range(self.alarm_lines):
                    ctrlB0.append({
                        'enableAC': not bool(1 if (int(data[0:2], 16) & (1 << number)) == (1 << number) else 0),
                        'enableDC': not bool(1 if (int(data[2:4], 16) & (1 << number)) == (1 << number) else 0),
                        'enabled': bool(1 if (int(data[4:6], 16) & (1 << number)) == (1 << number) else 0),
                    })
                    if number < len(c.alarm_line_ids):
                        c.alarm_line_ids[number].write(ctrlB0[number])

    # Commands to controllers
    def _base_command(self, cmd: str, cmd_data: str = None, cmd_dict: dict = None):
        commands = self.env['hr.rfid.command']
        # Generate commands
        for c in self:
            new_cmd = cmd_dict or {'webstack_id': c.webstack_id.id,
                                   'controller_id': c.id,
                                   'cmd': cmd,
                                   }
            if cmd and not cmd_dict and cmd_data:
                new_cmd.update({'cmd_data': cmd_data})
            commands += self.env['hr.rfid.command'].find_last_wait(new_cmd) or self.env['hr.rfid.command'].with_user(
                SUPERUSER_ID).create([new_cmd])
        # Execute commands
        for c in commands:
            if not c.webstack_id.is_limit_executed_cmd_reached() and not c.webstack_id.behind_nat and c.webstack_id.active:
                try:
                    c.webstack_id.direct_execute({}, c)
                except Exception as e:
                    _logger.error('Direct execute failed for %s: %s', c.controller_id.name, e)
                    if c.status == 'Process':
                        c.status = 'Wait'
                        c.retries += 1
                    if c.retries >= 3:
                        c.status = 'Failure'
                        c.error = str(e)[:200]

        return commands

    def change_output_state(self, out_number: int, out_state: int, time: int = 0):
        """
        :param out: 0 to open door, 1 to close door
        :param time: Range: [0, 99]
        """
        _logger.info('Change Output %d state to %d for %d seconds.', out_number, out_state, time)
        self.ensure_one()
        cmd = {
            'cmd': {
                'id': self.ctrl_id,
                'c': 'DB',
            }
        }
        if self.is_relay_ctrl():
            # 1 byte - 64(0x40), Event Number(1 byte), 12 byte card data
            # 1 byte - 31(0x1F), Reader number(1 byte), 12 byte output number (card data)
            # mode 1 and 3- any reader, mode 2- 1..16(R1), 17..32(R2)
            if self.mode == 2:
                reader = (out_number < 17) and 1 or 2
            else:
                reader = 1
            cmd_data = ('1F%02X' % reader) + self.create_output_data_for_relay_control(out_number)
        else:
            cmd_data = '%02x%02d%02d' % (out_number, out_state, time)

        res = self.with_user(SUPERUSER_ID)._base_command('DB', cmd_data)

    def read_controller_information_cmd(self):
        return self._base_command('F0')

    def read_status(self):
        return self._base_command('B3')

    def read_alarm_lines_setup(self):
        return self._base_command('B0', '01')

    def synchronize_clock_cmd(self):
        return self._base_command('D7')

    def delete_all_cards_cmd(self):
        return self._base_command('DC', '0303')

    def delete_all_events_cmd(self):
        return self._base_command('DC', '0404')

    def read_io_table_cmd(self):
        if self.webstack_id.is_10_3():
            return [self._base_command('F9', '%02X' % (i + 1)) for i in range(self.io_table_lines)]
        else:
            return self._base_command('F9', '00')

    def write_io_table_cmd(self, cmd_data):
        if self.webstack_id.is_10_3() and len(cmd_data) > (2 + 16):
            return [self._base_command('D9', '%02X' % (i + 1) + cmd_data[2 + i * 16:2 + i * 16 + 16]) for i in
                    range(self.io_table_lines)]
        else:
            return self._base_command('D9', cmd_data)

    def read_readers_mode_cmd(self):
        return self._base_command('F6')

    def read_anti_pass_back_mode_cmd(self):
        return self._base_command('FC')

    def read_input_masks_cmd(self):
        return self._base_command('FB')

    def write_input_masks_cmd(self, masks: int = None):
        result = self.env['hr.rfid.command']
        if masks is None:
            for c in self:
                new_mask = sum((1 << i) for i, bit in enumerate(c.input_mask_ids) if bit.i_mask)
                result += c.write_input_masks_cmd(new_mask)
            return result
        for c in self:
            m = masks or c.inputs_mask or 0
            cmd_masks = [int(m >> (i * 7)) & 0x7F for i in range(4)]
            if c.is_relay_ctrl():
                cmd_masks[2] = cmd_masks[3] = 0x7F if c.relay_output_mask else 0
            cmd_data = ''.join(['%02X' % d for d in cmd_masks])
            result += self._base_command('DD', cmd_data)
            c.inputs_mask = m
        return result

    def write_alarm_line_setup(self):
        # _logger.info('Write Alarm Line Setup')
        result = self.env['hr.rfid.command']
        for ctrl in self:
            enableAC = enableDC = enabled = 0
            for line in range(4):
                if len(ctrl.alarm_line_ids)>=(line+1):
                    enableAC += int(not ctrl.alarm_line_ids[line].enableAC) << line
                    enableDC += int(not ctrl.alarm_line_ids[line].enableDC) << line
                    enabled += int(ctrl.alarm_line_ids[line].enabled) << line
            enabled += int(ctrl.alarm_sensor_events) << 4
            cmd_data = '00%02X%02X%02X' % (enableAC, enableDC, enabled)
            result += ctrl._base_command('B0', cmd_data)
            result += ctrl.read_status()
            ctrl.read_b3_cmd = False
        return result

    def process_input_masks(self, masks, output_relay_mask):
        for c in self:
            self.env['hr.rfid.ctrl.input.mask'].with_context({'from_controller':True})._generate_input_masks(c, masks)
            c.with_context({'from_controller':True}).write(
                {'inputs_mask': masks, 'relay_output_mask': 0x7F in output_relay_mask}
            )

    def read_outputs_ts_cmd(self):
        return self._base_command('FF')

    def temp_range_cmd(self, high_temp=None, low_tempt=None, hyst=None):
        if high_temp is None:
            return self._base_command('B1', '01')
        else:
            ht = ['%.2d' % i for i in polimex.get_reverse_temperature(self.high_temperature)]
            lt = ['%.2d' % i for i in polimex.get_reverse_temperature(self.low_temperature)]
            h = ['%.2d' % i for i in polimex.get_reverse_temperature(self.hysteresis)]
            # 00 0100 0090 0010       00 0001 5a00 0a00
            return self._base_command('B1', '00%s%s%s' % (''.join(ht), ''.join(lt), ''.join(h)))

    def read_cards_cmd(self, position=0, count=0):
        if count == 0:
            return self._base_command(
                cmd='F2',
                cmd_data=''.join(['0%s' % d for d in ('%.5d' % position)]) + '%.2d' % count,
            )
        else:
            if (self.cards_count > 0) and (self.cards_count >= position):
                if self.cards_count < (position + polimex.READ_CARDS_BLOCK_SIZE):
                    cmd_count = self.cards_count - position + 1
                else:
                    cmd_count = polimex.READ_CARDS_BLOCK_SIZE
                first_command = self._base_command(
                    cmd='F2',
                    cmd_data=''.join(['0%s' % d for d in ('%.5d' % position)]) + '%.2d' % cmd_count,
                )
                if count - cmd_count > 0:
                    self.read_cards_cmd(position=position + cmd_count, count=count - cmd_count)
                return first_command
            else:
                pass

    def create_d1_cmd(self, card_num, pin_code, ts_code, rights_data, rights_mask):
        commands = []
        for controller in self:
            commands.append(
                self.env['hr.rfid.command'].with_user(SUPERUSER_ID).create([{
                    'webstack_id': controller.webstack_id.id,
                    'controller_id': controller.id,
                    'cmd': 'D1',
                    'card_number': card_num,
                    'pin_code': pin_code,
                    'ts_code': ts_code,
                    'rights_data': rights_data,
                    'rights_mask': rights_mask,
                }])
            )
        if len(commands) == 1:
            return commands[0]
        else:
            return commands

    def _create_d1_cmd_relay(self, card_num, rights_data, rights_mask):
        commands = []
        for controller in self:
            commands.append(
                self.env['hr.rfid.command'].with_user(SUPERUSER_ID).create([{
                    'webstack_id': controller.webstack_id.id,
                    'controller_id': controller.id,
                    'cmd': 'D1',
                    'card_number': card_num,
                    'rights_data': rights_data,
                    'rights_mask': rights_mask,
                }])
            )
        if len(commands) == 1:
            return commands[0]
        else:
            return commands

    def add_remove_card(self, card_number, pin_code, ts_code, rights_data, rights_mask):
        commands = []
        commands_env = self.env['hr.rfid.command'].with_user(SUPERUSER_ID)
        for controller in self:
            old_cmd = commands_env.search([
                ('cmd', '=', 'D1'),
                ('status', '=', 'Wait'),
                ('card_number', '=', card_number),
                ('controller_id', '=', controller.id),
            ], limit=1)

            if not old_cmd:
                if rights_mask != 0:
                    commands += controller.create_d1_cmd(card_number, pin_code, ts_code, rights_data, rights_mask)
            else:
                new_ts_code = ''
                if str(ts_code) != '':
                    for i in range(4):
                        num_old = int(old_cmd.ts_code[i * 2:i * 2 + 2], 16)
                        num_new = int(ts_code[i * 2:i * 2 + 2], 16)
                        if num_new == 0:
                            num_new = num_old
                        new_ts_code += '%02X' % num_new
                else:
                    new_ts_code = old_cmd.ts_code
                write_dict = {
                    'pin_code': pin_code,
                    'ts_code': new_ts_code,
                }

                new_rights_data = (rights_data | old_cmd.rights_data)
                new_rights_data ^= (rights_mask & old_cmd.rights_data)
                new_rights_data ^= (rights_data & old_cmd.rights_mask)
                new_rights_mask = rights_mask | old_cmd.rights_mask
                new_rights_mask ^= (rights_mask & old_cmd.rights_data)
                new_rights_mask ^= (rights_data & old_cmd.rights_mask)

                write_dict['rights_mask'] = new_rights_mask
                write_dict['rights_data'] = new_rights_data

                if new_rights_mask == 0:
                    old_cmd.unlink()
                else:
                    old_cmd.write(write_dict)
        if len(commands) == 1:
            return commands[0]
        else:
            return commands

    def _add_remove_card_relay(self, card_number, rights_data, rights_mask):
        commands = []
        commands_env = self.env['hr.rfid.command'].with_user(SUPERUSER_ID)
        for controller in self:
            old_cmd = commands_env.search([
                ('cmd', '=', 'D1'),
                ('status', '=', 'Wait'),
                ('card_number', '=', card_number),
                ('controller_id', '=', controller.id),
            ])

            if not old_cmd:
                commands += self._create_d1_cmd_relay(card_number, rights_data, rights_mask)
            else:
                if controller.mode == 3:
                    new_rights_data = rights_data
                    new_rights_mask = rights_mask
                else:
                    new_rights_data = (rights_data | old_cmd.rights_data)
                    new_rights_data ^= (rights_mask & old_cmd.rights_data)
                    new_rights_data ^= (rights_data & old_cmd.rights_mask)
                    new_rights_mask = rights_mask | old_cmd.rights_mask
                    new_rights_mask ^= (rights_mask & old_cmd.rights_data)
                    new_rights_mask ^= (rights_data & old_cmd.rights_mask)
                # TODO Check if result is usless and delete command as previos function
                old_cmd.write({
                    'rights_mask': new_rights_mask,
                    'rights_data': new_rights_data,
                })
        if len(commands) == 1:
            return commands[0]
        else:
            return commands

    def write_controller_mode(self, new_mode: int = None, new_ext_db: bool = None, new_dual_person_mode: bool = None, new_relay_factor: int = None):
        if new_mode is None:
            new_mode = self.mode
        if new_ext_db is None:
            new_ext_db = self.external_db
        if new_relay_factor is None:
            new_relay_factor = self.relay_time_factor
        if new_dual_person_mode is None:
            new_dual_person_mode = self.dual_person_mode

        cmd_data = '%02X' % (int(new_relay_factor) * 0x40 + int(new_ext_db) * 0x20 + int(new_dual_person_mode) * 0x08 + int(new_mode))
        cmd = self._base_command('D5', cmd_data)
        self.read_controller_information_cmd()
        return cmd

    def write_ts(self, ts_data: str):
        return self._base_command('D3', ts_data)

    def write_ts_id(self, ts_id):
        if self.env.context.get('no_hardware_commands'):
            return
        if ts_id and ts_id.number != 0 and not ts_id.is_empty:
            for ctrl in self.filtered(lambda c: c.id not in ts_id.controller_ids.mapped('id')):
                ctrl.write_ts(ts_id.ts_data)
                ts_id.sudo().write({'controller_ids': [(4, ctrl.id, 0)]})

    def delete_ts_id(self, ts_id):
        if self.env.context.get('no_hardware_commands'):
            return
        if ts_id and ts_id.number != 0:
            for ctrl in self.filtered(lambda c: c.id in ts_id.controller_ids.mapped('id')):
                ts_used = self.env['hr.rfid.access.group.door.rel'].search([
                    ('door_id', 'in', ctrl.door_ids.mapped('id')),
                    ('time_schedule_id', '=', ts_id.id),
                ])
                if not ts_used:
                    ts_id.sudo().write({'controller_ids': [(3, ctrl.id, 0)]})

    def change_controller_mode(self, new_mode):
        for c in self:
            c.write_controller_mode(new_mode)

    def write_output_ts(self):
        for ctrl in self:
            cmd_data = ''
            ts_for_send = []
            for out in range(ctrl.outputs if ctrl.outputs <= 8 else 8):
                out_ts = ctrl.output_ts_ids.filtered(lambda rel: rel.output_number == out + 1)
                cmd_data += '%02X' % (out_ts and out_ts.time_schedule_id.number or 0)
                if out_ts and out_ts.time_schedule_id.number > 0:
                    ts_for_send.append(out_ts.time_schedule_id)
            ctrl._base_command('DF', cmd_data)
            if ts_for_send:
                [ctrl.write_ts_id(ts) for ts in ts_for_send]

    # Command parsers

    def cp_input_masks(self, response):
        pass

    def cp_outputs_ts(self, response):
        pass

    # Communication helpers
    def report_sys_ev(self, description, post_data=None, sys_ev_dict: dict = None):
        '''
        Create System event
        Dict = {
            'webstack_id': id,
            'controller_id': id,
            'timestamp': timestamp,
            'event_action': str event number,
            'error_description': str,
            'input_js': str Input JSON
        }
        '''
        for ctrl in self:
            ctrl.webstack_id.report_sys_ev(description, post_data, ctrl, sys_ev_dict)
