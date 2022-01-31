from odoo import fields, models, api, exceptions, _, SUPERUSER_ID
from odoo.addons.hr_rfid.controllers.polimex import HW_TYPES


class HrRfidController(models.Model):
    _name = 'hr.rfid.ctrl'
    _inherit = ['mail.thread']
    _description = 'Controller'
    _sql_constraints = [('rfid_controller_unique', 'unique(serial_number)',
                         'Serial numbers must be unique!')]
    _order = 'webstack_id, ctrl_id'

    name = fields.Char(
        string='Name',
        help='Label to easily distinguish the controller',
        required=True,
        index=True,
        tracking=True,
    )

    ctrl_id = fields.Integer(
        string='ID',
        help='A number to distinguish the controller from others on the same module',
        index=True,
    )

    hw_version = fields.Selection(
        selection=HW_TYPES,
        string='Hardware Type',
        help='Type of the controller',
    )

    serial_number = fields.Char(
        string='Serial',
        help='Serial number of the controller',
        size=4,
    )

    sw_version = fields.Char(
        string='Version',
        help='The version of the software on the controller',
        size=3,
    )

    inputs = fields.Integer(
        string='Inputs',
        help='Hardware Inputs of the controller',
    )

    outputs = fields.Integer(
        string='Outputs',
        help='Hardware Outputs of the controller',
    )
    input_states = fields.Integer(
        help='State of the inputs of the controller',
    )

    output_states = fields.Integer(
        help='States the outputs of the controller',
    )

    readers = fields.Integer(
        string='Readers',
        help='Number of readers on the controller'
    )

    time_schedules = fields.Integer(
        string='Time Schedules',
        help='',
    )

    io_table_lines = fields.Integer(
        string='IO Table Lines',
        help='Size of the input/output table',
    )

    alarm_lines = fields.Integer(
        string='Alarm Lines',
        help='How many alarm inputs there are',
        default=0
    )

    alarm_line_states = fields.Char(
        string='Alarm Line States',
        help='Status of the Alarm lines',
    )

    siren_state = fields.Boolean(
        help='Alarm Siren state',
        compute='_compute_siren_state',
        inverse='_set_siren_state'
    )

    mode = fields.Integer(
        string='Controller Mode',
        help='The mode of the controller',
    )

    mode_selection = fields.Selection(
        string='Controller mode',
        selection=[('1', 'One door'), ('2', 'Two doors')],
        required=True,
        compute='_compute_controller_mode',
    )

    mode_selection_4 = fields.Selection(
        string='Controller mode',
        selection=[('2', 'Two doors'), ('3', 'Three doors'), ('4', 'Four doors')],
        required=True,
        compute='_compute_controller_mode',
    )

    mode_selection_31 = fields.Selection(
        string='Controller mode',
        selection=[('1', '1 x 32 Relays'), ('2', '2 x 16 Relays'), ('3', '1 x 512 Relays')],
        readonly=False,
        required=True,
        compute='_compute_controller_mode_31',
        inverse='_inverse_controller_mode_31',
    )

    external_db = fields.Boolean(
        string='External DB',
        help='If the controller uses the "ExternalDB" feature.',
        default=False,
    )

    relay_time_factor = fields.Selection(
        [('0', '1 second'), ('1', '0.1 seconds')],
        string='Relay Time Factor',
        default='0',
    )

    dual_person_mode = fields.Boolean(
        string='Dual Person Mode',
        default=False,
    )

    max_cards_count = fields.Integer(
        string='Maximum Cards',
        help='Maximum amount of cards the controller can hold in memory',
    )

    max_events_count = fields.Integer(
        string='Maximum Events',
        help='Maximum amount of events the controller can hold in memory',
    )

    hotel_readers = fields.Integer(
        string='Hotel readers',
        help='Hotel readers connected to controller',
        default=0
    )
    hotel_readers_card_presence = fields.Integer(
        string='Hotel readers card presence',
        help='Card inserted in Hotel readers connected to controller',
        default=0
    )
    hotel_readers_buttons_pressed = fields.Integer(
        string='Hotel readers buttons pressed',
        help='Pressed button on Hotel readers connected to controller',
        default=0
    )

    # Warning, don't change this field manually unless you know how to create a
    # command to change the io table for the controller or are looking to avoid exactly that.
    # You can use the change_io_table method to automatically create a command
    io_table = fields.Char(
        string='Input/Output Table',
        help='Input and output table for the controller.',
    )

    webstack_id = fields.Many2one(
        'hr.rfid.webstack',
        string='Module',
        help='Module the controller serves',
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    door_ids = fields.One2many(
        comodel_name='hr.rfid.door',
        inverse_name='controller_id',
        string='Controlled Doors',
        help='Doors that belong to this controller'
    )

    reader_ids = fields.One2many(
        comodel_name='hr.rfid.reader',
        inverse_name='controller_id',
        string='Controlled Readers',
        help='Readers that belong to this controller',
    )

    alarm_line_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.alarm',
        inverse_name='controller_id',
        string='Controlled Alarm Lines',
        help='Alarm lines that belong to this controller',
    )

    read_b3_cmd = fields.Boolean(
        string='Read Controller Status',
        default=False,
        index=True,
    )

    temperature = fields.Float(
        string='Temperature',
        default=0,
    )

    humidity = fields.Float(
        string='Humidity',
        default=0,
    )

    system_voltage = fields.Float(
        string='System Voltage',
        default=0,
    )

    input_voltage = fields.Float(
        string='Input Voltage',
        default=0,
    )

    last_f0_read = fields.Datetime(
        string='Last System Information Update',
    )

    commands_count = fields.Char(string='Commands count', compute='_compute_counts')
    system_event_count = fields.Char(string='System Events count', compute='_compute_counts')
    user_event_count = fields.Char(string='User events count', compute='_compute_counts')
    readers_count = fields.Char(string='Readers count', compute='_compute_counts')
    doors_count = fields.Char(string='Doors count', compute='_compute_counts')
    alarm_line_count = fields.Char(string='Alarm line count', compute='_compute_counts')


    @api.depends('mode')
    def _compute_controller_mode(self):
        for c in self:
            if c.mode <= 2:
                c.mode_selection = str(c.mode)
                c.mode_selection_4 = '2' # Fake
            else:
                c.mode_selection = '1' # Fake
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
            ctrl.write_controller_mode(int(ctrl.mode_selection_31))

    @api.depends('reader_ids', 'door_ids', 'alarm_line_ids')
    def _compute_counts(self):
        for a in self:
            a.commands_count = self.env['hr.rfid.command'].search_count([('controller_id', '=', a.id)])
            a.system_event_count = self.env['hr.rfid.event.system'].search_count([('controller_id', '=', a.id)])
            a.readers_count = len(a.reader_ids)
            a.doors_count = len(a.door_ids)
            a.alarm_line_count = len(a.alarm_line_ids)
            a.user_event_count = self.env['hr.rfid.event.user'].search_count([('door_id', 'in', [d.id for d in a.door_ids])])

    @api.depends('alarm_lines')
    def _compute_siren_state(self):
        for c in self:
            siren_out = (c.alarm_lines == 1) and 4 or 10
            c.siren_state = c._get_output_state(siren_out)

    def _set_siren_state(self):
        for c in self:
            siren_out = (c.alarm_lines == 1) and 4 or 10
            c.change_output_state(siren_out, int(c.siren_state), 99)

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
            domain = [('door_id', 'in', self.door_ids.mapped('id'))]
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
    def get_default_io_table(self, hw_type, sw_version, mode):
        io_tables = {
            # iCON110
            '6': {
                1: [
                    (734,
                     '0000000000000000000000000000000000000000000000030000000000000300000000000000030000000000000003000000000000000003000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000040463000000000000030000000000000000030000000000000000000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300'),
                ],
                2: [
                    (734,
                     '0000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000000000000000300000000000000000000000000000000000000000000000000000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000046363000000000000030000000000000000030000000000000000000000000000030000000000000003000000000000000000000000000000000000000000000003000000000000000300'),
                ],
            },
            # Turnstile
            '9': {
                1: [
                    (734,
                     '0000000003030303050505050000000000000000000000030000000300000000000000030000000000000003000000000000000000000300000003000000000000000300000000000000030000000000000000000003000000030000000000000003000000000000000300000000000000000000030000000300000000000000030000000000000003000000000000000000000063636363000000000000000000000000000000030000000000000300000000000003000000000000030000000404040401010101040404040000000000000000000000000000000000000000'),
                    (740,
                     '0000000003030303050505050000000000000000000000030000000300000000000000030000000000000003000000000000000000000300000003000000000000000300000000000000030000000000000000000003000000030000000000000003000000000000000300000000000000000000030000000300000000000000030000000000000003000000000000000000000063636363000000000305030500000000000000030000000000000300000000000003000000000000030000000404040401010101040404040000000000000000000000000000000000000000'),
                ]
            },
            # iCON115
            '11': {
                1: [
                    (734,
                     '0000000000000000000000000000000000000000000000030000000000000300000000000000030000000000000003000000000000000003000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000006363000000000000000000000000000000030000000000000000000000000000030000000000000003000000000000000300000000000000030000000000000000000000000000000000'),
                ],
                2: [
                    (734,
                     '0000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000000000000000300000000000000000000000000000000000000000000000000000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000006363000000000000000000000000000000030000000000000000000000000000030000000000000003000000000000000000000000000000000000000000000000000000000000000000'),
                ],
            },
            # iCON50
            '12': {
                1: [
                    (734,
                     '0000000000000003000000000000030000000000000000030000000000000300000000000000000000000000000003000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),
                ],
            },
            # iCON130
            '17': {
                2: [
                    (734,
                     '0000000000000303000005050000000000000000000000030000000300000000000000030000000000000003000000000000000000000003000000030000000000000003000000000000000300000000000000000003000000000300000000000000030000000000000003000000000000000000000300000000030000000000000003000000000000000300000000000000000000006363000000000000000000000000000000030000000000000300000000000000000000000000000000000000010100000303000001010000030300000000000000000000000000000000'),
                ],
                3: [
                    (734,
                     '0000000000030303000505050000000000000000000000030000000300000000000000030000000000000003000000000000000000000003000000030000000000000003000000000000000300000000000000000003000000000300000000000000030000000000000003000000000000000000030000000003000000000000000300000000000000030000000000000000000000636363000000000000000000000000000000030000000000000300000000000003000000000000000000000001010100030303000101010003030300000000000000000000000000000000'),
                ],
                4: [
                    (734,
                     '0000000003030303050505050000000000000000000000030000000300000000000000030000000000000003000000000000000000000300000003000000000000000300000000000000030000000000000000000003000000030000000000000003000000000000000300000000000000000000030000000300000000000000030000000000000003000000000000000000000063636363000000000000000000000000000000030000000000000300000000000003000000000000030000000101010103030303010101010303030300000000000000000000000000000000'),
                ],
            },
        }

        if hw_type not in io_tables or mode not in io_tables[hw_type]:
            return ''

        sw_versions = io_tables[hw_type][mode]
        io_table = ''
        for sw_v, io_t in sw_versions:
            if int(sw_version) > sw_v:
                io_table = io_t
        return io_table

    @api.model
    def update_ctrl_alarm_lines(self):
        ctrl_ids = self.env['hr.rfid.ctrl'].sudo().search([('alarm_lines', '>', 0), ('alarm_line_ids', '=', False)])
        ctrl_ids._setup_alarm_lines()
        return True

    def button_reload_cards(self):
        cmd_env = self.env['hr.rfid.command'].with_user(SUPERUSER_ID)

        cmd_env.create({
            'webstack_id': self.webstack_id.id,
            'controller_id': self.id,
            'cmd': 'DC',
            'cmd_data': '0303',
        })

        cmd_env.create({
            'webstack_id': self.webstack_id.id,
            'controller_id': self.id,
            'cmd': 'DC',
            'cmd_data': '0404',
        })

        for door in self.door_ids:
            self.env['hr.rfid.card.door.rel'].reload_door_rels(door)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Controller cards reload"),
                'message': _("This will take time. For more information check controller's commands"),
                'type': 'success',
                'sticky': False,
            }}

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
            return [int(line[i * 2:i * 2 + 2]) for i in reversed(range(0, 8))]
        else:
            return []

    def _set_io_line(self, line_number: int, line: [int]):
        self.ensure_one()
        if not (0 < line_number < self.io_table_lines + 1):
            raise "Invalid IO Line number"
        self.change_io_table(''.join([f"{line[i]:02d}" for i in reversed(range(0, 8))]), line_number)

    def change_io_table(self, new_io_table, line=0):
        cmd_env = self.env['hr.rfid.command'].with_user(SUPERUSER_ID)
        cmd_data = f"{line:02d}" + new_io_table

        for ctrl in self:
            if ctrl.io_table == new_io_table:
                continue

            if (len(ctrl.io_table) != len(new_io_table) and line == 0) or (line != 0 and len(new_io_table) != 16):
                raise exceptions.ValidationError(
                    'IO table lengths are different, this should never happen????'
                )
            if line == 0:
                ctrl.io_table = new_io_table
                cmd_env.create({
                    'webstack_id': ctrl.webstack_id.id,
                    'controller_id': ctrl.id,
                    'cmd': 'D9',
                    'cmd_data': cmd_data,
                })
            else:
                io_table = self.io_table[:16 * (line - 1)]
                io_table += new_io_table
                io_table += self.io_table[16 * (line - 1) + 16:]
                ctrl.io_table = io_table
                cmd_env.create({
                    'webstack_id': ctrl.webstack_id.id,
                    'controller_id': ctrl.id,
                    'cmd': 'D9',
                    'cmd_data': cmd_data,
                })

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

    def get_ctrl_model_name(self, hw_id):
        tmp = -1
        if hw_id:
            tmp = hw_id
        elif self:
            self.ensure_one()
            tmp = self.hw_version
        for m in HW_TYPES:
            if m[0] == tmp:
                return m[1]
        return _('Unknown')

    def re_read_ctrl_info(self):
        cmd_env = self.env['hr.rfid.command']
        for ctrl in self:
            cmd_env.read_controller_information_cmd(ctrl)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Refresh Controller information"),
                'message': _("This will take time. For more information check controller's commands"),
                'type': 'success',
                'sticky': False,
            }}

    def write(self, vals):
        for ctrl in self:
            old_ext_db = ctrl.external_db
            super(HrRfidController, ctrl).write(vals)
            new_ext_db = ctrl.external_db

            if old_ext_db != new_ext_db:
                ctrl.write_controller_mode(new_ext_db=new_ext_db)

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
        return self.input_states & (2 ** (input_number - 1)) == (2 ** (input_number - 1))

    def _get_output_state(self, output_number):
        self.ensure_one()
        return self.output_states & (2 ** (output_number - 1)) == (2 ** (output_number - 1))

    def _update_output_state(self, output_number, state):
        '''
        Output Number from 1
        State 0 or 1, True or False
        '''
        if state:  # !=0
            if self.output_states & (2 ** (output_number - 1)) != (2 ** (output_number - 1)):
                self.output_states += (2 ** (output_number - 1))
        elif self.output_states & (2 ** (output_number - 1)) == (2 ** (output_number - 1)):
            self.output_states -= (2 ** (output_number - 1))

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

    def update_th(self, sensor_number: int, data_dict: dict):
        '''
        sensor_number:int any number!. system sensor(integrated) number 0
        data_dict: expect {'t':float, 'h':float}
        '''
        for c in self:
            th_id = self.env['hr.rfid.ctrl.th'].search([
                ('controller_id', '=', c.id),
                ('sensor_number', '=', sensor_number),
            ])
            if not th_id:
                th_id = self.env['hr.rfid.ctrl.th'].create([{
                    'name': _('T&H Sensor {} on {}').format(sensor_number, c.name),
                    'controller_id': c.id,
                    'sensor_number': sensor_number
                }])
            new_dict = {}
            if 't' in data_dict:
                new_dict.update({'temperature': data_dict['t']})
                if sensor_number == 0:
                    c.temperature = data_dict['t']
            if 'h' in data_dict:
                new_dict.update({'humidity': data_dict['h']})
                if sensor_number == 0:
                    c.humidity = data_dict['h']
            if new_dict:
                th_id.write(new_dict)

    def decode_door_number_for_relay(self, data):
        self.ensure_one()
        pcs_str = [data[i * 6:i * 6 + 6] for i in range(4)]  # ['000000', '000000', '000000', '000101']
        pcs_int = []
        for pcs in pcs_str:
            pcs_int.append(int(''.join(str(int(pcs[i * 2: i * 2 + 2])) for i in range(3))))
        return int(''.join([str(p) for p in pcs_int]))

    # Commands to controllers
    def _base_command(self, cmd: str, cmd_data: str = None, cmd_dict: dict = None):
        commands = self.env['hr.rfid.command']
        for c in self:
            new_cmd = cmd_dict or {'webstack_id': c.webstack_id.id,
                                   'controller_id': c.id,
                                   'cmd': cmd,
                                   }
            if cmd and not cmd_dict and cmd_data:
                new_cmd.update({'cmd_data': cmd_data})
            commands += self.env['hr.rfid.command'].find_last_wait(new_cmd) or self.env['hr.rfid.command'].with_user(
                SUPERUSER_ID).create([new_cmd])

        return commands

    def change_output_state(self, out_number: int, out_state: int, time: int):
        """
        :param out: 0 to open door, 1 to close door
        :param time: Range: [0, 99]
        """
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

        if self.webstack_id.behind_nat:
            cmd_id = self.env['hr.rfid.command'].sudo().create([{
                'webstack_id': self.webstack_id.id,
                'controller_id': self.id,
                'cmd': 'DB',
                'cmd_data': cmd_data
            }])
        else:
            cmd['cmd']['d'] = cmd_data
            body_js = self.webstack_id.direct_execute(cmd=cmd)
            if body_js['response']['e'] != 0:
                raise exceptions.ValidationError('Error. Controller returned body:\n' + str(body_js))

    def read_controller_information_cmd(self):
        return self._base_command('F0')

    def read_status(self):
        return self._base_command('B3')

    def synchronize_clock_cmd(self):
        return self._base_command('D7')

    def delete_all_cards_cmd(self):
        return self._base_command('DC', '0303')

    def delete_all_events_cmd(self):
        return self._base_command('DC', '0404')

    def read_io_table_cmd(self):
        return self._base_command('F9', '00')

    def read_readers_mode_cmd(self):
        return self._base_command('F6')

    def read_anti_pass_back_mode_cmd(self):
        return self._base_command('FC')

    def read_input_masks_cmd(self):
        return self._base_command('FB')

    def read_outputs_ts_cmd(self):
        return self._base_command('FF')

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

    def write_controller_mode(self, new_mode: int = None, new_ext_db: bool = None):
        if new_mode is not None:
            # TODO Check if mode is being changed, change io table if so
            pass
        if new_mode is None:
            new_mode = self.mode
        if new_ext_db is None:
            new_ext_db = self.external_db
        if new_ext_db is True:
            new_mode = 0x20 + new_mode
        cmd_data = '%02X' % new_mode
        return self._base_command('D5', cmd_data)

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
        self.ensure_one()
        return self.webstack_id.report_sys_ev(description, post_data, self, sys_ev_dict)


