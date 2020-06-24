# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from datetime import datetime, timedelta
from ..wizards.helpers import create_and_ret_d_box, return_wiz_form_view
import socket
import http.client
import json
import base64
import pytz

# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]
def _tz_get(self):
    return _tzs


class HrRfidWebstackDiscovery(models.TransientModel):
    _name = 'hr.rfid.webstack.discovery'
    _description = 'Webstack discovery'

    found_webstacks = fields.Many2many(
        comodel_name='hr.rfid.webstack',
        relation='hr_rfid_webstack_discovery_all',
        column1='wiz',
        column2='ws',
        string='Found modules',
        readonly=True,
        help='Modules that were just found during the discovery process',
    )

    setup_and_set_to_active = fields.Many2many(
        comodel_name='hr.rfid.webstack',
        relation='hr_rfid_webstack_discovery_set',
        column1='wiz',
        column2='ws',
        string='Setup and activate',
        help='Modules to automatically setup for the odoo and activate',
    )

    state = fields.Selection(
        [ ('pre_discovery', 'pre_discovery'), ('post_discovery', 'post_discovery') ],
        default='pre_discovery'
    )

    def discover(self):
        self.ensure_one()
        # TODO get list of stored webstack serials
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_sock.bind(("", 30303))

        send_msg = b'Discovery:'
        res = udp_sock.sendto(send_msg, ('<broadcast>', 30303))
        if res is False:
            udp_sock.close()
            return

        added_sn=list()
        ws_env = self.env['hr.rfid.webstack']
        for rec in ws_env.search([('|'),('active','=',True), ('active', '=', False)]):
            added_sn.append(rec.serial)
        while True:
            udp_sock.settimeout(0.5)
            try:
                data, addr = udp_sock.recvfrom(1024)
                data = data.decode().split('\n')[:-1]
                data = list(map(str.strip, data))
                if (len(data) == 0) or (len(data) > 100) or (data[4] in added_sn):
                    continue
                print(data[4])
                # if data[4] in added_sn:
                #     continue
                # if len(ws_env.search([('serial', '=', data[4])])) > 0:
                #     continue
                module = {
                    'last_ip':    addr[0],
                    'name':       data[0],
                    'version':    data[3],
                    'hw_version': data[2],
                    'serial':     data[4],
                    'behind_nat': False,
                    'available': 'u',
                }
                env = ws_env.sudo()

                module = env.create(module)
                added_sn.append(data[4])
                self.found_webstacks += module
                module.action_check_if_ws_available()

                # try:
                #     module.action_check_if_ws_available()
                # except exceptions.ValidationError as __:
                #     pass
            except socket.timeout:
                break


        udp_sock.close()
        self.write({ 'state': 'post_discovery' })
        return return_wiz_form_view(self._name, self.id)

    def setup_modules(self):
        self.ensure_one()
        for ws in self.setup_and_set_to_active:
            ws.action_set_webstack_settings()
            ws.action_set_active()

        self.get_controllers()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def get_controllers(self):
        self.ensure_one()

        ctrl_env = self.env['hr.rfid.ctrl']

        for ws in self.setup_and_set_to_active:
            host = str(ws.last_ip)
            try:
                conn = http.client.HTTPConnection(host, 80, timeout=2)
                conn.request('GET', '/config.json')
                response = conn.getresponse()
                code = response.getcode()
                body = response.read()
                conn.close()
                if code != 200:
                    raise exceptions.ValidationError('Webstack sent us http code {}'
                                                     ' when 200 was expected.'.format(code))
                js = json.loads(body.decode())
                controllers = js['sdk']['devFound']

                if type(controllers) != type(int(0)):
                    raise exceptions.ValidationError('Webstack gave us bad data when requesting /config.json')

                for dev in range(controllers):
                    conn = http.client.HTTPConnection(host, 80, timeout=2)
                    conn.request('GET', '/sdk/status.json?dev=' + str(dev))
                    response = conn.getresponse()
                    code = response.getcode()
                    body = response.read()
                    conn.close()

                    if code != 200:
                        raise exceptions.ValidationError('Webstack sent us http code {} when 200 was expected'
                                                         ' while requesting /sdk/details.json?dev={}'
                                                         .format(code, dev))

                    ctrl_js = json.loads(body.decode())
                    controller = ctrl_env.create({
                        'name': 'Controller',
                        'ctrl_id': ctrl_js['dev']['devID'],
                        'webstack_id': ws.id,
                    })
                    self.env['hr.rfid.command'].read_controller_information_cmd(controller)
            except socket.timeout:
                raise exceptions.ValidationError('Could not connect to the webstack at ' + host)
            except(socket.error, socket.gaierror, socket.herror) as e:
                raise exceptions.ValidationError('Unexpected error:\n' + str(e))
            except KeyError as __:
                raise exceptions.ValidationError('Information returned by the webstack at '
                                                 + host + ' invalid')


class HrRfidWebstackManualCreate(models.TransientModel):
    _name = 'hr.rfid.webstack.manual.create'
    _description = 'Webstack Manual Creation'

    webstack_name = fields.Char(
        string='Module Name',
        required=True,
    )

    webstack_address = fields.Char(
        string='Webstack Address',
        required=True,
    )

    def create_webstack(self):
        self.env['hr.rfid.webstack'].create({
            'name': self.webstack_name,
            'last_ip': self.webstack_address,
        }).action_check_if_ws_available()


