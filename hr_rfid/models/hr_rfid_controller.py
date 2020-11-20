from odoo import fields, models, api, exceptions, _
from ..wizards.helpers import create_and_ret_d_box, return_wiz_form_view
import base64
import json
import http.client
import socket
import logging

_logger = logging.getLogger(__name__)


class HrRfidCtrlIoTableRow(models.TransientModel):
    _name = 'hr.rfid.ctrl.io.table.row'
    _description = 'Controller IO Table row'

    event_codes = [
        ('1', "Duress"),
        ('2', "Duress Error"),
        ('3', "Reader #1 Card OK"),
        ('4', "Reader #1 Card Error"),
        ('5', "Reader #1 TS Error"),
        ('6', "Reader #1 APB Error"),
        ('7', "Reader #2 Card OK"),
        ('8', "Reader #2 Card Error"),
        ('9', "Reader #2 TS Error"),
        ('10', "Reader #2 APB Error"),
        ('11', "Reader #3 Card OK"),
        ('12', "Reader #3 Card Error"),
        ('13', "Reader #3 TS Error"),
        ('14', "Reader #3 APB Error"),
        ('15', "Reader #4 Card OK"),
        ('16', "Reader #4 Card Error"),
        ('17', "Reader #4 TS Error"),
        ('18', "Reader #4 APB Error"),
        ('19', "Emergency Input"),
        ('20', "Arm On Siren"),
        ('21', "Exit Button 1"),
        ('22', "Exit Button 2"),
        ('23', "Exit Button 3"),
        ('24', "Exit Button 4"),
        ('25', "Door Overtime"),
        ('26', "Door Forced Open"),
        ('27', "On Delay"),
        ('28', "Off Delay"),
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
            raise exceptions.ValidationError(_('Controller does now have an input/output table loaded!'))

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

    @api.multi
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


class HrRfidController(models.Model):
    _name = 'hr.rfid.ctrl'
    _inherit = ['mail.thread']
    _description = 'Controller'
    _sql_constraints = [('rfid_controller_unique', 'unique(serial_number)',
                         'Serial numbers must be unique!')]

    hw_types = [('1', 'iCON200'), ('2', 'iCON150'), ('3', 'iCON150'), ('4', 'iCON140'),
                ('5', 'iCON120'), ('6', 'iCON110'), ('7', 'iCON160'), ('8', 'iCON170'),
                ('9', 'Turnstile'), ('10', 'iCON180'), ('11', 'iCON115'), ('12', 'iCON50'),
                ('13', 'FireControl'), ('14', 'FireControl'), ('18', 'FireControl'),
                ('19', 'FireControl'), ('15', 'TempRH'), ('16', 'Vending'), ('17', 'iCON130'),
                ('20', 'AlarmControl'), ('21', 'AlarmControl'), ('22', 'AlarmControl'),
                ('23', 'AlarmControl'), ('26', 'AlarmControl'), ('27', 'AlarmControl'),
                ('28', 'AlarmControl'), ('29', 'AlarmControl'), ('24', 'iTemp'), ('25', 'iGas'),
                ('30', 'RelayControl110'), ('31', 'RelayControl150'), ('32', 'RelayControl'),
                ('33', 'RelayControl'), ('34', 'RelayControl'), ('35', 'RelayControl'),
                ('36', 'RelayControl'), ('37', 'RelayControl'), ('38', 'RelayControl'),
                ('39', 'RelayControl'), ('40', 'MFReader'), ('41', 'MFReader'), ('42', 'MFReader'),
                ('43', 'MFReader'), ('44', 'MFReader'), ('45', 'MFReader'), ('46', 'MFReader'),
                ('47', 'MFReader'), ('48', 'MFReader'), ('49', 'MFReader'), ('50', 'iMotor')]

    name = fields.Char(
        string='Name',
        help='Label to easily distinguish the controller',
        required=True,
        index=True,
        track_visibility='onchange',
    )

    ctrl_id = fields.Integer(
        string='ID',
        help='A number to distinguish the controller from others on the same module',
        index=True,
    )

    hw_version = fields.Selection(
        selection=hw_types,
        string='Hardware Type',
        help='Type of the controller',
    )

    serial_number = fields.Char(
        string='Serial',
        help='Serial number of the controller',
        limit=4,
    )

    sw_version = fields.Char(
        string='Version',
        help='The version of the software on the controller',
        limit=3,
    )

    inputs = fields.Integer(
        string='Inputs',
        help='Mask describing the inputs of the controller',
    )

    outputs = fields.Integer(
        string='Outputs',
        help='Mask detailing the outputs of the controller',
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
    )

    mode = fields.Integer(
        string='Controller Mode',
        help='The mode of the controller',
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
        'hr.rfid.door',
        'controller_id',
        string='Controlled Doors',
        help='Doors that belong to this controller'
    )

    reader_ids = fields.One2many(
        'hr.rfid.reader',
        'controller_id',
        string='Controlled Readers',
        help='Readers that belong to this controller',
    )

    system_event_ids = fields.One2many(
        'hr.rfid.event.system',
        'controller_id',
        string='Errors',
        help='Errors received from the controller',
    )

    command_ids = fields.One2many(
        'hr.rfid.command',
        'controller_id',
        string='Commands',
        help='Commands that have been sent to this controller',
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

    @api.one
    def button_reload_cards(self):
        cmd_env = self.env['hr.rfid.command'].sudo()

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

    @api.multi
    def change_io_table(self, new_io_table):
        cmd_env = self.env['hr.rfid.command'].sudo()
        cmd_data = '00' + new_io_table

        for ctrl in self:
            if ctrl.io_table == new_io_table:
                continue

            if len(ctrl.io_table) != len(new_io_table):
                raise exceptions.ValidationError(_('Io table lengths are different, this should never happen????'))

            ctrl.io_table = new_io_table
            cmd_env.create({
                'webstack_id': ctrl.webstack_id.id,
                'controller_id': ctrl.id,
                'cmd': 'D9',
                'cmd_data': cmd_data,
            })

    @api.multi
    def is_relay_ctrl(self):
        self.ensure_one()
        return self.hw_version_is_for_relay_ctrl(self.hw_version)

    @api.model
    def hw_version_is_for_relay_ctrl(self, hw_version):
        return hw_version in ['30', '31', '32']

    @api.multi
    def re_read_ctrl_info(self):
        cmd_env = self.env['hr.rfid.command']
        for ctrl in self:
            cmd_env.read_controller_information_cmd(ctrl)

    @api.multi
    def write(self, vals):
        # TODO Check if mode is being changed, change io table if so
        cmd_env = self.env['hr.rfid.command'].sudo()
        for ctrl in self:
            old_ext_db = ctrl.external_db
            super(HrRfidController, ctrl).write(vals)
            new_ext_db = ctrl.external_db

            if old_ext_db != new_ext_db:
                cmd_dict = {
                    'webstack_id': ctrl.webstack_id.id,
                    'controller_id': ctrl.id,
                    'cmd': 'D5',
                }
                if new_ext_db is True:
                    new_mode = 0x20 + ctrl.mode
                    cmd_dict['cmd_data'] = '%02X' % new_mode
                else:
                    cmd_dict['cmd_data'] = '%02X' % ctrl.mode
                cmd_env.create(cmd_dict)


class HrRfidDoorOpenCloseWiz(models.TransientModel):
    _name = 'hr.rfid.door.open.close.wiz'
    _description = 'Open or close door'

    def _default_doors(self):
        return self.env['hr.rfid.door'].browse(self._context.get('active_ids'))

    doors = fields.Many2many(
        'hr.rfid.door',
        string='Doors to open/close',
        required=True,
        default=_default_doors,
    )

    time = fields.Integer(
        string='Time',
        help='Amount of time (in seconds) the doors will stay open or closed. 0 for infinity.',
        default=3,
        required=True,
    )

    @api.multi
    def open_doors(self):
        for door in self.doors:
            door.open_close_door(out=1, time=self.time)
        return create_and_ret_d_box(self.env, 'Doors opened', 'Doors successfully opened')

    @api.multi
    def close_doors(self):
        for door in self.doors:
            door.open_close_door(out=0, time=self.time)
        return create_and_ret_d_box(self.env, 'Door closed', 'Doors successfully closed')


class HrRfidDoor(models.Model):
    _name = 'hr.rfid.door'
    _description = 'Door'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Name',
        help='A label to easily differentiate doors',
        required=True,
        intex=True,
        track_visibility='onchange',
    )

    number = fields.Integer(
        string='Number',
        help='Number of the door in the controller',
        required=True,
        index=True,
    )

    card_type = fields.Many2one(
        'hr.rfid.card.type',
        string='Card type',
        help='Only cards of this type this door will open to',
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_card_type_def').id,
        ondelete='set null',
        track_visibility='onchange',
    )

    apb_mode = fields.Boolean(
        string='APB Mode',
        default=False,
        track_visibility='onchange',
    )

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        string='Controller',
        help='Controller that manages the door',
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    access_group_ids = fields.One2many(
        'hr.rfid.access.group.door.rel',
        'door_id',
        string='Door Access Groups',
        help='The access groups this door is a part of',
    )

    user_event_ids = fields.One2many(
        'hr.rfid.event.user',
        'door_id',
        string='Events',
        help='Events concerning this door',
    )

    reader_ids = fields.Many2many(
        'hr.rfid.reader',
        'hr_rfid_reader_door_rel',
        'door_id',
        'reader_id',
        string='Readers',
        help='Readers that open this door',
    )

    card_rel_ids = fields.One2many(
        'hr.rfid.card.door.rel',
        'door_id',
        string='Cards',
        help='Cards that have access to this door',
    )

    zone_ids = fields.Many2many(
        'hr.rfid.zone',
        'hr_rfid_zone_door_rel',
        'door_id',
        'zone_id',
        string='Zones',
        help='Zones containing this door',
    )

    def get_potential_cards(self, access_groups=None):
        """
        Returns a list of tuples (card, time_schedule) for which the card potentially has access to this door
        """
        if access_groups is None:
            acc_gr_rels = self.access_group_ids
        else:
            acc_gr_rels = self.env['hr.rfid.access.group.door.rel'].search([
                ('id', 'in', self.access_group_ids.ids),
                ('access_group_id', 'in', access_groups.ids),
            ])
        ret = []
        for rel in acc_gr_rels:
            ts_id = rel.time_schedule_id
            acc_gr = rel.access_group_id
            employees = acc_gr.mapped('all_employee_ids').mapped('employee_id')
            contacts = acc_gr.mapped('all_contact_ids').mapped('contact_id')
            cards = employees.mapped('hr_rfid_card_ids') + contacts.mapped('hr_rfid_card_ids')
            for card in cards:
                ret.append((card, ts_id))
        return ret

    @api.multi
    def open_door(self):
        self.ensure_one()
        return self.open_close_door(1, 3)

    @api.multi
    def close_door(self):
        self.ensure_one()
        return self.open_close_door(0, 3)

    @api.multi
    def open_close_door(self, out: int, time: int):
        self.ensure_one()

        if self.controller_id.webstack_id.behind_nat is True:
            return self.create_door_out_cmd(out, time)
        else:
            return self.change_door_out(out, time)

    @api.multi
    def create_door_out_cmd(self, out: int, time: int):
        self.ensure_one()
        cmd_env = self.env['hr.rfid.command']
        ctrl = self.controller_id
        cmd_dict = {
            'webstack_id': ctrl.webstack_id.id,
            'controller_id': ctrl.id,
            'cmd': 'DB',
        }
        if not ctrl.is_relay_ctrl():
            cmd_dict['cmd_data'] = '%02d%02d%02d' % (self.number, out, time),
        else:
            if out == 0:
                return create_and_ret_d_box(self.env, _('Cannot close a relay door.'),
                                            _('Relay doors cannot be closed.'))
            cmd_dict['cmd_data'] = ('1F%02X' % self.reader_ids[0].number) + self.create_rights_data()

        cmd_env.create([cmd_dict])
        self.log_door_change(out, time, cmd=True)
        return create_and_ret_d_box(
            self.env,
            _('Command creation successful'),
            _('Because the webstack is behind NAT, we have to wait for the webstack to call us, so we created '
              'a command. The door will open/close as soon as possible.')
        )

    @api.multi
    def create_rights_data(self):
        self.ensure_one()
        ctrl = self.controller_id
        if not ctrl.is_relay_ctrl():
            data = 1 << (self.reader_ids.number - 1)
        else:
            if ctrl.mode == 1:
                data = 1 << (self.number - 1)
            elif ctrl.mode == 2:
                data = 1 << (self.number - 1)
                if self.reader_ids.number == 2:
                    data *= 0x10000
            elif ctrl.mode == 3:
                data = self.number
            else:
                raise exceptions.ValidationError(_('Controller %s has mode=%d, which is not supported!')
                                                 % (ctrl.name, ctrl.mode))

        return self.create_rights_int_to_str(data)

    @api.model
    def create_rights_int_to_str(self, data):
        ctrl = self.controller_id
        if not ctrl.is_relay_ctrl():
            cmd_data = '{:02X}'.format(data)
        else:
            cmd_data = '%03d%03d%03d%03d' % (
                (data >> (3 * 8)) & 0xFF,
                (data >> (2 * 8)) & 0xFF,
                (data >> (1 * 8)) & 0xFF,
                (data >> (0 * 8)) & 0xFF,
            )
            cmd_data = ''.join(list('0' + ch for ch in cmd_data))
        return cmd_data

    @api.multi
    def change_door_out(self, out: int, time: int):
        """
        :param out: 0 to open door, 1 to close door
        :param time: Range: [0, 99]
        """
        self.ensure_one()
        self.log_door_change(out, time)

        ws = self.controller_id.webstack_id
        if ws.module_username is False:
            username = ''
        else:
            username = str(ws.module_username)

        if ws.module_password is False:
            password = ''
        else:
            password = str(ws.module_password)

        auth = base64.b64encode((username + ':' + password).encode())
        auth = auth.decode()
        headers = {'content-type': 'application/json', 'Authorization': 'Basic ' + str(auth)}
        cmd = {
            'cmd': {
                'id': self.controller_id.ctrl_id,
                'c': 'DB',
            }
        }

        if self.controller_id.is_relay_ctrl():
            if out == 0:
                return create_and_ret_d_box(self.env, _('Cannot close a relay door.'),
                                            _('Relay doors cannot be closed.'))
            cmd['cmd']['d'] = ('1F%02X' % self.reader_ids[0].number) + self.create_rights_data()
        else:
            cmd['cmd']['d'] = '%02d%02d%02d' % (self.number, out, time)

        cmd = json.dumps(cmd)

        host = str(ws.last_ip)
        try:
            conn = http.client.HTTPConnection(str(host), 80, timeout=2)
            conn.request('POST', '/sdk/cmd.json', cmd, headers)
            response = conn.getresponse()
            code = response.getcode()
            body = response.read()
            conn.close()
            if code != 200:
                raise exceptions.ValidationError('While trying to send the command to the module, '
                                                 'it returned code ' + str(code) + ' with body:\n'
                                                 + body.decode())

            body_js = json.loads(body.decode())
            if body_js['response']['e'] != 0:
                raise exceptions.ValidationError('Error. Controller returned body:\n' + str(body))
        except socket.timeout:
            raise exceptions.ValidationError('Could not connect to the module. '
                                             "Check if it is turned on or if it's on a different ip.")
        except (socket.error, socket.gaierror, socket.herror) as e:
            raise exceptions.ValidationError('Error while trying to connect to the module.'
                                             ' Information:\n' + str(e))

        return create_and_ret_d_box(self.env, _('Door successfully opened/closed'),
                                    _('Door will remain opened/closed for %d seconds.') % time)

    @api.multi
    def log_door_change(self, action: int, time: int, cmd: bool = False):
        """
        :param action: 1 for door open, 0 for door close
        :param time: Range: [0, 99]
        :param cmd: If the command was created instead of
        """
        self.ensure_one()
        if time > 0:
            if cmd is False:
                if action == 1:
                    self.message_post(body=_('Opened the door for %d seconds.') % time)
                else:
                    self.message_post(body=_('Closed the door for %d seconds.') % time)
            else:
                if action == 1:
                    self.message_post(body=_('Created a command to open the door for %d seconds.') % time)
                else:
                    self.message_post(body=_('Created a command to close the door for %d seconds.') % time)
        else:
            if cmd is False:
                if action == 1:
                    self.message_post(body=_('Opened the door.') % time)
                else:
                    self.message_post(body=_('Closed the door.') % time)
            else:
                if action == 1:
                    self.message_post(body=_('Created a command to open the door.') % time)
                else:
                    self.message_post(body=_('Created a command to close the door.') % time)

    @api.multi
    @api.constrains('apb_mode')
    def _check_apb_mode(self):
        for door in self:
            if door.apb_mode is True and len(door.reader_ids) < 2:
                raise exceptions.ValidationError('Cannot activate APB Mode for a door if it has less than 2 readers')

    @api.multi
    def write(self, vals):
        cmd_env = self.env['hr.rfid.command']
        rel_env = self.env['hr.rfid.card.door.rel']
        for door in self:
            old_card_type = door.card_type
            old_apb_mode = door.apb_mode

            super(HrRfidDoor, door).write(vals)

            if old_card_type != door.card_type:
                rel_env.update_door_rels(door)

            if old_apb_mode != door.apb_mode:
                cmd_data = 0
                for door2 in door.controller_id.door_ids:
                    if door2.apb_mode and len(door2.reader_ids) > 1:
                        cmd_data += door2.number
                cmd_dict = {
                    'webstack_id': door.controller_id.webstack_id.id,
                    'controller_id': door.controller_id.id,
                    'cmd': 'DE',
                    'cmd_data': '%02d' % cmd_data,
                }
                cmd_env.create(cmd_dict)

        return True


class HrRfidTimeSchedule(models.Model):
    _name = 'hr.rfid.time.schedule'
    _inherit = ['mail.thread']
    _description = 'Time Schedule'

    name = fields.Char(
        string='Name',
        help='Label for the time schedule',
        required=True,
        track_visibility='onchange',
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

    @api.multi
    def unlink(self):
        raise exceptions.ValidationError('Cannot delete time schedules!')


class HrRfidReader(models.Model):
    _name = 'hr.rfid.reader'
    _inherit = ['mail.thread']
    _description = 'Reader'

    reader_types = [
        ('0', 'In'),
        ('1', 'Out'),
    ]

    reader_modes = [
        ('01', 'Card Only'),
        ('02', 'Card and Pin'),
        ('03', 'Card and Workcode'),
        ('04', 'Card or Pin'),
    ]

    name = fields.Char(
        string='Reader name',
        help='Label to differentiate readers',
        default='Reader',
        track_visibility='onchange',
    )

    number = fields.Integer(
        string='Number',
        help='Number of the reader on the controller',
        index=True,
    )

    # TODO Rename to just 'type'
    reader_type = fields.Selection(
        selection=reader_types,
        string='Reader type',
        help='Type of the reader',
        required=True,
        default='0',
    )

    mode = fields.Selection(
        selection=reader_modes,
        string='Reader mode',
        help='Mode of the reader',
        default='01',
    )

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        string='Controller',
        help='Controller that manages the reader',
        required=True,
        ondelete='cascade',
    )

    user_event_ids = fields.One2many(
        'hr.rfid.event.user',
        'reader_id',
        string='Events',
        help='Events concerning this reader',
    )

    door_ids = fields.Many2many(
        'hr.rfid.door',
        'hr_rfid_reader_door_rel',
        'reader_id',
        'door_id',
        string='Doors',
        help='Doors the reader opens',
        ondelete='cascade',
    )

    door_id = fields.Many2one(
        'hr.rfid.door',
        string='Door',
        compute='_compute_reader_door',
        inverse='_inverse_reader_door',
    )

    @api.multi
    def _compute_reader_name(self):
        for record in self:
            record.name = record.door_id.name + ' ' + \
                          self.reader_types[int(record.reader_type)][1] + \
                          ' Reader'

    @api.multi
    @api.depends('door_ids')
    def _compute_reader_door(self):
        for reader in self:
            if not reader.controller_id.is_relay_ctrl() and len(reader.door_ids) == 1:
                reader.door_id = reader.door_ids

    @api.multi
    def _inverse_reader_door(self):
        for reader in self:
            reader.door_ids = reader.door_id

    @api.multi
    def write(self, vals):
        if 'mode' not in vals or ('no_d6_cmd' in vals and vals['no_d6_cmd'] is True):
            if 'no_d6_cmd' in vals:
                vals.pop('no_d6_cmd')
            super(HrRfidReader, self).write(vals)
            return

        for reader in self:
            if 'no_d6_cmd' in vals:
                vals.pop('no_d6_cmd')
            old_mode = reader.mode
            super(HrRfidReader, reader).write(vals)
            new_mode = reader.mode

            if old_mode != new_mode:
                ctrl = reader.controller_id
                cmd_env = self.env['hr.rfid.command'].sudo()

                data = ''
                for r in ctrl.reader_ids:
                    data = data + str(r.mode) + '0100'

                cmd_env.create({
                    'webstack_id': ctrl.webstack_id.id,
                    'controller_id': ctrl.id,
                    'cmd': 'D6',
                    'cmd_data': data,
                })