class HrRfidCtrlIoTableRow(models.TransientModel):
    _name = 'hr.rfid.ctrl.io.table.row'
    _description = 'Controller IO Table row'

    event_codes = [
        ('1', _("Duress")),
        ('2', _("Duress Error")),
        ('3', _("Reader #1 Card OK")),
        ('4', _("Reader #1 Card Error")),
        ('5', _("Reader #1 TS Error")),
        ('6', _("Reader #1 APB Error")),
        ('7', _("Reader #2 Card OK")),
        ('8', _("Reader #2 Card Error")),
        ('9', _("Reader #2 TS Error")),
        ('10', _("Reader #2 APB Error")),
        ('11', _("Reader #3 Card OK")),
        ('12', _("Reader #3 Card Error")),
        ('13', _("Reader #3 TS Error")),
        ('14', _("Reader #3 APB Error")),
        ('15', _("Reader #4 Card OK")),
        ('16', _("Reader #4 Card Error")),
        ('17', _("Reader #4 TS Error")),
        ('18', _("Reader #4 APB Error")),
        ('19', _("Emergency Input")),
        ('20', _("Arm On Siren")),
        ('21', _("Exit Button 1")),
        ('22', _("Exit Button 2")),
        ('23', _("Exit Button 3")),
        ('24', _("Exit Button 4")),
        ('25', _("Door Overtime")),
        ('26', _("Door Forced Open")),
        ('27', _("On Delay")),
        ('28', _("Off Delay")),
    ]

    event_number = fields.Selection(
        selection=event_codes,
        string='Event Number',
        help='What the outs are set to when this event occurs',
        required=True,
        readonly=True,
    )

    # Range is from 00 to 99
    out8 = fields.Integer(string='Out8', required=True)
    out7 = fields.Integer(string='Out7', required=True)
    out6 = fields.Integer(string='Out6', required=True)
    out5 = fields.Integer(string='Out5', required=True)
    out4 = fields.Integer(string='Out4', required=True)
    out3 = fields.Integer(string='Out3', required=True)
    out2 = fields.Integer(string='Out2', required=True)
    out1 = fields.Integer(string='Out1', required=True)


