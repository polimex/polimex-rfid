from odoo import api, fields, models

from ..helpers import codecs

FAMILY_SELECTION = [
    ('access', 'Access control'),
    ('hotel', 'Hotel access control'),
    ('vending', 'Vending machine'),
    ('relay', 'Relay controller'),
    ('io', 'Input/output module'),
    ('temperature', 'Temperature controller'),
    ('fire', 'Fire panel'),
    ('gas', 'Gas detector'),
    ('power', 'Power controller'),
    ('alarm', 'Alarm controller'),
    ('reader', 'Reader'),
    ('motor', 'Motor controller'),
    ('unknown', 'Unknown'),
]


class HwImportCtrl(models.Model):
    _name = 'hr.rfid.hw.import.ctrl'
    _description = 'Surveyed Controller'
    _order = 'module_id, address'

    run_id = fields.Many2one('hr.rfid.hw.import.run', required=True, ondelete='cascade', index=True,
                             help="The survey that read this controller.")
    module_id = fields.Many2one('hr.rfid.hw.import.module', required=True, ondelete='cascade', index=True,
                                help="The module this controller is connected to.")
    address = fields.Integer(string="Address on the bus", required=True, help="Address of the controller on the module's bus (1-254).")
    dev_index = fields.Integer(string="Position in the module list", help="Position of the controller in the module's own list.")
    name = fields.Char(compute='_compute_name', store=True,
                       help="Model, serial number and address, as the access control module names controllers.")
    hw_code = fields.Char(string="Hardware type code", help="Hardware type code the controller reports.")
    hw_name = fields.Char(compute='_compute_family', store=True, help="Model name for that hardware type.")
    family = fields.Selection(FAMILY_SELECTION, compute='_compute_family', store=True, index=True,
                              help="What kind of device this is. Only access controllers hold cards; "
                                   "vending machines are left out of the survey entirely.")
    serial = fields.Char(string="Serial number", index=True, help="Serial number the controller reports.")
    sw_version = fields.Char(string="Firmware", help="Firmware version the controller reports.")
    mode = fields.Integer(string="Operating mode", help="Operating mode (1-4); it decides how readers are grouped into doors.")
    external_db = fields.Boolean(string="Asks the server for unknown cards", help="The controller asks the server before granting unknown cards.")
    dual_person = fields.Boolean(string="Two cards to open", help="Two cards are required to open a door.")
    interlocking = fields.Boolean(string="Interlocked doors", help="Doors are interlocked: one opens only when the other is closed.")
    relay_time_factor = fields.Boolean(string="Relay times in tenths of a second", help="Relay times are in tenths of a second instead of seconds.")
    readers = fields.Integer(help="Number of readers the controller has.")
    inputs = fields.Integer(help="Number of inputs.")
    outputs = fields.Integer(help="Number of outputs (relays).")
    time_schedules = fields.Integer(string="Schedule slots", help="How many time schedule slots the controller holds.")
    io_table_lines = fields.Integer(string="Input/output table rows", help="Rows in the input/output table.")
    alarm_lines = fields.Integer(string="Alarm zones", help="Alarm zones the controller has (0 when it has none).")
    max_cards = fields.Integer(string="Card capacity", help="How many cards the controller can hold.")
    max_events = fields.Integer(string="Event capacity", help="How many events the controller can buffer.")
    record_size = fields.Integer(string="Bytes per card record", help="Bytes per card record for this model; decides how the card table is read.")
    reads_cards = fields.Boolean(compute='_compute_family', store=True,
                                 help="The card table of this controller is read by the survey.")

    f0_hex = fields.Char(string="System information (raw)", help="Raw system information reply (evidence).")
    f5_hex = fields.Char(string="Operating mode (raw)", help="Raw controller mode reply.")
    f6_hex = fields.Char(string="Reader settings (raw)", help="Raw reader modes reply.")
    f8_hex = fields.Char(string="Input/output settings (raw)", help="Raw duress settings reply.")
    f9_hex = fields.Text(string="Input/output table (raw)", help="Raw input/output table reply.")
    fb_hex = fields.Char(string="Input masks (raw)", help="Raw input masks reply.")
    fc_hex = fields.Char(string="Anti-passback settings (raw)", help="Raw anti-passback reply.")
    ff_hex = fields.Char(string="Output schedules (raw)", help="Raw output time schedules reply.")
    b0_hex = fields.Char(string="Alarm zone settings (raw)", help="Raw alarm zone setup reply.")
    b3_hex = fields.Char(string="Status (raw)", help="Raw status reply.")
    f7_hex = fields.Char(string="Clock (raw)", help="Raw clock reply.")

    reader_modes_json = fields.Text(string="Reader settings", help="Reader modes as read (decoded).")
    io_table_hex = fields.Text(string="Input/output table", help="The input/output table in the form the access control module stores it.")
    input_mask = fields.Integer(string="Input mask", help="Input mask as read.")
    output_relay_mask = fields.Boolean(string="Relay output mask", help="Relay output mask flag as read.")
    apb_bitmap = fields.Integer(string="Anti-passback per door", help="Anti-passback enabled per door (bit per door).")
    out_ts_json = fields.Text(string="Output schedules", help="Time schedule slot per output, as read.")
    alarm_setup_json = fields.Text(string="Alarm zone settings", help="Alarm zone setup as read (decoded).")
    status_json = fields.Text(string="Status at survey time", help="Live status at the time of the survey (decoded).")
    holidays_json = fields.Text(string="Holiday lists", help="Holiday lists per slot, as read.")
    clock_read = fields.Datetime(string="Controller clock", help="The controller's clock at the time of the survey.")
    clock_drift_seconds = fields.Integer(string="Clock difference (seconds)", help="Difference between the controller's clock and this server's.")
    gaps_json = fields.Text(string="Settings the controller cannot report", help="Commands this controller does not support (recorded, not an error).")

    card_count_device = fields.Integer(string="Cards on the device", help="How many cards the controller says it holds.")
    cards_read = fields.Integer(string="Cards read", help="How many card records were read so far.")
    read_cursor = fields.Integer(string="Reading position", default=1, help="Next card position to read; -1 once the table is complete.")
    read_state = fields.Selection([
        ('pending', 'Not read yet'),
        ('config', 'Reading settings'),
        ('cards', 'Reading cards'),
        ('done', 'Read'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ], default='pending', required=True, index=True,
        help="How far the reading of this controller has got.")
    read_error = fields.Text(string="Reading problem", help="Why reading failed, if it did.")
    include = fields.Boolean(default=True,
                             help="Read this controller and include it in the import. Vending machines cannot be included.")

    existing_ctrl_id = fields.Many2one('hr.rfid.ctrl', string="Existing controller", ondelete='set null',
                                       help="A controller with this serial that already exists here.")
    ctrl_rec_id = fields.Many2one('hr.rfid.ctrl', string="Imported as", ondelete='set null',
                                  help="The controller record created or reused by the import.")
    imported_without_doors = fields.Boolean(string="Settings only, no doors",
        help="The controller was imported with its settings only; its doors and readers "
             "could not be derived from the mode it reports.")
    door_map_json = fields.Text(string="Readers per door", help="Which readers belong to which door (derived from the mode).")
    zone_map_json = fields.Text(string="Alarm zones per door", help="Which alarm zones belong to which door (derived from the mode).")

    ts_ids = fields.One2many('hr.rfid.hw.import.ts', 'ctrl_id', string='Time schedules',
                             help="The time schedule slots read from this controller.")
    card_record_ids = fields.One2many('hr.rfid.hw.import.card.record', 'ctrl_id', string='Card records',
                                      help="The card records read from this controller.")

    _address_uniq = models.Constraint(
        'UNIQUE (module_id, address)',
        'A module cannot have two controllers at the same address.')

    @api.depends('hw_code', 'alarm_lines')
    def _compute_family(self):
        for ctrl in self:
            ctrl.family = codecs.family_of(ctrl.hw_code)
            ctrl.hw_name = codecs.hw_label(ctrl.hw_code)
            ctrl.reads_cards = codecs.reads_cards(ctrl.hw_code)

    @api.depends('hw_name', 'serial', 'address')
    def _compute_name(self):
        for ctrl in self:
            if ctrl.hw_code:
                ctrl.name = self.env._('%(model)s SN:%(serial)s ID:%(address)s',
                                       model=ctrl.hw_name, serial=ctrl.serial or '?',
                                       address=ctrl.address)
            else:
                ctrl.name = self.env._('Controller %(address)s', address=ctrl.address)

    def _door_map(self):
        self.ensure_one()
        return codecs.reader_door_map(self.hw_code, self.mode, self.readers)

    def _zone_map(self):
        self.ensure_one()
        return codecs.zone_door_map(self.alarm_lines, self.mode)