class HrRfidWebstack(models.Model):
    _name = 'hr.rfid.webstack'
    _inherit = ['mail.thread']
    _description = 'Module'

    name = fields.Char(
        string='Name',
        help='A label to easily differentiate modules',
        required=True,
        index=True,
        track_visibility='onchange',
    )

    tz = fields.Selection(
        _tz_get,
        string='Timezone',
        default=lambda self: self._context.get('tz'),
        help='If not set, will assume GMT',
    )

    tz_offset = fields.Char(
        string='Timezone offset',
        compute='_compute_tz_offset',
    )

    serial = fields.Char(
        string='Serial number',
        help='Unique number to differentiate all modules',
        limit=6,
        index=True,
        readonly=True,
    )

    key = fields.Char(
        string='Key',
        limit=4,
        index=True,
        default='0000',
        track_visibility='onchange',
    )

    active = fields.Boolean(
        string='Active',
        help='Will accept events from module if true',
        default=False,
        track_visibility='onchange',
    )

    version = fields.Char(
        string='Version',
        help='Software version of the module',
        limit=6,
    )

    hw_version = fields.Char(
        string='Hardware Version',
        help='Hardware version of the module',
        limit=6,
    )

    behind_nat = fields.Boolean(
        string='Behind NAT',
        help='Whether we can create a direct connection to the module or not',
        required=True,
        default=True,
    )

    last_ip = fields.Char(
        string='Last IP',
        help='Last IP the module connected from',
        limit=26,
    )

    updated_at = fields.Datetime(
        string='Last Update',
        help='The last date we received an event from the module',
    )

    controllers = fields.One2many(
        'hr.rfid.ctrl',
        'webstack_id',
        string='Controllers',
        help='Controllers that this WebStack manages'
    )

    system_event_ids = fields.One2many(
        'hr.rfid.event.system',
        'webstack_id',
        string='Errors',
        help='Errors that we have received from the module'
    )

    command_ids = fields.One2many(
        'hr.rfid.command',
        'webstack_id',
        string='Commands',
        help='Commands that have been or are in queue to send to this module.',
    )

    http_link = fields.Char(
        compute='_compute_http_link'
    )

    module_username = fields.Selection(
        selection=[ ('admin', 'Admin'), ('sdk', 'SDK') ],
        string='Module Username',
        help='Username for the admin account for the module',
        default='admin',
    )

    module_password = fields.Char(
        string='Module Password',
        help='Password for the admin account for the module',
        default='',
    )

    available = fields.Selection(
        selection=[ ('u', 'Unavailable'), ('a', 'Available') ],
        string='Available?',
        help='Whether the module was available the last time Odoo tried to connect to it.',
        default='u',
    )

    last_update = fields.Boolean(compute='_last_update_calculate')

    _sql_constraints = [ ('rfid_webstack_serial_unique', 'unique(serial)',
                          'Serial number for webstacks must be unique!') ]

    @api.depends('updated_at')
    def _last_update_calculate(self):
        for r in self:
            if not r.updated_at:
                r.last_update = False
                continue
            ten_min_dalay = datetime.now() - timedelta(minutes=10)
            r.last_update = True if r.updated_at < ten_min_dalay else False
            print(r.last_update)



    def toggle_ws_active(self):
        for rec in self:
            rec.active = not rec.active

    def action_set_active(self):
        self.active = True

    def action_set_inactive(self):
        self.active = False

    def action_set_webstack_settings(self):
        odoo_url = str(self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
        splits = odoo_url.split(':')
        odoo_url = splits[1][2:]
        if len(splits) == 3:
            odoo_port = int(splits[2], 10)
        else:
            odoo_port = 80
        odoo_url += '/hr/rfid/event'

        if self.module_username is False:
            username = ''
        else:
            username = str(self.module_username)

        if self.module_password is False:
            password = ''
        else:
            password = str(self.module_password)

        auth = base64.b64encode((username + ':' + password).encode())
        auth = auth.decode()
        req_headers = { "content-type": "application/json", "Authorization": "Basic " + str(auth) }
        host = str(self.last_ip)
        js_uart_conf = json.dumps([
            {
                "br": 9600,
                "db": 3,
                "fc": 0,
                "ft": 122,
                "port": 0,
                "pr": 0,
                "rt": False,
                "sb": 1,
                "usage": 0
            }, {
                "br": 9600,
                "db": 3,
                "fc": 0,
                "ft": 122,
                "port": 2,
                "pr": 0,
                "rt": False,
                "sb": 1,
                "usage": 1
            }
        ])

        config_params = 'sdk=1&stsd=1&sdts=1&stsu=' + odoo_url + '&prt=' \
                        + str(odoo_port) + '&hb=1&thb=60&br=1&odoo=1'
        try:
            if self.hw_version != '50.1':
                conn = http.client.HTTPConnection(str(host), 80, timeout=2)
                conn.request("POST", "/protect/uart/conf", js_uart_conf, req_headers)
                response = conn.getresponse()
                conn.close()
                code = response.getcode()
                body = response.read()
                if code != 200:
                    raise exceptions.ValidationError('While trying to setup /protect/uart/conf the module '
                                                     'returned code ' + str(code) + ' with body:\n' +
                                                     body.decode())

            conn = http.client.HTTPConnection(str(host), 80, timeout=2)
            conn.request("POST", "/protect/config.htm", config_params, req_headers)
            response = conn.getresponse()
            conn.close()
            code = response.getcode()
            body = response.read()
            if code != 200:
                raise exceptions.ValidationError('While trying to setup /protect/config.htm the module '
                                                 'returned code ' + str(code) + ' with body:\n' +
                                                 body.decode())
        except socket.timeout:
            raise exceptions.ValidationError('Could not connect to the module. '
                                             "Check if it is turned on or if it's on a different ip.")
        except (socket.error, socket.gaierror, socket.herror) as e:
            raise exceptions.ValidationError('Error while trying to connect to the module.'
                                             ' Information:\n' + str(e))

    def action_check_if_ws_available(self):
        host = str(self.last_ip)
        try:
            conn = http.client.HTTPConnection(host, 80, timeout=2)
            conn.request('GET', '/config.json')
            response = conn.getresponse()
            code = response.getcode()
            body = response.read()
            conn.close()
            if code != 200:
                raise exceptions.ValidationError('Webstack sent us http code {}'
                                                 ' when 200 was expected.'.format(code))

            js = json.loads(body.decode())
            module = {
                'version': js['sdk']['sdkVersion'],
                'hw_version': js['sdk']['sdkHardware'],
                'serial': js['convertor'],
                'available': 'a',
            }
            self.write(module)
        except socket.timeout:
            raise exceptions.ValidationError('Could not connect to the webstack')
        except(socket.error, socket.gaierror, socket.herror) as e:
            raise exceptions.ValidationError('Unexpected error:\n' + str(e))
        except KeyError as __:
            raise exceptions.ValidationError('Information returned by the webstack invalid')

    @api.depends('tz')
    def _compute_tz_offset(self):
        for user in self:
            user.tz_offset = datetime.now(pytz.timezone(user.tz or 'GMT')).strftime('%z')

    def _compute_http_link(self):
        for record in self:
            if record.last_ip != '' and record.last_ip is not False:
                link = 'http://' + record.last_ip + '/'
                record.http_link = link
            else:
                record.http_link = ''

    @api.model
    def _deconfirm_webstack(self, ws):
        ws.available = 'u'

    @api.model
    def _confirm_webstack(self, ws):
        ws.available = 'c'

    def write(self, vals):
        if 'tz' not in vals:
            return super(HrRfidWebstack, self).write(vals)

        commands_env = self.env['hr.rfid.command']

        for ws in self:
            old_tz = ws.tz
            super(HrRfidWebstack, ws).write(vals)
            new_tz = ws.tz

            if old_tz != new_tz:
                for ctrl in ws.controllers:
                    commands_env.create([{
                        'webstack_id': ctrl.webstack_id.id,
                        'controller_id': ctrl.id,
                        'cmd': 'D7',
                    }])


class HrRfidCtrlIoTableRow(models.TransientModel):
    _name = 'hr.rfid.ctrl.io.table.row'
    _description = 'Controller IO Table row'

    event_codes = [
        ('1' , "Duress"),
        ('2' , "Duress Error"),
        ('3' , "Reader #1 Card OK"),
        ('4' , "Reader #1 Card Error"),
        ('5' , "Reader #1 TS Error"),
        ('6' , "Reader #1 APB Error"),
        ('7' , "Reader #2 Card OK"),
        ('8' , "Reader #2 Card Error"),
        ('9' , "Reader #2 TS Error"),
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
            raise exceptions.ValidationError('Controller does now have an input/output table loaded!')

        io_table = ctrl.io_table
        rows = rows_env

        for i in range(0, len(ctrl.io_table), row_len):
            creation_dict = { 'event_number': str(int(i / row_len) + 1) }
            for j in range(8, 0, -1):
                index = i + ((8 - j) * 2)
                creation_dict['out' + str(j)] = int(io_table[index:index+2], 16)
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
            outs = [ row.out8, row.out7, row.out6, row.out5, row.out4, row.out3, row.out2, row.out1 ]
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
    _sql_constraints = [ ('rfid_controller_unique', 'unique(serial_number)',
                          'Serial numbers must be unique!') ]

    hw_types = [ ('1', 'iCON200'), ('2', 'iCON150'), ('3', 'iCON150'), ('4', 'iCON140'),
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
                 ('47', 'MFReader'), ('48', 'MFReader'), ('49', 'MFReader'), ('50', 'iMotor') ]

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
                    (734, '0000000000000000000000000000000000000000000000030000000000000300000000000000030000000000000003000000000000000003000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000040463000000000000030000000000000000030000000000000000000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300'),
                ],
                2: [
                    (734, '0000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000000000000000300000000000000000000000000000000000000000000000000000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000046363000000000000030000000000000000030000000000000000000000000000030000000000000003000000000000000000000000000000000000000000000003000000000000000300'),
                ],
            },
            # Turnstile
            '9': {
                1: [
                    (734, '0000000003030303050505050000000000000000000000030000000300000000000000030000000000000003000000000000000000000300000003000000000000000300000000000000030000000000000000000003000000030000000000000003000000000000000300000000000000000000030000000300000000000000030000000000000003000000000000000000000063636363000000000000000000000000000000030000000000000300000000000003000000000000030000000404040401010101040404040000000000000000000000000000000000000000'),
                    (740, '0000000003030303050505050000000000000000000000030000000300000000000000030000000000000003000000000000000000000300000003000000000000000300000000000000030000000000000000000003000000030000000000000003000000000000000300000000000000000000030000000300000000000000030000000000000003000000000000000000000063636363000000000305030500000000000000030000000000000300000000000003000000000000030000000404040401010101040404040000000000000000000000000000000000000000'),
                ]
            },
            # iCON115
            '11': {
                1: [
                    (734, '0000000000000000000000000000000000000000000000030000000000000300000000000000030000000000000003000000000000000003000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000006363000000000000000000000000000000030000000000000000000000000000030000000000000003000000000000000300000000000000030000000000000000000000000000000000'),
                ],
                2: [
                    (734, '0000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000000000000000300000000000000000000000000000000000000000000000000000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000000300000000000000030000000000000003000000000000006363000000000000000000000000000000030000000000000000000000000000030000000000000003000000000000000000000000000000000000000000000000000000000000000000'),
                ],
            },
            # iCON50
            '12': {
                1: [
                    (734, '0000000000000003000000000000030000000000000000030000000000000300000000000000000000000000000003000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),
                ],
            },
            # iCON130
            '17': {
                2: [
                    (734, '0000000000000303000005050000000000000000000000030000000300000000000000030000000000000003000000000000000000000003000000030000000000000003000000000000000300000000000000000003000000000300000000000000030000000000000003000000000000000000000300000000030000000000000003000000000000000300000000000000000000006363000000000000000000000000000000030000000000000300000000000000000000000000000000000000010100000303000001010000030300000000000000000000000000000000'),
                ],
                3: [
                    (734, '0000000000030303000505050000000000000000000000030000000300000000000000030000000000000003000000000000000000000003000000030000000000000003000000000000000300000000000000000003000000000300000000000000030000000000000003000000000000000000030000000003000000000000000300000000000000030000000000000000000000636363000000000000000000000000000000030000000000000300000000000003000000000000000000000001010100030303000101010003030300000000000000000000000000000000'),
                ],
                4: [
                    (734, '0000000003030303050505050000000000000000000000030000000300000000000000030000000000000003000000000000000000000300000003000000000000000300000000000000030000000000000000000003000000030000000000000003000000000000000300000000000000000000030000000300000000000000030000000000000003000000000000000000000063636363000000000000000000000000000000030000000000000300000000000003000000000000030000000101010103030303010101010303030300000000000000000000000000000000'),
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

    def button_reload_cards(self):
        cmd_env = self.env['hr.rfid.command'].with_user(1)

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

    def change_io_table(self, new_io_table):
        cmd_env = self.env['hr.rfid.command'].sudo()
        cmd_data = '00' + new_io_table

        for ctrl in self:
            if ctrl.io_table == new_io_table:
                continue

            if len(ctrl.io_table) != len(new_io_table):
                raise exceptions.ValidationError(
                    'Io table lengths are different, this should never happen????'
                )

            ctrl.io_table = new_io_table
            cmd_env.create({
                'webstack_id': ctrl.webstack_id.id,
                'controller_id': ctrl.id,
                'cmd': 'D9',
                'cmd_data': cmd_data,
            })

    def is_relay_ctrl(self):
        self.ensure_one()
        return self.hw_version_is_for_relay_ctrl(self.hw_version)

    @api.model
    def hw_version_is_for_relay_ctrl(self, hw_version):
        return hw_version in [ '30', '31', '32' ]

    def re_read_ctrl_info(self):
        cmd_env = self.env['hr.rfid.command']
        for ctrl in self:
            cmd_env.read_controller_information_cmd(ctrl)

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

    def open_doors(self):
        for door in self.doors:
            door.open_close_door(out=1, time=self.time)
        return create_and_ret_d_box(self.env, 'Doors opened', 'Doors successfully opened')

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

    def open_door(self):
        self.ensure_one()
        return self.open_close_door(1, 3)

    def close_door(self):
        self.ensure_one()
        return self.open_close_door(0, 3)

    def open_close_door(self, out: int, time: int):
        self.ensure_one()

        if self.controller_id.webstack_id.behind_nat is True:
            return self.create_door_out_cmd(out, time)
        else:
            return self.change_door_out(out, time)

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
            _('Because the webstack is behind NAT, we have to wait for the webstack to call us, so we created a command. The door will open/close as soon as possible.')
        )

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
                (data >> (3*8)) & 0xFF,
                (data >> (2*8)) & 0xFF,
                (data >> (1*8)) & 0xFF,
                (data >> (0*8)) & 0xFF,
            )
            cmd_data = ''.join(list('0' + ch for ch in cmd_data))
        return cmd_data

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
        headers = { 'content-type': 'application/json', 'Authorization': 'Basic ' + str(auth) }
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

    @api.constrains('apb_mode')
    def _check_apb_mode(self):
        for door in self:
            if door.apb_mode is True and len(door.reader_ids) < 2:
                raise exceptions.ValidationError('Cannot activate APB Mode for a door if it has less than 2 readers')

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

    def _compute_reader_name(self):
        for record in self:
            record.name = record.door_id.name + ' ' + \
                          self.reader_types[int(record.reader_type)][1] + \
                          ' Reader'

    @api.depends('door_ids')
    def _compute_reader_door(self):
        for reader in self:
            if not reader.controller_id.is_relay_ctrl() and len(reader.door_ids) == 1:
                reader.door_id = reader.door_ids

    def _inverse_reader_door(self):
        for reader in self:
            reader.door_ids = reader.door_id

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


class HrRfidUserEvent(models.Model):
    _name = 'hr.rfid.event.user'
    _description = "RFID User Event"
    _order = 'id desc'

    name = fields.Char(
        compute='_compute_user_ev_name'
    )

    ctrl_addr = fields.Integer(
        string='Controller ID',
        required=True,
        help='ID the controller differentiates itself from the others with on the same webstack'
    )

    workcode = fields.Char(
        string='Workcode (Raw)',
        help="Workcode that arrived from the event. If you are seeing this version, it means that you haven't created "
             'a workcode label for this one in the workcodes page.',
        default='-',
        readonly=True,
    )

    workcode_id = fields.Many2one(
        comodel_name='hr.rfid.workcode',
        string='Workcode',
        help='Workcode that arrived from the event',
        readonly=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help='Employee affected by this event',
        ondelete='cascade',
    )

    contact_id = fields.Many2one(
        'res.partner',
        string='Contact',
        help='Contact affected by this event',
        ondelete='cascade',
    )

    door_id = fields.Many2one(
        'hr.rfid.door',
        string='Door',
        help='Door affected by this event',
        ondelete='cascade',
    )

    reader_id = fields.Many2one(
        'hr.rfid.reader',
        string='Reader',
        help='Reader affected by this event',
        required=True,
        ondelete='cascade',
    )

    card_id = fields.Many2one(
        'hr.rfid.card',
        string='Card',
        help='Card affected by this event',
        ondelete='cascade',
    )

    command_id = fields.Many2one(
        'hr.rfid.command',
        string='Response',
        help='Response command',
        readonly=True,
        ondelete='set null',
    )

    event_time = fields.Datetime(
        string='Timestamp',
        help='Time the event triggered',
        required=True,
        index=True,
    )

    action_selection = [
        ('1', 'Granted'),
        ('2', 'Denied'),
        ('3', 'Denied T/S'),
        ('4', 'Denied APB'),
        ('5', 'Exit Button'),
        ('6', 'Granted (no entry)'),
        ('64', 'Request Instructions'),
    ]

    event_action = fields.Selection(
        selection=action_selection,
        string='Action',
        help='What happened to trigger the event',
        required=True,
    )

    action_string = fields.Char(
        compute='_compute_user_ev_action_str',
    )

    @api.model
    def _delete_old_events(self):
        event_lifetime = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.event_lifetime')
        if event_lifetime is None:
            return False

        lifetime = timedelta(days=int(event_lifetime))
        today = datetime.today()
        res = self.search([
            ('event_time', '<', today-lifetime)
        ])
        res.unlink()

        return self.env['hr.rfid.event.system'].delete_old_events()

    def _compute_user_ev_name(self):
        for record in self:
            if record.employee_id:
                name = record.employee_id.name
            elif record.contact_id:
                name = record.contact_id.name
            else:
                name = record.door_id.name
            name += ' - '
            if record.event_action != '64':
                name += self.action_selection[int(record.event_action)-1][1]
            else:
                name += 'Request Instructions'
            if record.door_id:
                name += ' @ ' + record.door_id.name
            record.name = name

    def _compute_user_ev_action_str(self):
        for record in self:
            record.action_string = 'Access ' + self.action_selection[int(record.event_action)-1][1]

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        records = super(HrRfidUserEvent, self).create(vals_list)

        for rec in records:
            # '1' == Granted
            if rec.event_action != '1':
                continue

            if not rec.employee_id and not rec.contact_id:
                continue

            zones = rec.door_id.zone_ids

            if len(rec.door_id.reader_ids) > 1:
                # Reader type is In
                if rec.reader_id.reader_type == '0':
                    zones.person_entered(rec.employee_id or rec.contact_id, rec)
                # Reader type is Out
                else:
                    zones.person_left(rec.employee_id or rec.contact_id, rec)
                continue

            if rec.reader_id.mode != '03':
                zones.person_went_through(rec)
            else:
                wc = rec.workcode_id
                if len(wc) == 0:
                    continue

                if wc.user_action == 'start':
                    rec.door_id.zone_ids.person_entered(rec.employee_id, rec)
                elif wc.user_action == 'break':
                    rec.door_id.zone_ids.person_left(rec.employee_id, rec)
                elif wc.user_action == 'stop':
                    stack = []
                    last_events = self.search([
                        ('event_time',  '>=', datetime.now() - timedelta(hours=12)),
                        ('employee_id',  '=', rec.employee_id.id),
                        ('id',          '!=', rec.id),
                        ('workcode_id', '!=', None),
                    ]).sorted(key=lambda r: r.event_time)

                    for event in last_events:
                        action = event.workcode_id.user_action
                        if action == 'stop':
                            if len(stack) > 0:
                                stack.pop()
                        else:
                            stack.append(action)

                    if len(stack) > 0:
                        if stack[-1] == 'start':
                            rec.door_id.zone_ids.person_left(rec.employee_id, rec)
                        else:
                            rec.door_id.zone_ids.person_entered(rec.employee_id, rec)

        return records


class HrRfidSystemEvent(models.Model):
    _name = 'hr.rfid.event.system'
    _description = 'RFID System Event'
    _order = 'id desc'

    name = fields.Char(
        compute='_compute_sys_ev_name'
    )

    webstack_id = fields.Many2one(
        'hr.rfid.webstack',
        string='Module',
        help='Module affected by this event',
        default=None,
        ondelete='cascade',
    )

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        string='Controller',
        help='Controller affected by this event',
        default=None,
        ondelete='cascade',
    )

    timestamp = fields.Datetime(
        string='Timestamp',
        help='Time the event occurred',
        required=True,
        index=True,
    )

    occurrences = fields.Integer(
        string='Occurrences',
        help='Number of times the event has happened',
        default=1,
    )

    last_occurrence = fields.Datetime(
        string='Last occurrence',
    )

    action_selection = [
        ('0', 'Unknown Event?'),
        ('1', 'DuressOK'),
        ('2', 'DuressError'),
        ('3', 'R1 Card OK'),
        ('4', 'R1 Card Error'),
        ('5', 'R1 T/S Error'),
        ('6', 'R1 APB Error'),
        ('7', 'R2 Card OK'),
        ('8', 'R2 Card Error'),
        ('9', 'R2 T/S Error'),
        ('10', 'R2 APB Error'),
        ('11', 'R3 Card OK'),
        ('12', 'R3 Card Error'),
        ('13', 'R3 T/S Error'),
        ('14', 'R3 APB Error'),
        ('15', 'R4 Card Ok'),
        ('16', 'R4 Card Error'),
        ('17', 'R4 T/S Error'),
        ('18', 'R4 APB Error'),
        ('19', 'EmergencyOpenDoor'),
        ('20', 'ON/OFF Siren'),
        ('21', 'OpenDoor1 from In1'),
        ('22', 'OpenDoor2 from In2'),
        ('23', 'OpenDoor3 from In3'),
        ('24', 'OpenDoor4 from In4'),
        ('25', 'Dx Overtime'),
        ('26', 'ForcedOpenDx'),
        ('27', 'DELAY ZONE ON (if out) Z4,Z3,Z2,Z1'),
        ('28', 'DELAY ZONE OFF (if in) Z4,Z3,Z2,Z1'),
        ('29', ''),
        ('30', 'Power On event'),
        ('31', 'Open/Close Door From PC'),
        ('33', 'Siren On/Off from PC'),
        ('34', 'eZoneAlarm'),
        ('35', 'Zone Arm/Disarm'),
        ('45', '1-W ERROR (wiring problems)'),
        ('47', 'Vending Purchase Complete'),
        ('48', 'Vending Error1'),
        ('49', 'Vending Error2'),
        ('64', 'Vending Request User Balance'),
        ('67', 'Arm Denied'),
    ]

    event_nums = list(map(lambda a: a[0], action_selection))

    event_action = fields.Selection(
        selection=action_selection,
        string='Event Type',
    )

    error_description = fields.Char(
        string='Description',
        help='Description on why the error happened',
    )

    input_js = fields.Char(
        string='Input JSON',
    )

    @api.model
    def delete_old_events(self):
        event_lifetime = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.event_lifetime')
        if event_lifetime is None:
            return False

        lifetime = timedelta(days=int(event_lifetime))
        today = datetime.today()
        res = self.search([
            ('timestamp', '<', today-lifetime)
        ])
        res.unlink()

        return True

    def _compute_sys_ev_name(self):
        for record in self:
            record.name = str(record.webstack_id.name) + '-' + str(record.controller_id.name) +\
                          ' at ' + str(record.timestamp)

    def _check_save_comms(self, vals):
        save_comms = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.save_webstack_communications')
        if save_comms != 'True':
            if 'input_js' not in vals:
                return

            if 'error_description' in vals and vals['error_description'] == 'Could not find the card':
                js = json.loads(vals['input_js'])
                vals['input_js'] = js['event']['card']
            else:
                vals.pop('input_js')

    def _check_duplicate_sys_ev(self, vals):
        dupe = self.env['hr.rfid.event.system'].search([
            ('webstack_id', '=', vals['webstack_id']),
        ], limit=1)

        if not dupe:
            return False

        if vals.get('controller_id', False) != dupe.controller_id.id:
            return False

        if vals.get('event_action', False) != dupe.event_action:
            return False

        if vals.get('error_description', False) != dupe.error_description:
            return False

        if vals.get('input_js', False) != dupe.input_js:
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

            records += super(HrRfidSystemEvent, self).create([vals])

        return records

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

        if type(sys_ev.input_js) != type(''):
            raise exceptions.ValidationError('System event does not have a card number in it')

        if len(sys_ev.input_js) == 10:
            return sys_ev.input_js

        js = json.loads(sys_ev.input_js)
        try:
            card_number = js['event']['card']
            return card_number
        except KeyError as _:
            raise exceptions.ValidationError('System event does not have a card number in it')

    sys_ev_id = fields.Many2one(
        'hr.rfid.event.system',
        string='System event',
        required=True,
        default=_default_sys_ev,
        ondelete='cascade',
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Card owner (employee)',
    )

    contact_id = fields.Many2one(
        'res.partner',
        stirng='Card owner (contact)',
    )

    card_number = fields.Char(
        string='Card Number',
        default =_default_card_number,
    )

    card_type = fields.Many2one(
        'hr.rfid.card.type',
        string='Card type',
        help='Only doors that support this type will be able to open this card',
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_card_type_def').id,
    )

    activate_on = fields.Datetime(
        string='Activate on',
        help='Date and time the card will be activated on',
        track_visibility='onchange',
        default=lambda self: datetime.now(),
    )

    deactivate_on = fields.Datetime(
        string='Deactivate on',
        help='Date and time the card will be deactivated on',
        track_visibility='onchange',
    )

    active = fields.Boolean(
        string='Active',
        help='Whether the card is active or not',
        track_visibility='onchange',
        default=True,
    )

    cloud_card = fields.Boolean(
        string='Cloud Card',
        help='A cloud card will not be added to controllers that are in the "externalDB" mode.',
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


class HrRfidCommands(models.Model):
    # Commands we have queued up to send to the controllers
    _name = 'hr.rfid.command'
    _description = 'Command to controller'
    _order = 'id desc'

    commands = [
        ('F0', 'Read System Information'),
        ('F1', 'Read/Search Card And Info'),
        ('F2', 'Read Group of Cards'),
        ('F3', 'Read Time Schedules'),
        ('F4', 'Read Holiday List'),
        ('F5', 'Read Controller Mode'),
        ('F6', 'Read Readers Mode'),
        ('F7', 'Read System Clock'),
        ('F8', 'Read Duress Mode'),
        ('F9', 'Read Input/Output Table'),
        ('FB', 'Read Inputs Flags'),
        ('FC', 'Read Anti-Passback Mode'),
        ('FD', 'Read Fire & Security Status'),
        ('FE', 'Read FireTime, Sound_Time'),
        ('FF', 'Read Output T/S Table'),
        ('D0', 'Write Controller ID'),
        ('D1', 'Add/Delete Card'),
        ('D2', 'Delete Card'),
        ('D3', 'Write Time Schedules'),
        ('D4', 'Write Holiday List'),
        ('D5', 'Write Controller Mode'),
        ('D6', 'Write Readers Mode'),
        ('D7', 'Write Controller System Clock'),
        ('D8', 'Write Duress Mode'),
        ('D9', 'Write Input/Output Table'),
        ('DA', 'Delete Last Event'),
        ('DB', 'Open Output'),
        ('DB2', 'Sending Balance To Vending Machine'),
        ('DC', 'System Initialization'),
        ('DD', 'Write Input Flags'),
        ('DE', 'Write Anti-Passback Mode'),
        ('DF', 'Write Outputs T/S Table'),
        ('D3', 'Delete Time Schedule'),
        ('B3', 'Read Controller Status'),
    ]

    statuses = [
        ('Wait', 'Command Waiting for Webstack Communication'),
        ('Process', 'Command Processing'),
        ('Success', 'Command Execution Successful'),
        ('Failure', 'Command Execution Unsuccessful'),
    ]

    errors = [
        ('-1', 'Unknown Error'),
        ('0', 'No Error'),
        ('1', 'I2C Error'),
        ('2', 'I2C Error'),
        ('3', 'RS485 Error'),
        ('4', 'Wrong Value/Parameter'),
        ('5', 'CRC Error'),
        ('6', 'Memory Error'),
        ('7', 'Cards Overflow'),
        ('8', 'Not Use'),
        ('9', 'Card Not Found'),
        ('10', 'No Cards'),
        ('11', 'Not Use'),
        ('12', 'Controller Busy, Local Menu Active or Master Card Mode in Use'),
        ('13', '1-Wire Error'),
        ('14', 'Unknown Command'),
        ('20', 'No Response from controller (WebSDK)'),
        ('21', 'Bad JSON Structure (WebSDK)'),
        ('22', 'Bad CRC from Controller (WebSDK)'),
        ('23', 'Bridge is Currently in Use (WebSDK)'),
        ('24', 'Internal Error, Try Again (WebSDK)'),
        ('30', 'No response from the Module'),
        ('31', 'Incorrect Data Response'),
    ]

    error_codes = list(map(lambda a: a[0], errors))

    name = fields.Char(
        compute='_compute_cmd_name',
    )

    webstack_id = fields.Many2one(
        'hr.rfid.webstack',
        string='Module',
        help='Module the command is/was intended for',
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        string='Controller',
        help='Controller the command is/was intended for',
        required=True,
        readonly=True,
        ondelete='cascade',
        index=True,
    )

    cmd = fields.Selection(
        selection=commands,
        string='Command',
        help='Command to send/have sent to the module',
        required=True,
        readonly=True,
        index=True,
    )

    cmd_data = fields.Char(
        string='Command data',
        help='Additional data sent to the controller',
        default='',
        readonly=True,
    )

    status = fields.Selection(
        selection=statuses,
        string='Status',
        help='Current status of the command',
        default='Wait',
        index=True,
    )

    error = fields.Selection(
        selection=errors,
        string='Error',
        help='If status is "Command Unsuccessful" this field is updated '
             'to the reason for why it was unsuccessful',
        default='0'
    )

    cr_timestamp = fields.Datetime(
        string='Creation Time',
        help='Time at which the command was created',
        readonly=True,
        required=True,
        default=lambda self: datetime.now(),
    )

    ex_timestamp = fields.Datetime(
        string='Execution Time',
        help='Time at which the module returned a response from the command',
    )

    request = fields.Char(
        string='Request',
        help='Request json sent to the module'
    )

    response = fields.Char(
        string='Response',
        help='Response json sent from the module',
    )

    card_number = fields.Char(
        string='Card',
        help='Card the command will do an operation for',
        limit=10,
        index=True,
    )

    retries = fields.Integer(
        string='Command retries',
        help='How many times the command failed to run and has been retried',
        default=0,
    )

    pin_code = fields.Char(string='Pin Code (debug info)')
    ts_code = fields.Char(string='TS Code (debug info)', limit=8)
    rights_data = fields.Integer(string='Rights Data (debug info)')
    rights_mask = fields.Integer(string='Rights Mask (debug info)')

    @api.model
    def read_controller_information_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'F0',
        }])

    @api.model
    def synchronize_clock_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'D7',
        }])

    @api.model
    def delete_all_cards_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'DC',
            'cmd_data': '0303',
        }])

    @api.model
    def delete_all_events_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'DC',
            'cmd_data': '0404',
        }])

    @api.model
    def read_readers_mode_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'F6',
        }])

    @api.model
    def read_io_table_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'F9',
            'cmd_data': '00',
        }])

    @api.model
    def read_anti_pass_back_mode_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'FC',
        }])

    def _compute_cmd_name(self):
        def find_desc(cmd):
            for it in HrRfidCommands.commands:
                if it[0] == cmd:
                    return it[1]

        for record in self:
            record.name = str(record.cmd) + ' ' + find_desc(record.cmd)

    @api.model
    def create_d1_cmd(self, ws_id, ctrl_id, card_num, pin_code, ts_code, rights_data, rights_mask):
        self.create([{
            'webstack_id': ws_id,
            'controller_id': ctrl_id,
            'cmd': 'D1',
            'card_number': card_num,
            'pin_code': pin_code,
            'ts_code': ts_code,
            'rights_data': rights_data,
            'rights_mask': rights_mask,
        }])

    @api.model
    def _create_d1_cmd_relay(self, ws_id, ctrl_id, card_num, rights_data, rights_mask):
        self.create([{
            'webstack_id': ws_id,
            'controller_id': ctrl_id,
            'cmd': 'D1',
            'card_number': card_num,
            'rights_data': rights_data,
            'rights_mask': rights_mask,
        }])

    @api.model
    def add_remove_card(self, card_number, ctrl_id, pin_code, ts_code, rights_data, rights_mask):
        ctrl = self.env['hr.rfid.ctrl'].browse(ctrl_id)
        commands_env = self.env['hr.rfid.command']

        old_cmd = commands_env.search([
            ('cmd', '=', 'D1'),
            ('status', '=', 'Wait'),
            ('card_number', '=', card_number),
            ('controller_id', '=', ctrl.id),
        ])

        if not old_cmd:
            if rights_mask != 0:
                self.create_d1_cmd(ctrl.webstack_id.id, ctrl_id, card_number,
                                   pin_code, ts_code, rights_data, rights_mask)
        else:
            new_ts_code = ''
            if str(ts_code) != '':
                for i in range(4):
                    num_old = int(old_cmd.ts_code[i*2:i*2+2], 16)
                    num_new = int(ts_code[i*2:i*2+2], 16)
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

    @api.model
    def _add_remove_card_relay(self, card_number, ctrl_id, rights_data, rights_mask):
        ctrl = self.env['hr.rfid.ctrl'].browse(ctrl_id)
        commands_env = self.env['hr.rfid.command']

        old_cmd = commands_env.search([
            ('cmd', '=', 'D1'),
            ('status', '=', 'Wait'),
            ('card_number', '=', card_number),
            ('controller_id', '=', ctrl.id),
        ])

        if not old_cmd:
            self._create_d1_cmd_relay(ctrl.webstack_id.id, ctrl_id, card_number, rights_data, rights_mask)
        else:
            if ctrl.mode == 3:
                new_rights_data = rights_data
                new_rights_mask = rights_mask
            else:
                new_rights_data = (rights_data | old_cmd.rights_data)
                new_rights_data ^= (rights_mask & old_cmd.rights_data)
                new_rights_data ^= (rights_data & old_cmd.rights_mask)
                new_rights_mask = rights_mask | old_cmd.rights_mask
                new_rights_mask ^= (rights_mask & old_cmd.rights_data)
                new_rights_mask ^= (rights_data & old_cmd.rights_mask)

            old_cmd.write({
                'rights_mask': new_rights_mask,
                'rights_data': new_rights_data,
            })

    @api.model
    def add_card(self, door_id, ts_id, pin_code, card_id):
        door = self.env['hr.rfid.door'].browse(door_id)
        time_schedule = self.env['hr.rfid.time.schedule'].browse(ts_id)
        card = self.env['hr.rfid.card'].browse(card_id)
        card_number = card.number

        if door.controller_id.is_relay_ctrl():
            return self._add_card_to_relay(door_id, card_id)

        for reader in door.reader_ids:
            ts_code = [0, 0, 0, 0]
            ts_code[reader.number-1] = time_schedule.number
            ts_code = '%02X%02X%02X%02X' % (ts_code[0], ts_code[1], ts_code[2], ts_code[3])
            self.add_remove_card(card_number, door.controller_id.id, pin_code, ts_code,
                                 1 << (reader.number-1), 1 << (reader.number-1))

    @api.model
    def _add_card_to_relay(self, door_id, card_id):
        door = self.env['hr.rfid.door'].browse(door_id)
        card = self.env['hr.rfid.card'].browse(card_id)
        ctrl = door.controller_id

        if ctrl.mode == 1:
            rdata = 1 << (door.number - 1)
            rmask = rdata
        elif ctrl.mode == 2:
            rdata = 1 << (door.number - 1)
            if door.reader_ids.number == 2:
                rdata *= 0x10000
            rmask = rdata
        elif ctrl.mode == 3:
            rdata = door.number
            rmask = -1
        else:
            raise exceptions.ValidationError(_('Controller %s has mode=%d, which is not supported!')
                                             % (ctrl.name, ctrl.mode))

        self._add_remove_card_relay(card.number, ctrl.id, rdata, rmask)

    @api.model
    def remove_card(self, door_id, pin_code, card_number=None, card_id=None):
        door = self.env['hr.rfid.door'].browse(door_id)

        if card_id is not None:
            card = self.env['hr.rfid.card'].browse(card_id)
            card_number = card.number

        if door.controller_id.is_relay_ctrl():
            return self._remove_card_from_relay(door_id, card_number)

        for reader in door.reader_ids:
            self.add_remove_card(card_number, door.controller_id.id, pin_code, '00000000',
                                 0, 1 << (reader.number-1))

    @api.model
    def _remove_card_from_relay(self, door_id, card_number):
        door = self.env['hr.rfid.door'].browse(door_id)
        ctrl = door.controller_id

        if ctrl.mode == 1:
            rmask = 1 << (door.number - 1)
        elif ctrl.mode == 2:
            rmask = 1 << (door.number - 1)
            if door.reader_ids.number == 2:
                rmask *= 0x10000
        elif ctrl.mode == 3:
            rmask = -1
        else:
            raise exceptions.ValidationError(_('Controller %s has mode=%d, which is not supported!')
                                             % (ctrl.name, ctrl.mode))

        self._add_remove_card_relay(card_number, ctrl.id, 0, rmask)

    @api.model
    def change_apb_flag(self, door, card, can_exit=True):
        if door.number == 1:
            rights = 0x40  # Bit 7
        else:
            rights = 0x20  # Bit 6
        self.add_remove_card(card.number, door.controller_id.id, card.get_owner().hr_rfid_pin_code,
                             '00000000', rights if can_exit else 0, rights)

    @api.model
    def _update_commands(self):
        failed_commands = self.search([
            ('status', '=', 'Process'),
            ('cr_timestamp', '<', str(fields.datetime.now() - timedelta(minutes=1)))
        ])

        for it in failed_commands:
            it.write({
                'status': 'Failure',
                'error': '30',
            })

        failed_commands = self.search([
            ('status', '=', 'Wait'),
            ('cr_timestamp', '<', str(fields.datetime.now() - timedelta(minutes=1)))
        ])

        for it in failed_commands:
            it.write({
                'status': 'Failure',
                'error': '30',
            })

    @api.model
    def _sync_clocks(self):
        ws_env = self.env['hr.rfid.webstack']
        commands_env = self.env['hr.rfid.command']

        controllers = ws_env.search([('active', '=', True)]).mapped('controllers')

        for ctrl in controllers:
            commands_env.create([{
                'webstack_id': ctrl.webstack_id.id,
                'controller_id': ctrl.id,
                'cmd': 'D7',
            }])

    @api.model
    def _read_statuses(self):
        ctrl_env = self.env['hr.rfid.ctrl']
        commands_env = self.env['hr.rfid.command']

        controllers = ctrl_env.search([('read_b3_cmd', '=', True)])

        for ctrl in controllers:
            commands_env.create({
                'webstack_id': ctrl.webstack_id.id,
                'controller_id': ctrl.id,
                'cmd': 'B3',
            })

    def _check_save_comms(self, vals):
        save_comms = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.save_webstack_communications')
        if save_comms != 'True':
            if 'request' in vals:
                vals.pop('request')
            if 'response' in vals:
                vals.pop('response')

    @api.model_create_multi
    def create(self, vals_list: list):
        def find_last_wait(_cmd, _vals):
            ret = self.search([
                ('webstack_id', '=', _vals['webstack_id']),
                ('controller_id', '=', _vals['controller_id']),
                ('cmd', '=', _cmd),
                ('status', '=', 'Wait'),
            ])
            if len(ret) > 0:
                return ret[-1]
            return ret

        records = self.env['hr.rfid.command']
        for vals in vals_list:
            self._check_save_comms(vals)

            cmd = vals['cmd']

            if cmd not in [ 'DB', 'D9', 'D5', 'DE', 'D7', 'F0', 'FC', 'D6', 'B3' ]:
                records += super(HrRfidCommands, self).create([vals])
                continue

            res = find_last_wait(cmd, vals)

            if len(res) == 0:
                records += super(HrRfidCommands, self).create([vals])
                continue

            cmd_data = vals.get('cmd_data', False)

            if cmd == 'DB':
                if res.cmd_data[0] == cmd_data[0] and res.cmd_data[1] == cmd_data[1]:
                    res.cmd_data = cmd_data
                    continue
            elif cmd in [ 'D9', 'D5', 'DE', 'D6' ]:
                res.cmd_data = cmd_data
                continue
            elif cmd in [ 'D7', 'F0', 'FC', 'B3' ]:
                continue

            records += super(HrRfidCommands, self).create([vals])

        return records

    def write(self, vals):
        self._check_save_comms(vals)

        if 'error' in vals and vals['error'] not in self.error_codes:
            vals['error'] = '-1'

        return super(HrRfidCommands, self).write(vals)
