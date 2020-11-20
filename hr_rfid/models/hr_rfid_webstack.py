# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from datetime import datetime, timedelta
from ..wizards.helpers import create_and_ret_d_box, return_wiz_form_view
import socket
import http.client
import json
import base64
import pytz
import logging

_logger = logging.getLogger(__name__)

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
        [('pre_discovery', 'pre_discovery'), ('post_discovery', 'post_discovery')],
        default='pre_discovery'
    )

    @api.multi
    def discover(self):
        self.ensure_one()
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_sock.bind(("", 30303))

        send_msg = b'Discovery:'
        res = udp_sock.sendto(send_msg, ('<broadcast>', 30303))
        if res is False:
            udp_sock.close()
            return

        ws_env = self.env['hr.rfid.webstack']

        while True:
            udp_sock.settimeout(0.5)
            try:
                data, addr = udp_sock.recvfrom(1024)
                data = data.decode().split('\n')[:-1]
                data = list(map(str.strip, data))
                if len(data) == 0 or len(data) > 100:
                    continue
                if len(ws_env.search([('serial', '=', data[4])])) > 0:
                    continue
                module = {
                    'last_ip': addr[0],
                    'name': data[0],
                    'version': data[3],
                    'hw_version': data[2],
                    'serial': data[4],
                    'behind_nat': False,
                    'available': 'u',
                }
                env = ws_env.sudo()
                module = env.create(module)
                self.found_webstacks += module
                try:
                    module.action_check_if_ws_available()
                except exceptions.ValidationError as __:
                    pass
            except socket.timeout:
                break

        udp_sock.close()
        self.write({'state': 'post_discovery'})
        return return_wiz_form_view(self._name, self.id)

    @api.multi
    def setup_modules(self):
        self.ensure_one()
        for ws in self.setup_and_set_to_active:
            ws.action_set_webstack_settings()
            ws.active = True

        self.get_controllers()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.multi
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
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


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
    company_id = fields.Many2one(
        'res.company', string='Company', change_default=True,
        default=lambda self: self.env['res.company']._company_default_get(),
        required=True, readonly=True,
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
        selection=[('admin', 'Admin'), ('sdk', 'SDK')],
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
        selection=[('u', 'Unavailable'), ('a', 'Available')],
        string='Available?',
        help='Whether the module was available the last time Odoo tried to connect to it.',
        default='u',
    )

    last_update = fields.Boolean(compute='_last_update_calculate')

    _sql_constraints = [('rfid_webstack_serial_unique', 'unique(serial)',
                         'Serial number for webstacks must be unique!')]

    @api.multi
    @api.depends('write_date')
    def _last_update_calculate(self):
        for r in self:
            if not r.write_date:
                r.last_update = False
                continue
            ten_min_dalay = datetime.now() - timedelta(minutes=10)
            r.last_update = True if r.write_date < ten_min_dalay else False

    @api.one
    def action_set_webstack_settings(self):
        odoo_url = str(self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
        splits = odoo_url.split(':')
        odoo_url = splits[1][2:]
        if len(splits) == 3:
            odoo_port = int(splits[2], 10)
        else:
            odoo_port = 80
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

    @api.one
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
                raise exceptions.ValidationError(_('Webstack sent us http code {}'
                                                 ' when 200 was expected.').format(code))

            js = json.loads(body.decode())
            module = {
                'version': js['sdk']['sdkVersion'],
                'hw_version': js['sdk']['sdkHardware'],
                'serial': js['convertor'],
                'available': 'a',
                'behind_nat': False,
            }
            self.write(module)
        except socket.timeout:
            raise exceptions.ValidationError(_('Could not connect to the module'))
        except(socket.error, socket.gaierror, socket.herror) as e:
            raise exceptions.ValidationError(_('Unexpected error:\n') + str(e))
        except KeyError as __:
            raise exceptions.ValidationError(_('Invalid information returned by the module'))

    @api.depends('tz')
    def _compute_tz_offset(self):
        for user in self:
            user.tz_offset = datetime.now(pytz.timezone(user.tz or 'GMT')).strftime('%z')

    @api.multi
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

    @api.multi
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