class HrRfidCtrlIoTableWiz(models.TransientModel):
    _name = 'hr.rfid.ctrl.io.table.wiz'
    _description = 'Controller IO Table Wizard'

    def _default_ctrl(self):
        return self.env['hr.rfid.ctrl'].browse(self._context.get('active_ids'))

    def _generate_io_table(self):
        rows_env = self.env['hr.rfid.ctrl.io.table.row']
        row_len = 8 * 2  # 8 outs, 2 symbols each to display the number
        ctrl = self._default_ctrl()

        if len(ctrl.io_table) % row_len != 0:
            raise exceptions.ValidationError('Controller does now have an input/output table loaded!')

        io_table = ctrl.io_table
        rows = rows_env

        for i in range(0, len(ctrl.io_table), row_len):
            creation_dict = {'event_number': str(int(i / row_len) + 1)}
            for j in range(8, 0, -1):
                index = i + ((8 - j) * 2)
                creation_dict['out' + str(j)] = int(io_table[index:index + 2], 16)
            rows += rows_env.create(creation_dict)

        return rows

    def _default_outs(self):
        return self._default_ctrl().outputs

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        default=_default_ctrl,
        required=True
    )

    io_row_ids = fields.Many2many(
        'hr.rfid.ctrl.io.table.row',
        string='IO Table',
        default=_generate_io_table,
    )

    outs = fields.Integer(
        default=_default_outs,
    )

    def save_table(self):
        self.ensure_one()

        new_io_table = ''

        for row in self.io_row_ids:
            outs = [row.out8, row.out7, row.out6, row.out5, row.out4, row.out3, row.out2, row.out1]
            for out in outs:
                if out < 0 or out > 99:
                    raise exceptions.ValidationError(
                        _('%d is not a valid number for the io table. Valid values range from 0 to 99') % out
                    )
                new_io_table += '%02X' % out

        self.controller_id.change_io_table(new_io_table)


class HrRfidTimeSchedule(models.Model):
    _name = 'hr.rfid.time.schedule'
    _inherit = ['mail.thread']
    _description = 'Time Schedule'

    name = fields.Char(
        string='Name',
        help='Label for the time schedule',
        required=True,
        tracking=True,
    )

    number = fields.Integer(
        string='TS Number',
        required=True,
        readonly=True,
    )

    access_group_door_ids = fields.One2many(
        'hr.rfid.access.group.door.rel',
        'time_schedule_id',
        string='Access Group/Door Combinations',
        help='Which doors use this time schedule in which access group',
    )

    def unlink(self):
        raise exceptions.ValidationError(_('Cannot delete time schedules!'))
