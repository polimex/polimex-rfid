# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from requests import ConnectTimeout

from odoo.addons.hr_rfid.controllers import polimex
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
    """Return the IP address of the machine running the code.

    The method uses a socket to connect to a non-existent IP address (10.255.255.255) with a timeout of 0 seconds.
    This ensures that the socket does not actually establish a connection.
    By calling `getsockname()` on the socket, the local IP address is retrieved.

    :return: The local IP address as a string.
    """
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
    _inherit = ['mail.activity.mixin', 'mail.thread', 'balloon.mixin']
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

    last_update = fields.Boolean(
        string='Contacted in last 10 min',
        compute='_compute_last_update',
        store=True
    )

    commands_count = fields.Char(string='Commands count', compute='_compute_counts')
    system_event_count = fields.Char(string='System Events count', compute='_compute_counts')
    controllers_count = fields.Char(string='Controllers count', compute='_compute_counts')

    _sql_constraints = [('rfid_webstack_serial_unique', 'unique(serial)',
                         'Serial number for webstacks must be unique!')]

    @api.model
    def _notify_inactive(self):
        """
        Notify Inactive

        Notify all records that are inactive and have not been updated within the last 24 hours by creating a todo activity for each record.

        :return: None
        """
        todo_activity_type = self.env.ref('mail.mail_activity_data_todo')

        # Get all records of the model
        all_records = self.search([
            ('active', '=', True),
            ('updated_at', '<', fields.Datetime.now() - relativedelta(days=1)),
        ])

        for record in all_records:
            todo_activity = record.activity_ids.filtered(lambda a: a.activity_type_id == todo_activity_type)
            if not todo_activity:
                for follower in record.message_follower_ids:
                    # If the follower is a user
                    user = self.env['res.users'].search([('partner_id', '=', follower.partner_id.id)], limit=1)
                    if user:
                        # Set the user's language in the context
                        lang_context = self.env.context.copy()
                        lang_context['lang'] = user.lang or 'en_US'

                        # Create the activity with the new context
                        self.env['mail.activity'].with_context(lang_context).create({
                            'activity_type_id': todo_activity_type.id,
                            'res_id': record.id,
                            'res_model_id': self.env['ir.model']._get(self._name).id,
                            'user_id': user.id,
                            'summary': _('Todo Check communication or contact with support team'),
                            'note': _(
                                'This is a automatic Todo activity based on communication statistics with the module.')
                        })

    @api.depends('hw_version')
    def _compute_time_format(self):
        for ws in self:
            if (ws.hw_version and ws.hw_version in ['100.1', '50.1']) or (ws.version and float(ws.version) > 1.40):
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
        """
        Set webstack settings for the module.

        :return: None
        """
        self.ensure_one()
        bad_hosts = ['localhost', '127.0.0.1', '.local']
        odoo_url = str(self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
        odoo_port = len(odoo_url.split(':')) == 3 and int(odoo_url.split(':')[2], 10) or 80
        odoo_protocol = odoo_url.split('//')[0]
        if any([odoo_url.find(bh) < 0 for bh in bad_hosts]):
            local_ip = get_local_ip()
            new_odoo_url = f"{local_ip}"
            if odoo_url == new_odoo_url:
                raise exceptions.ValidationError(
                    _('Your current setup not permit this operation. You need to do it manually.\n '
                      'Please call your support team for more information!'))
            else:
                odoo_url = new_odoo_url
                _logger.info(f"After investigation, the system url is: {odoo_url}")
        odoo_url += '/hr/rfid/event'

        username = str(self.module_username) if self.module_username else ''
        password = str(self.module_password) if self.module_password else ''

        host = str(self.last_ip)
        uart_conf = [
            {"br": 9600, "db": 3, "fc": 0, "ft": 122, "port": 0, "pr": 0, "rt": False, "sb": 1, "usage": 0},
            {"br": 9600, "db": 3, "fc": 0, "ft": 122, "port": 2, "pr": 0, "rt": False, "sb": 1, "usage": 1}
        ]
        config_params_dict = {
            'sdk': 1, 'stsd': 1, 'sdts': 1, 'stsu': odoo_url, 'prt': str(odoo_port),
            'hb': 1, 'thb': 60, 'br': 1, 'odoo': 1,
        }
        try:
            if self.hw_version == '100.1':
                response = requests.post(
                    url=f"http://{host}/protect/uart/conf",
                    json=uart_conf, auth=(username, password), timeout=2
                )
                if response.status_code != 200:
                    raise exceptions.ValidationError(
                        _('''Error received while trying to setup the module!\n 
                          (/protect/uart/conf) returned {reason}({code}) with body:\n''').format(
                            reason=response.reason, code=response.status_code) +
                        response.text
                    )
            if self.hw_version == '10.3':
                del config_params_dict['odoo']
            response = requests.post(
                url=f"http://{host}/protect/config.htm",
                data=config_params_dict, auth=(username, password), timeout=2
            )
            if response.status_code != 200:
                raise exceptions.ValidationError(_('''While trying to setup /protect/config.htm the module\n
                                                 error returned {reason}({code}) with body:\n''').format(
                    reason=response.reason, code=response.status_code) +
                                                 response.text)
            if self.hw_version == '10.3':
                response = requests.post(
                    url=f"http://{host}/protect/reboot.cgi",
                    auth=(username, password), timeout=2
                )
                if response.status_code != 200:
                    raise exceptions.ValidationError(_('''While trying to reboot the module \n
                                                       error returned {response.reason}({response.status_code}) with body:\n''').format(
                        reason=response.reason, code=response.status_code) +
                                                     response.text)
            self.key = None
        except (ConnectionError, ConnectTimeout) as e:
            raise exceptions.ValidationError(_('Could not connect to the module. \n'
                                               "Check if it is turned on or if it's on a different ip.\n") +
                                             f"({str(e)})")
        except (socket.error, socket.gaierror, socket.herror) as e:
            raise exceptions.ValidationError(_('Error while trying to connect to the module.'
                                               ' Information:\n') + str(e))
        except Exception as e:
            raise exceptions.ValidationError(_('Error while trying to connect to the module.'
                                               ' Information:\n') + str(e))
        self.key = None
        return self.balloon_success_sticky(
            title=_('Setup the Module'),
            message=_('Information sent to the Module. If everything is fine, the Module have to start '
                      'communication with this instance. The URL in use is http://%s on port %d.', odoo_url, odoo_port)
        )

    def action_check_if_ws_available(self):
        for ws in self:
            host = str(ws.last_ip)
            try:
                response = requests.get(f"http://{host}/config.json", timeout=5)
                if response.status_code != 200:
                    raise exceptions.ValidationError(_('Error response from Webstack. {} ({})').format(
                        response.reason,
                        response.status_code
                    ))

                # js = json.loads(response.json())
                js = response.json()
                module = {
                    'version': js['sdk']['sdkVersion'],
                    'hw_version': js['sdk']['sdkHardware'],
                    'serial': js['convertor'],
                    'available': 'a',
                }
                ws.write(module)
            except (ConnectionError, ConnectTimeout) as e:
                raise exceptions.ValidationError(
                    _('Could not connect to the module. \n'
                      "Check if it is turned on or if it's on a different ip.\n") +
                    f"({str(e)})")
            except KeyError as e:
                raise exceptions.ValidationError(_('Information returned by the webstack invalid: \n') + str(e))
            except Exception as e:
                raise exceptions.ValidationError(_('Module connection error:\n') + str(e))
        return self.balloon_success(
            title=_('Check connection to the Module'),
            message=_('Everything looks just great!')
        )

    def get_controllers(self):
        """
        Retrieve the list of controllers from the webstack.

        :return: an action to open the controller view if controllers are found, or a warning balloon message if no controllers are detected or the webstack is archived.
        """
        controllers = None
        for ws in self:
            if ws.behind_nat or not ws.active:
                continue
            host = str(ws.last_ip)
            try:
                response = requests.get(f'http://{host}/config.json', timeout=2)
                if response.status_code != 200:
                    raise exceptions.ValidationError(_('Webstack sent us error {}({}) \n'
                                                       ' while requesting device list')
                                                     .format(response.reason, response.status_code))
                js = response.json()
                controllers = js['sdk']['devFound']
                if ws.name == f"Module {ws.serial}":
                    ws.name = f"Module {ws.serial} ({js['netConfig']['Host_Name']})"
                if not isinstance(controllers, int):
                    raise exceptions.ValidationError(_('Webstack gave us bad data when requesting /config.json'))

                for dev in range(controllers):
                    response = requests.get(f'http://{host}/sdk/status.json?dev={dev}')

                    if response.status_code != 200:
                        raise exceptions.ValidationError(_('Webstack sent us error {}({}) \n'
                                                           ' while requesting information for controller {}')
                                                         .format(response.reason, response.status_code, dev))
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
            except (ConnectionError, ConnectTimeout) as e:
                raise exceptions.ValidationError(
                    _('Could not connect to the module. \n'
                      "Check if it is turned on or if it's on a different ip:\n") +
                    str(e))
            except KeyError as __:
                raise exceptions.ValidationError(_('Information returned by the webstack at {} is invalid', host))
            except Exception as e:
                raise exceptions.ValidationError(_('Unexpected communication error:\n') + str(e))
        if controllers:
            return self.with_context(xml_id='hr_rfid_ctrl_action').return_action_to_open()
        else:
            return self.balloon_warning(
                title=_('Reading controllers from the Module'),
                message=_('No controllers detected in the Module or the Module is Archived')
            )

    def reboot_cmd(self):
        """
        Reboots the module.

        :return: None
        """
        for ws in self:
            username = str(ws.module_username) if ws.module_username else ''
            password = str(ws.module_password) if ws.module_password else ''

            host = str(ws.last_ip)
            try:
                if self.hw_version == '100.1':
                    response = requests.get(
                        url=f"http://{host}/protect/restart",
                        auth=(username, password), timeout=2
                    )
                    if response.status_code != 200:
                        raise exceptions.ValidationError(
                            _('''Error received while trying to reboot the module!\n 
                              Return {reason}({code}) with body:\n''').format(
                                reason=response.reason, code=response.status_code) +
                            response.text
                        )
                if self.hw_version == '10.3':
                    response = requests.post(
                        url=f"http://{host}/protect/reboot.cgi",
                        auth=(username, password), timeout=2
                    )
                    if response.status_code != 200:
                        raise exceptions.ValidationError(_('''While trying to reboot the module \n
                                                           error returned {response.reason}({response.status_code}) with body:\n''').format(
                            reason=response.reason, code=response.status_code) +
                                                         response.text)
            except (ConnectionError, ConnectTimeout) as e:
                raise exceptions.ValidationError(_('Could not connect to the module. \n'
                                                   "Check if it is turned on or if it's on a different ip.\n") +
                                                 f"({str(e)})")
            except Exception as e:
                raise exceptions.ValidationError(_('Error while trying to connect to the module.'
                                                   ' Information:\n') + str(e))
            return self.balloon_success_sticky(
                title=_('Reboot the Module'),
                message=_('The module was rebooted. It takes up to 10 sec to restore the work conditions')
            )

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
        """
        :param error_description: (str) Description of the error that occurred.
        :param input_json: (str) JSON input for the logs.
        :return: None

        This method is used to log system errors and input JSON in the HR RFID webstack. It creates a new record in the 'hr.rfid.event.system' model with the following fields:
        - webstack_id: The ID of the current webstack.
        - timestamp: The current date and time.
        - error_description: The description of the error that occurred.
        - input_json: The input JSON for the logs.

        Example Usage:
            hr_rfid_webstack = HrRfidWebstack()
            hr_rfid_webstack.sys_log("Error occurred", "{\"key\": \"value\"}")
        """
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
    def _execute_direct_cmd(self, cmd: dict, retry=0):
        """
        :param cmd: A dictionary containing the command to be executed
        :param retry: Number of times to retry the command if it fails (default is 0)
        :return: The result of the command execution

        This method is used to execute a command directly to a remote module using HTTP requests.
        The command is provided as a dictionary in the `cmd` parameter. The `retry` parameter specifies the number of times to retry the command if it fails.

        Example usage:
            cmd = {
                'cmd': {
                    'c': 'F9',
                    'param1': 'value1',
                    'param2': 'value2'
                }
            }
            result = self._execute_direct_cmd(cmd, retry=3)
        """
        self.ensure_one()
        username = self.module_username and str(self.module_username) or ''
        password = self.module_password and str(self.module_password) or ''
        timeout = 2
        try:
            _logger.info('Direct sending %s' % str(cmd))
            if cmd['cmd']['c'] in ['F9']:
                timeout = 5
            response = requests.post(f'http://{self.last_ip}/sdk/cmd.json', auth=(username, password), json=cmd,
                                     timeout=timeout)
            result = None
            if response.status_code == 200:
                result = response.json()
            else:  # response.status_code != 200:
                _logger.error('While trying to send the command to the module, '
                              'it returned code ' + str(response.status_code) + ' with body:\n'
                              + response.content.decode())
                if retry < 3:
                    result = self._execute_direct_cmd(cmd, retry + 1)
                if not result:
                    raise exceptions.ValidationError(_('While trying to send the command to the module, '
                                                       'it returned code {} with body:\n', str(response.status_code))
                                                     + response.content.decode())
            _logger.info('Direct receiving %s' % str(result))
            return result
        except requests.exceptions.ReadTimeout as __:
            _logger.error(f'Timeout {str(__.args)}')
        # except json.decoder.JSONDecodeError as __:
        #     _logger.error(f'JSON decoder error {str(__.args)} in {}')
        except Exception as e:
            _logger.exception(tools.exception_to_unicode(e))
            # raise

    def direct_execute(self, cmd: dict, command_id: models.Model = None):
        """
        :param cmd: A dictionary that contains the command to be executed.
        :param command_id: (optional) A model instance representing a stored command.
        :return: The response from the command execution.

        This method is used to execute a command directly. If the parameter "command_id" is provided, the method will execute the stored command represented by that model instance. If no "command_id" is provided, the method will execute the command specified in the "cmd" parameter.

        If "command_id" is provided, the method will execute the stored command by calling the "_execute_direct_cmd" method of the associated "webstack_id" model instance, passing the command as a parameter. The method will then check if a response is received and call the "parse_response" method of the "webstack_id" model instance to process the response. If no response is received, the status of the "command_id" will be set to "Wait". The method will return the response from the command execution.

        If no "command_id" is provided, the method will execute the command by calling the "_execute_direct_cmd" method of the current model instance, passing the command as a parameter. The method will then return the response from the command execution.
        """
        if command_id:
            # TODO Direct execution of stored commands
            cmd_response = command_id.webstack_id._execute_direct_cmd({'cmd': command_id.send_command(200)['cmd']})
            if cmd_response:
                command_id.webstack_id.parse_response(cmd_response, direct_cmd=True)
            else:
                command_id.status = 'Wait'
            return cmd_response
        else:
            for ws in self:
                # TODO Store command in model as in execution
                cmd_response = ws._execute_direct_cmd(cmd)
                return cmd_response

    def is_10_3(self):
        """
        Check if the hardware version is '10.3' or the version number is less than 1.40 for all instances of `HrRfidWebstack`.

        :return: True if all instances meet the conditions, False otherwise.
        """
        return all([(ws.hw_version == '10.3') or (float(ws.version) < 1.40) for ws in self])

    def is_50_1(self):
        return all([ws.hw_version == '50.1' for ws in self])

    def is_100_1(self):
        return all([(ws.hw_version == '100.1') and (float(ws.version) > 1.40) for ws in self])

    def in_cmd_execution(self):
        return self.env['hr.rfid.command'].search_count([
            ('webstack_id', 'in', self.mapped('id')),
            ('status', '=', 'Process')
        ]) > 0

    def count_cmds_in(self, seconds=10):
        dt = fields.Datetime.now() - relativedelta(seconds=seconds)
        return self.env['hr.rfid.command'].with_user(
            SUPERUSER_ID).search_count([
            ('webstack_id', 'in', self.ids),
            ('ex_timestamp', '>', dt)
        ])

    def is_limit_executed_cmd_reached(self):
        """
        Check if the limit of executed commands has been reached.

        :return: True if the limit is reached, False otherwise
        """
        return self.count_cmds_in(
            polimex.MAX_DIRECT_EXECUTE_TIME) > polimex.MAX_DIRECT_EXECUTE or self.in_cmd_execution()

    def get_ws_time(self, post_data: dict):
        """
        :param post_data: A dictionary containing 'date' and 'time' as keys, with their corresponding values.
        :return: A datetime object representing the time retrieved from the web service.

        This method takes in a dictionary of post_data, containing the date and time retrieved from the web service.
        It ensures that there is only one record in the current model instance.
        The 'date' and 'time' values are combined into a string 't', with a format fix for the WiFi module.
        The 't' string is then converted into a datetime object 'ws_time' using the self.time_format specified in the model.
        An offset is subtracted from 'ws_time' to adjust for the timezone.
        If 't' cannot be converted into a datetime object, a BadTimeException is raised.
        The resulting 'ws_time' is returned.
        """
        self.ensure_one()
        t = f"{post_data['date']} {post_data['time']}"
        t = t.replace('-', '.')  # fix for WiFi module format
        try:
            # _logger.info('------------------------t=%s, format=%s', t, self.time_format)
            ws_time = datetime.strptime(t, self.time_format)
            ws_time -= self._get_tz_offset()
            # _logger.info('------------------------ws_time=%s',ws_time)
        except ValueError:
            raise BadTimeException
        return ws_time

    def get_ws_time_str(self, post_data: dict):
        self.ensure_one()
        return self.get_ws_time(post_data).strftime('%Y-%m-%d %H:%M:%S')

    def _retry_command(self, status_code, cmd, event=None):
        if cmd.retries == 5:
            cmd.status = 'Failure'
            return self.check_for_unsent_cmd(status_code, event)

        cmd.retries = cmd.retries + 1

        if event is not None:
            event.command_id = cmd
        return cmd.send_command(status_code)

    def check_for_unsent_cmd(self, status_code, event=None):
        """
        :param status_code: The status code of the command to be checked.
        :param event: The corresponding event object. Defaults to None.
        :return: If there are processing commands, it retries the command based on the status code and event.
                 If there are waiting commands, it sends the command based on the status code and event.
                 If there are no commands, it returns the status code.

        """
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

    def report_sys_ev(self, description, post_data=None, controller_id=None, sys_ev_dict: dict = None):
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

        def get_timestamp(data: dict):
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
            if not 'error_description' in sys_ev_dict:
                sys_ev_dict['error_description'] = description
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

    def parse_response(self, post_data: dict, direct_cmd=False):
        """
        :param post_data: A dictionary containing the response data received from a request.
        :param direct_cmd: A boolean indicating whether the command was sent directly or not.
        :return: None

        This method parses the response received from a controller and performs actions based on the command type and response data. It updates the status and response fields of the corresponding command record. If the response indicates an error, it handles the error accordingly. It also updates various fields of the controller based on the response data for different command types.
        """
        self.ensure_one()
        command_env = self.env['hr.rfid.command'].with_user(SUPERUSER_ID)
        response = post_data['response']
        controller = self.controllers.filtered(lambda c: c.ctrl_id == response.get('id', -1)).with_context(
            no_output=True)
        if not controller:
            self.report_sys_ev(_('Module sent us a response from a controller that does not exist'),
                               post_data=post_data)
            return not direct_cmd and self.check_for_unsent_cmd(200)

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
            controller.report_sys_ev(_('Controller sent us a response to a command we never sent'))
            return not direct_cmd and self.check_for_unsent_cmd(200)

        # controller not response!
        if response['e'] != 0:
            if response['e'] == 20:  # controller not response!
                return self._retry_command(200, command)
            command.write({
                'status': 'Failure',
                'error': str(response['e']),
                'ex_timestamp': fields.Datetime.now(),
                'response': json.dumps(post_data),
            })
            return not direct_cmd and self.check_for_unsent_cmd(200)

        command.write({
            'status': 'Success',
            'ex_timestamp': fields.Datetime.now(),
            'response': json.dumps(post_data),
        })

        if response['c'] == 'F0':
            command.parse_f0_response(post_data=post_data)

        if response['c'] == 'F2':
            if len(response['d']) == 10:  # card counter only
                controller.cards_count = polimex.bytes_to_num(response['d'], 0, 5)
                if controller.is_temperature_ctrl():
                    controller.read_cards_cmd(position=1, count=controller.cards_count)
                else:
                    pass
            else:  # card list
                if controller.is_temperature_ctrl():
                    sensors = []
                    for block in [response['d'][i * 36:i * 36 + 36] for i in range(0, len(response['d']) // 36)]:
                        barray = polimex.str_hex_to_array(block)
                        sensor_uid = ''.join([f'{c:x}' for c in barray[0:16]])
                        sensor_id = barray[16]
                        sensor_flag = barray[17]
                        # controller.update_th(0, {
                        #     't': temperature,
                        #     'h': humidity,
                        # })
                        th_id = controller.sensor_ids.filtered(lambda s: s.uid == sensor_uid)
                        if not th_id:
                            self.env['hr.rfid.ctrl.th'].create({
                                'name': _('External Sensor %s connected to %s') % (
                                    len(controller.with_context(active_test=False).sensor_ids),
                                    controller.name
                                ),
                                'uid': sensor_uid,
                                'internal_number': sensor_id,
                                'active': sensor_flag == 1,
                                'controller_id': controller.id,
                                'sensor_number': len(controller.with_context(active_test=False).sensor_ids),
                            })
                        # if not th_id:
                        #     controller.write({
                        #         'sensor_ids': [(0, 0, {
                        #             'name': _('External Sensor {} on {}').format(len(controller.sensor_ids),
                        #                                                          controller.name),
                        #             'uid': sensor_uid,
                        #             'internal_number': sensor_id,
                        #             'active': sensor_flag == 1,
                        #             'controller_id': controller.id,
                        #             'sensor_number': len(controller.sensor_ids),
                        #         })]
                        #     })
                    pass
                else:
                    pass
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
            if command.cmd_data != '00':  # receiving single line from IOTable
                controller.change_io_table(new_io_table=response['d'], line=int(command.cmd_data, 16), no_command=True)
            else:
                controller.write({
                    'io_table': response['d']
                })

        if response['c'] == 'FB':
            input_masks = 0
            byte_data = bytes.fromhex(response['d'])
            for i in range(4):
                input_masks += byte_data[i] & 0x7F << (i * 8)
            controller.process_input_masks(input_masks)

        if response['c'] == 'FC':
            apb_mode = response['d']
            for door in controller.door_ids:
                door.apb_mode = (door.number == '1' and (apb_mode & 1)) \
                                or (door.number == '2' and (apb_mode & 2))
        if response['c'] == 'B1':
            if response['d'] != '00':
                # '01 0400 0050 0010'
                high_temp = polimex.get_temperature(int(response['d'][2:4]), int(response['d'][4:6]))
                low_temp = polimex.get_temperature(int(response['d'][6:8]), int(response['d'][8:10]))
                hyst = polimex.get_temperature(int(response['d'][10:12]), int(response['d'][12:14]))
                controller.with_context(readed=True).write({
                    'high_temperature': high_temp,
                    'low_temperature': low_temp,
                    'hysteresis': hyst
                })

        if response['c'] == 'B3':
            data = response['d']
            # 0000 0100 0711 0000 0000 0000 000000000000000000000000
            # '5a0000000719000000000000020202020000000000000000' iCON180
            input_states = (int(data[0:2], 16) & 0x7f) + ((int(data[2:4], 16) & 0x7f) << 7)
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
                controller.update_th(sensor_number=0, data_dict={
                    't': temperature,
                    'h': humidity,
                })

        if response['c'] == 'D1':
            # 00 00 00 00 01
            if not controller.is_temperature_ctrl:
                controller.cards_count = polimex.bytes_to_num(response['d'], 0, 5)
                db_count = [d.card_rel_id for d in controller.door_ids]
                waiting_cmd = self.env['hr.rfid.command'].search_count(
                    [('controller_id', '=', controller.id), ('status', '=', 'Wait')]) == 0
                if db_count != controller.cards_count and waiting_cmd:
                    controller.report_sys_ev(
                        _('Card count in controller and DB are different. Reload cards to solve the problem'),
                        post_data=post_data)
        if response['c'] == 'DB':
            # 00 00 00 00 01
            out_num = polimex.bytes_to_num(response['d'], 0, 1)
            out_state = polimex.bytes_to_num(response['d'], 2, 1)
            out_timer = len(response['d']) == 6
            if out_num == 99:  # emergency control
                controller._update_input_state(14, out_state)
                # _logger.info('After DB Controller %s emergency state %s', controller.name, controller.emergency_state)
            elif not out_timer:
                controller._update_output_state(out_num, out_state)

        return not direct_cmd and self.check_for_unsent_cmd(200)
