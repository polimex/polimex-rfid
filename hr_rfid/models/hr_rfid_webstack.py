# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _, SUPERUSER_ID, tools
from datetime import datetime, timedelta
import socket
import http.client
import requests
import json
import base64
import pytz

import logging
_logger = logging.getLogger(__name__)


# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def _tz_get(self):
    return _tzs

class BadTimeException(Exception):
    pass



class HrRfidWebstack(models.Model):
    _name = 'hr.rfid.webstack'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    _description = 'Module'

    name = fields.Char(
        string='Name',
        help='A label to easily differentiate modules',
        required=True,
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)
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
    time_format = fields.Char(
        compute='_compute_time_format'
    )

    serial = fields.Char(
        string='Serial number',
        help='Unique number to differentiate all modules',
        size=6,
        index=True,
        readonly=True,
    )

    key = fields.Char(
        string='Key',
        size=4,
        index=True,
        default='0000',
        tracking=True,
    )

    active = fields.Boolean(
        string='Active',
        help='Will accept events from module if true',
        default=False,
        tracking=True,
    )

    version = fields.Char(
        string='Version',
        help='Software version of the module',
        size=6,
    )

    hw_version = fields.Char(
        string='Hardware Version',
        help='Hardware version of the module',
        size=6,
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
        size=26,
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

    http_link = fields.Char(
        compute='_compute_http_link'
    )

    module_username = fields.Selection(
        selection=[('admin', 'admin'), ('sdk', 'SDK')],
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
        selection=[
            ('u', 'Unavailable'),
            ('a', 'Available')
        ],
        string='Available?',
        help='Whether the module was available the last time Odoo tried to connect to it.',
        default='u',
    )

    last_update = fields.Boolean(string='Contacted in last 10 min', compute='_compute_last_update')

    commands_count = fields.Char(string='Commands count', compute='_compute_counts')
    system_event_count = fields.Char(string='System Events count', compute='_compute_counts')
    controllers_count = fields.Char(string='Controllers count', compute='_compute_counts')

    _sql_constraints = [('rfid_webstack_serial_unique', 'unique(serial)',
                         'Serial number for webstacks must be unique!')]

    @api.depends('hw_version')
    def _compute_time_format(self):
        for ws in self:
            if ws.hw_version in ['100.1', '50.1']:
                ws.time_format = '%m.%d.%y %H:%M:%S'
            elif ws.hw_version in ['10.3']:
                ws.time_format = '%d.%m.%y %H:%M:%S'
            else:
                ws.time_format = '%d.%m.%y %H:%M:%S'

    @api.depends('controllers')
    def _compute_counts(self):
        for a in self:
            a.commands_count = self.env['hr.rfid.command'].search_count([('webstack_id', '=', a.id)])
            a.system_event_count = self.env['hr.rfid.event.system'].search_count([('webstack_id', '=', a.id)])
            a.controllers_count = len(a.controllers)

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
        else:
            domain = [('webstack_id', '=', self.id)]
        model = 'hr_rfid'
        if xml_id:
            res = self.env['ir.actions.act_window']._for_xml_id(model + '.' + xml_id)
            res.update(
                context=dict(self.env.context, default_webstack_id=self.id, group_by=False),
                domain=domain
            )
            return res
        return False

    @api.depends('updated_at')
    def _compute_last_update(self):
        for r in self:
            if not r.updated_at:
                r.last_update = False
                continue
            ten_min_delay = fields.Datetime.subtract(fields.Datetime.now(), minutes=10)
            r.last_update = r.updated_at > ten_min_delay

    def toggle_ws_active(self):
        for rec in self:
            rec.active = not rec.active

    def action_set_active(self):
        self.active = True

    def action_set_inactive(self):
        self.active = False

    def _get_tz_offset(self):
        self.ensure_one()
        tz_h = int(self.tz_offset[:3], 10)
        tz_m = int(self.tz_offset[3:], 10)
        return timedelta(hours=tz_h, minutes=tz_m)

    def action_set_webstack_settings(self):
        self.ensure_one()
        bad_hosts = ['localhost', '127.0.0.1','.local']
        odoo_url = str(self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
        odoo_port = len(odoo_url.split(':'))==3 and int(odoo_url.split(':')[2], 10) or 80
        odoo_protocol = odoo_url.split('//')[0]
        if any([odoo_url.find(bh) < 0 for bh in bad_hosts]):
            local_ip = get_local_ip()
            new_odoo_url =  f"{local_ip}"
            if odoo_url == new_odoo_url:
                raise exceptions.ValidationError(_('Your current setup not permit this operation. You need to do it manually. Please call your support team for more information!'))
            else:
                odoo_url = new_odoo_url
                _logger.info(f"After investigation, the system url is: {odoo_url}")
        odoo_url += '/hr/rfid/event'

        username = str(self.module_username) if self.module_username else ''
        password = str(self.module_password) if self.module_password else ''

        auth = base64.b64encode((username + ':' + password).encode())
        auth = auth.decode()
        req_headers = {"content-type": "application/json", "Authorization": "Basic " + str(auth)}
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
        self.key = None
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Setup the Module'),
                'message': _('Information sent to the Module. If everything is fine, the Module have to start '
                             'communication with this instance. The URL in use is http://{} on port {}.').format(odoo_url, odoo_port),
                'sticky': True,
            }}


    def action_check_if_ws_available(self):
        for ws in self:
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
                module = {
                    'version': js['sdk']['sdkVersion'],
                    'hw_version': js['sdk']['sdkHardware'],
                    'serial': js['convertor'],
                    'available': 'a',
                }
                ws.write(module)
            except socket.timeout:
                raise exceptions.ValidationError('Could not connect to the webstack')
            except(socket.error, socket.gaierror, socket.herror) as e:
                raise exceptions.ValidationError('Unexpected error:\n' + str(e))
            except KeyError as __:
                raise exceptions.ValidationError('Information returned by the webstack invalid')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Check connection to the Module'),
                'message': _('Everything looks just great!'),
                # 'links': [{
                #     'label': production.name,
                #     'url': f'#action={action.id}&id={production.id}&model=mrp.production'
                # }],
                'sticky': False,
            }}

    def get_controllers(self):
        controllers = None
        for ws in self:
            if ws.behind_nat or not ws.active:
                continue
            host = str(ws.last_ip)
            try:
                response = requests.get(f'http://{host}/config.json', timeout=2)
                if response.status_code != 200:
                    raise exceptions.ValidationError('Webstack sent us http code {}'
                                                     ' when 200 was expected.'.format(response.status_code))
                js = response.json()
                controllers = js['sdk']['devFound']
                if ws.name == f"Module {ws.serial}":
                    ws.name = f"Module {ws.serial} ({js['netConfig']['Host_Name']})"
                if not isinstance(controllers, int):
                    raise exceptions.ValidationError('Webstack gave us bad data when requesting /config.json')

                for dev in range(controllers):
                    response = requests.get(f'http://{host}/sdk/status.json?dev={dev}')

                    if response.status_code != 200:
                        raise exceptions.ValidationError('Webstack sent us http code {} when 200 was expected'
                                                         ' while requesting /sdk/details.json?dev={}'
                                                         .format(response.status_code, dev))
                    try:
                        ctrl_js = response.json()
                    except Exception as e:
                        _logger.error(str(e))
                        continue
                    if not self.env['hr.rfid.ctrl'].search_count(
                            [('ctrl_id', '=', ctrl_js['dev']['devID']), ('webstack_id', '=', ws.id)]):
                        controller = self.env['hr.rfid.ctrl'].sudo().create([{
                            'name': 'Controller',
                            'ctrl_id': ctrl_js['dev']['devID'],
                            'webstack_id': ws.id,
                        }])
                        controller.read_controller_information_cmd()
            except socket.timeout:
                raise exceptions.ValidationError('Could not connect to the webstack at ' + host)
            except(socket.error, socket.gaierror, socket.herror) as e:
                raise exceptions.ValidationError('Unexpected error:\n' + str(e))
            except KeyError as __:
                raise exceptions.ValidationError('Information returned by the webstack at '
                                                 + host + ' invalid')
        if controllers:
            return self.with_context(xml_id='hr_rfid_ctrl_action').return_action_to_open()
        else:
            return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Reading controllers from the Module'),
                        'message': _('No controllers detected in the Module or the Module is Archived'),
                        # 'links': [{
                        #     'label': production.name,
                        #     'url': f'#action={action.id}&id={production.id}&model=mrp.production'
                        # }],
                        'type': 'warning',
                        'sticky': False,
                    }}

    @api.depends('tz')
    def _compute_tz_offset(self):
        for user in self:
            user.tz_offset = datetime.now(pytz.timezone(user.tz or 'GMT')).strftime('%z')

    @api.depends('last_ip')
    def _compute_http_link(self):
        for record in self:
            if record.last_ip != '' and record.last_ip is not False:
                link = 'http://' + record.last_ip + '/'
                record.http_link = link
            else:
                record.http_link = ''

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

    # Commands to all controllers in webstack
    def _sync_clocks(self):
        for ws in self:
            ws.controllers.synchronize_clock_cmd()

    # Log system event for this webstack/s
    def sys_log(self, error_description, input_json):
        for ws in self:
            self.env['hr.rfid.event.system'].sudo().create({
                'webstack_id': ws.id,
                'timestamp': fields.Datetime.now(),
                'error_description': error_description,
                'input_js': input_json,
            })

    @api.model
    def sync_all_clocks(self):
        for ws in self.env['hr.rfid.webstack'].search([('active', '=', True)]):
            ws.controllers.synchronize_clock_cmd()


    # Communication helpers

    def direct_execute(self, cmd: dict, command_id: models.Model = None):
        if command_id:
            pass  # TODO Direct execution of stored commands
        else:
            for ws in self:
                if ws.module_username is False:
                    username = ''
                else:
                    username = str(ws.module_username)

                if ws.module_password is False:
                    password = ''
                else:
                    password = str(ws.module_password)
                # TODO Store command in model as in execution
                try:
                    response = requests.post('http://' + ws.last_ip + '/sdk/cmd.json', auth=(username, password), json=cmd,
                                             timeout=2)
                    if response.status_code != 200:
                        raise exceptions.ValidationError('While trying to send the command to the module, '
                                                         'it returned code ' + str(response.status_code) + ' with body:\n'
                                                         + response.content.decode())
                    return response.json()
                except Exception as e:
                    _logger.exception(tools.exception_to_unicode(e))
                    raise


    def get_ws_time(self, post_data: dict):
        self.ensure_one()
        t = f"{post_data['date']} {post_data['time']}"
        t = t.replace('-', '.')  # fix for WiFi module format
        try:
            ws_time = datetime.strptime(t, self.time_format)
            ws_time -= self._get_tz_offset()
        except ValueError:
            raise BadTimeException
        return ws_time

    def get_ws_time_str(self, post_data: dict):
        self.ensure_one()
        return self.get_ws_time(post_data).strftime('%Y-%m-%d %H:%M:%S')

    def _retry_command(self, status_code, cmd, event):
        if cmd.retries == 5:
            cmd.status = 'Failure'
            return self.check_for_unsent_cmd(status_code, event,)

        cmd.retries = cmd.retries + 1

        if event is not None:
            event.command_id = cmd
        return cmd.send_command(status_code)

    def check_for_unsent_cmd(self, status_code, event=None):
        self.ensure_one()

        commands_env = self.env['hr.rfid.command'].sudo()
        processing_comm = commands_env.search([
            ('webstack_id', '=', self.id),
            ('status', '=', 'Process'),
        ])

        if len(processing_comm) > 0:
            processing_comm = processing_comm[-1]
            return self._retry_command(status_code, processing_comm, event)

        command_id = commands_env.search([
            ('webstack_id', '=', self.id),
            ('status', '=', 'Wait'),
        ], order='id desc')

        if len(command_id) == 0:
            return {'status': status_code}

        command_id = command_id[-1]

        if event is not None:
            event.command_id = command_id.id
        return command_id.send_command(status_code)

    def report_sys_ev(self, description, post_data=None, controller_id=None, sys_ev_dict:dict = None):
        '''
        Create System event
        Dict = {
            'webstack_id': id,                  * auto
            'controller_id': id,                * auto
            'door_id': id,
            'alarm_line_id': id,
            'timestamp': timestamp,             * auto
            'event_action': str event number,
            'error_description': str,
            'input_js': str Input JSON
        }
        '''
        def get_timestamp(data:dict):
            if isinstance(data, dict) and 'event' in data:
                try:
                    return self.get_ws_time_str(data['event'])
                except BadTimeException:
                    return fields.Datetime.now()
            else:
                return fields.Datetime.now()

        self.ensure_one()
        sys_ev_env = self.env['hr.rfid.event.system'].sudo()
        if sys_ev_dict:
            if controller_id:
                sys_ev_dict['controller_id'] = controller_id.id
            sys_ev_dict['webstack_id'] = self.id
            if not 'timestamp' in sys_ev_dict:
                sys_ev_dict['timestamp'] = get_timestamp(post_data)
            if not 'input_js' in sys_ev_dict:
                sys_ev_dict['input_js'] = json.dumps(post_data)
            return sys_ev_env.create(sys_ev_dict)
        sys_ev = {
            'webstack_id': self.id,
            'error_description': description,
            'input_js': json.dumps(post_data),
        }

        if isinstance(post_data, dict) and 'event' in post_data:
            sys_ev['timestamp'] = get_timestamp(post_data)
            sys_ev['event_action'] = str(post_data['event']['event_n'])
        else:
            sys_ev['timestamp'] = fields.Datetime.now()

        if controller_id is not None:
            sys_ev['controller_id'] = controller_id.id

        return sys_ev_env.create(sys_ev)
        # sys_ev_env.refresh_views()

    def parse_heartbeat(self, post_data: dict):
        self.ensure_one()
        self.version = str(post_data['FW'])
        return self.check_for_unsent_cmd(200)

    def parse_response(self, post_data: dict):
        self.ensure_one()
        command_env = self.env['hr.rfid.command'].with_user(SUPERUSER_ID)
        response = post_data['response']
        controller = self.controllers.filtered(lambda c: c.ctrl_id == response.get('id', -1))
        if not controller:
            self.report_sys_ev('Module sent us a response from a controller that does not exist', post_data=post_data)
            return self.check_for_unsent_cmd(200)

        command = command_env.search([('webstack_id', '=', self.id),
                                      ('controller_id', '=', controller.id),
                                      ('status', '=', 'Process'),
                                      ('cmd', '=', response['c']), ], limit=1)

        if len(command) == 0 and response['c'] == 'DB':
            command = command_env.search([('webstack_id', '=', self.id),
                                          ('controller_id', '=', controller.id),
                                          ('status', '=', 'Process'),
                                          ('cmd', '=', 'DB2'), ], limit=1)

        if len(command) == 0:
            controller.report_sys_ev('Controller sent us a response to a command we never sent')
            return self.check_for_unsent_cmd(200)

        if response['e'] != 0:
            command.write({
                'status': 'Failure',
                'error': str(response['e']),
                'ex_timestamp': fields.Datetime.now(),
                'response': json.dumps(post_data),
            })
            return self.check_for_unsent_cmd(200)

        if response['c'] == 'F0':
            command.parse_f0_response(post_data=post_data)

        if response['c'] == 'F6':
            data = response['d']
            readers = [None, None, None, None]
            for it in controller.reader_ids:
                readers[it.number - 1] = it
            for i in range(4):
                if readers[i] is not None:
                    mode = str(data[i * 6:i * 6 + 2])
                    readers[i].write({
                        'mode': mode,
                        'no_d6_cmd': True,
                    })

        if response['c'] == 'F9':
            controller.write({
                'io_table': response['d']
            })

        if response['c'] == 'FC':
            apb_mode = response['d']
            for door in controller.door_ids:
                door.apb_mode = (door.number == '1' and (apb_mode & 1)) \
                                or (door.number == '2' and (apb_mode & 2))

        if response['c'] == 'B3':
            data = response['d']
            # 0000 0100 0711 0000 0000 0000 000000000000000000000000
            # '5a0000000719000000000000020202020000000000000000' iCON180
            input_states = (int(data[0:2], 16) & 0x7f) + ((int(data[2:4], 16) & 0x7f ) << 7)
            output_states = (int(data[4:6], 16) & 0x7f) + ((int(data[6:8], 16) & 0x7f) << 7)
            usys = [int(data[8:10], 16), int(data[10:12], 16)]
            uin = [int(data[12:14], 16), int(data[14:16], 16)]
            temperature = int(data[16:20], 10)
            humidity = int(data[20:24], 10)
            Z1 = int(data[24:26], 16)
            Z2 = int(data[26:28], 16)
            Z3 = int(data[28:30], 16)
            Z4 = int(data[30:32], 16)

            TOS = int(data[32:34], 16) * 10000 \
                  + int(data[34:36], 16) * 1000 \
                  + int(data[36:38], 16) * 100 \
                  + int(data[38:40], 16) * 10 \
                  + int(data[40:42], 16)

            hotel = [int(data[42:44], 16), int(data[44:46], 16), int(data[46:48], 16)]

            if temperature >= 1000:
                temperature -= 1000
                temperature *= -1
            temperature /= 10

            humidity /= 10

            sys_voltage = ((usys[0] & 0xF0) >> 4) * 1000
            sys_voltage += (usys[0] & 0x0F) * 100
            sys_voltage += ((usys[1] & 0xF0) >> 4) * 10
            sys_voltage += (usys[1] & 0x0F)
            sys_voltage = (sys_voltage * 8) / 500

            input_voltage = ((uin[0] & 0xF0) >> 4) * 1000
            input_voltage += (uin[0] & 0x0F) * 100
            input_voltage += ((uin[1] & 0xF0) >> 4) * 10
            input_voltage += (uin[1] & 0x0F)
            input_voltage = (input_voltage * 8) / 500

            controller.write({
                'system_voltage': sys_voltage,
                'input_voltage': input_voltage,
                'input_states': input_states,
                'output_states': output_states,
                'alarm_line_states': "{:02x}".format(Z1) + "{:02x}".format(Z2) + "{:02x}".format(Z3) + "{:02x}".format(
                    Z4),
                'hotel_readers': hotel[0],
                'hotel_readers_card_presence': hotel[1],
                'hotel_readers_buttons_pressed': hotel[2],
                'read_b3_cmd': controller.read_b3_cmd or temperature != 0 or humidity != 0 or controller.alarm_lines > 0
            })
            if temperature != 0 or humidity != 0:
                controller.update_th(0,{
                    't': temperature,
                    'h': humidity,
                })

        command.write({
            'status': 'Success',
            'ex_timestamp': fields.Datetime.now(),
            'response': json.dumps(post_data),
        })

        return self.check_for_unsent_cmd(200)
