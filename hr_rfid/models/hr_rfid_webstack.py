# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from requests import ConnectTimeout

from odoo.addons.hr_rfid.controllers import polimex
from odoo import api, fields, models, exceptions, _, SUPERUSER_ID, tools, Command
from datetime import datetime, timedelta
import socket
import http.client
import requests
import json
import base64
import pytz

import logging

_logger = logging.getLogger(__name__)

# Upper bound on the controllers a single heartbeat may provision — defence in
# depth against an oversized/hostile `controllers` array from an (authenticated)
# module. The hardware bus tops out at 64 devices (`maxDevInList` in the module
# SDK), so a larger list is never a real bus and is ignored wholesale.
MAX_DETECTED_CONTROLLERS = 64

# How long a module may stay silent before a presence scan counts it as a miss.
# Comfortably above the 60 s heartbeat Odoo provisions (`_setup_module`,
# 'thb': 60), so a single dropped check-in is never enough on its own.
PRESENCE_WINDOW_MINUTES = 10

# ...and how many scans in a row must miss before the operator is told the
# module is dark. Only Odoo-provisioned modules are guaranteed to beat every
# minute: a module behind NAT is configured by hand on the device itself, and
# one whose interval exceeds the window would otherwise flip green/orange on
# every pass - an indicator nobody would trust. Coming back is not delayed by
# this: the first check-in clears it immediately.
PRESENCE_MISSES_BEFORE_DARK = 3

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

    _serial_uniq = models.Constraint(
        "UNIQUE (serial)",
        "A module with this serial number already exists!")

    name = fields.Char(
        string='Name',
        help='Enter a descriptive name to identify this module (e.g., "Main Building Module" or "Warehouse Gate Module"). This helps you manage multiple modules in your system.',
        required=True,
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 help='Select which company this module belongs to. Controllers and access rights will be managed within this company context.',
                                 default=lambda self: self.env.company)
    shared_company_ids = fields.Many2many(
        comodel_name='res.company',
        relation='hr_rfid_webstack_shared_company_rel',
        column1='webstack_id',
        column2='company_id',
        string='Shared With',
        help='Other companies that use this module together with the owner company. '
             'They can see its controllers, doors and readers and grant access to '
             'their own people with their own access groups. Setting up the module '
             'and its hardware, and how long its events are kept, stay with the '
             'owner company.',
        tracking=True,
    )
    tz = fields.Selection(
        _tz_get,
        string='Timezone',
        default=lambda self: self.env.context.get('tz'),
        help='Select the timezone where this module is physically located. This ensures accurate time synchronization between the module and Odoo for access logs and schedules.',
    )

    tz_offset = fields.Char(
        string='Timezone offset',
        compute='_compute_tz_offset',
        help='Automatically calculated timezone offset from UTC (e.g., +0200 for UTC+2). Used internally for time synchronization.',
    )
    time_format = fields.Char(
        compute='_compute_time_format',
        help='Time format used by this module based on its hardware version. Automatically determined.',
    )

    serial = fields.Char(
        string='Serial number',
        help='Unique 6-digit serial number printed on the module hardware. This is automatically detected when the module connects to Odoo. Contact support if you need to register a new module.',
        size=6,
        index=True,
        readonly=True,
    )

    # `key` is a DELEGATED field: it lives on the shared per-serial
    # polimex.ws.endpoint (module polimex_ws) so a device that is both an AC
    # module and an IoT gateway shares ONE credential (the double-key fix). It
    # is read/written transparently as `webstack.key`; the storage is the
    # endpoint. See hr_rfid_webstack_ws.py for the _inherits delegation. proto 3
    # is trust-on-first-use (default False): a keyless module adopts the device's
    # key on the first authenticated check-in (_authenticate_webstack /
    # _ws_check_hello) rather than defaulting to "0000".

    active = fields.Boolean(
        string='Active',
        help='Enable this to allow the module to communicate with Odoo. When disabled, the module will not be able to send events or receive commands. Useful for maintenance or troubleshooting.',
        default=False,
        tracking=True,
    )

    version = fields.Char(
        string='Version',
        help='Firmware version running on the module. This is automatically detected. Contact support if an update is needed.',
        size=6,
    )

    hw_version = fields.Char(
        string='Hardware Version',
        help='Hardware model/version of the module (e.g., 10.3, 50.1, 100.1). This determines the module\'s capabilities and supported features.',
        size=6,
    )

    behind_nat = fields.Boolean(
        string='Behind NAT',
        help='Enable if the module is behind a firewall/router (most common). When enabled, the module initiates connection to Odoo. When disabled, Odoo can directly connect to the module\'s IP address.',
        required=True,
        default=True,
    )

    last_ip = fields.Char(
        string='Last IP',
        help='The IP address the module last connected from. For modules behind NAT, this is the public IP. For direct connection modules, this is used to send commands.',
        size=26,
    )

    updated_at = fields.Datetime(
        string='Last Update',
        help='Last time this module communicated with Odoo. If this is more than 10 minutes ago, the module may be offline or experiencing connection issues.',
    )

    controllers = fields.One2many(
        'hr.rfid.ctrl',
        'webstack_id',
        string='Controllers',
        help='List of access control devices connected to this module. Each controller manages doors, readers, and access permissions. Click "Read controllers" to auto-detect connected devices.'
    )

    http_link = fields.Char(
        compute='_compute_http_link',
        help='Direct web interface link to the module. Only available when "Behind NAT" is disabled. Click to access the module\'s configuration page.',
    )

    module_username = fields.Selection(
        selection=[('admin', 'admin'), ('sdk', 'SDK')],
        string='Module Username',
        help='Username for accessing the module\'s web interface. Use "admin" for full access or "SDK" for API access only. Must match the username configured in the module.',
        default='admin',
    )

    module_password = fields.Char(
        string='Module Password',
        help='Password for the module\'s web interface. Must match the password configured in the module. Required for direct connection and module configuration.',
        default='',
    )

    available = fields.Selection(
        selection=[
            ('u', 'Unavailable'),
            ('a', 'Available')
        ],
        string='Available?',
        help='Connection status indicator:\n• Available (green): Module is online and responding\n• Unavailable (red): Module is offline or not responding\nUpdated when using "Test module connection" button.',
        default='u',
    )

    presence_misses = fields.Integer(
        string='Missed presence checks',
        readonly=True,
        default=0,
        help='How many presence scans in a row found this module silent. '
             'Reset by the next contact; the module is reported as dark only '
             'once the count reaches its limit.',
    )

    last_update = fields.Boolean(
        string='Contacted recently',
        readonly=True,
        help='Whether the module is currently reachable. Set when it checks in '
             'and cleared by the presence scan once it has been silent for too '
             'long - a module that goes dark cannot report it itself.',
    )

    commands_count = fields.Char(
        string='Commands count',
        compute='_compute_counts',
        help='Total number of commands sent to this module. Includes pending, successful, and failed commands.',
    )
    system_event_count = fields.Char(
        string='System Events count',
        compute='_compute_counts',
        help='Total number of system events logged by this module. Includes errors, warnings, and diagnostic information.',
    )
    controllers_count = fields.Char(
        string='Controllers count',
        compute='_compute_counts',
        help='Number of controllers currently connected to this module. Each controller manages doors and readers.',
    )

    _rfid_webstack_serial_unique = models.Constraint(
        'UNIQUE(serial)',
        'Serial number for Module must be unique!'
    )

    def _is_reachable(self, window_minutes=PRESENCE_WINDOW_MINUTES):
        """Has this module been heard from within the window?

        Transport-aware on purpose: a module on the real-time channel never
        writes ``updated_at`` (the websocket ingress stamps ``ws_last_seen``
        instead), so a check on the HTTP timestamp alone would report every
        healthy real-time module as dead.
        """
        self.ensure_one()
        if self.ws_online:
            return True
        deadline = fields.Datetime.subtract(fields.Datetime.now(), minutes=window_minutes)
        return bool(self.updated_at and self.updated_at > deadline)

    def _touch_from_device(self, vals):
        """Record a check-in, and announce it only if the module was dark.

        The stamps in ``vals`` are telemetry and deliberately do not reach the
        monitoring screens. But a module coming BACK is news, and it is news
        nobody else can deliver: the presence scan below would find the module
        already reachable and have nothing to write. So the up-transition rides
        along on this very write, as a field the gate does not ignore.
        """
        self.ensure_one()
        if not self.last_update:
            vals = dict(vals, last_update=True)
        if self.presence_misses:
            # Start the tolerance from scratch, or a module that flaps twice in
            # a row would be declared dark on its first miss the second time.
            vals = dict(vals, presence_misses=0)
        return self.write(vals)

    @api.model
    def _cron_check_presence(self):
        """Turn the ABSENCE of device traffic into something the operator sees.

        No bus message can announce silence: the device that should send it is
        precisely the one that stopped talking. Hence a server-side scan, the
        same shape core uses for unjustified absence
        (``hr_attendance._cron_absence_detection``).

        Only real changes are written, so a healthy fleet costs zero writes and
        zero bus rows. One module failing must not leave the rest of the fleet
        on a stale state until someone notices, so each is isolated.
        """
        for module in self.search([('active', '=', True)]):
            try:
                with self.env.cr.savepoint():
                    module._apply_presence_check()
            except Exception:
                _logger.warning(
                    'Presence check failed for module %s (id=%s); its state is '
                    'left as it was and the scan continues with the rest',
                    module.name, module.id, exc_info=True)

    def _apply_presence_check(self):
        """One module's verdict for this pass.

        Going dark needs `PRESENCE_MISSES_BEFORE_DARK` misses in a row, so a
        module whose check-in interval is longer than the window is tolerated
        instead of flapping. Coming back needs nothing: any contact clears both
        the counter and the flag. Once a module IS reported dark nothing more is
        written, so a site that is off for a week costs one write, not one per
        scan.
        """
        self.ensure_one()
        if self._is_reachable():
            vals = {}
            if self.presence_misses:
                vals['presence_misses'] = 0
            if not self.last_update:
                vals['last_update'] = True
            if vals:
                self.write(vals)
        elif self.last_update:
            misses = self.presence_misses + 1
            vals = {'presence_misses': misses}
            if misses >= PRESENCE_MISSES_BEFORE_DARK:
                vals['last_update'] = False
            self.write(vals)

    @api.model
    def _notify_inactive(self):
        """
        Notify Inactive

        Notify all records that are inactive and have not been updated within the last 24 hours by creating a todo activity for each record.

        :return: None
        """
        todo_activity_type = self.env.ref('mail.mail_activity_data_todo')

        # Get all records of the model. Reachability is checked per record
        # rather than in the domain because a real-time module reports over the
        # websocket and never writes updated_at - selecting on that column alone
        # would raise a daily Todo for every healthy module on the WS fleet.
        # A module that has NEVER checked in is not a communication failure -
        # it is an unfinished installation, and the old SQL domain excluded it
        # for free (NULL < x is never true). Keep that, or every module created
        # by the discovery wizard would nag its followers within the minute.
        all_records = self.search([('active', '=', True), ('updated_at', '!=', False)]).filtered(
            lambda m: not m._is_reachable(window_minutes=24 * 60))

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
            # The FW version comes verbatim from the device; a non-numeric
            # value must not poison this compute (and with it every event
            # parse) - _version_num falls back to 0.0 -> legacy format.
            new_fw = ws._version_num() > 1.40
            if (ws.hw_version and ws.hw_version in ['100.1', '50.1']) or new_fw:
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
            except KeyError:
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

    def _check_owner_only_change(self):
        """Ownership, sharing and deletion of a module are reserved for the
        owner company. Without this guard a manager of a company the module is
        merely shared with could re-own the device (write company_id), drop
        the owner from it or delete it altogether."""
        if self.env.su or self.env.user.has_group('base.group_system'):
            return
        for ws in self:
            if ws.company_id and ws.company_id not in self.env.user.company_ids:
                raise exceptions.AccessError(self.env._(
                    'Only the company that owns the module "%s" can change its '
                    'owner or sharing, or delete it.', ws.name))

    def _revoke_shared_company_access(self, companies):
        """A company removed from the sharing list loses every grant its
        access groups hold on this module's doors. The unlink cascade drops
        the card-door relations and queues the remove-card commands."""
        self.ensure_one()
        self.env['hr.rfid.access.group.door.rel'].sudo().search([
            ('door_id.webstack_id', '=', self.id),
            ('access_group_id.company_id', 'in', companies.ids),
        ]).unlink()
        # Post-condition sweep: the cascade above skips cards that are not
        # "ready" right now (e.g. expired but not yet deactivated by the cron)
        # and stale grant rows without a covering access-group link. Their
        # unlink() queues the remove-card commands itself.
        self.env['hr.rfid.card.door.rel'].sudo().search([
            ('door_id.webstack_id', '=', self.id),
            ('card_id.company_id', 'in', companies.ids),
        ]).unlink()
        # sudo: the acting user may be an owner-company manager who cannot
        # read the removed company's record; the note must still name it.
        self.message_post(body=self.env._(
            'Sharing removed for %s. Their access to the doors of this module '
            'was revoked.', ', '.join(companies.sudo().mapped('name'))))

    @api.constrains('shared_company_ids')
    def _check_shared_card_number_collisions(self):
        # Defence in depth: the per-grant check lives on hr.rfid.card.door.rel;
        # this catches a sharing change that would legalise an already
        # conflicting grant set (e.g. re-adding a company via import paths).
        # NB: a Many2many READ is filtered by the reader's company visibility,
        # so every internal read of shared_company_ids goes through sudo.
        for ws in self:
            if ws.sudo().shared_company_ids:
                ws.controllers.door_ids.card_rel_ids._check_shared_module_card_collision()

    def write(self, vals):
        if 'company_id' in vals or 'shared_company_ids' in vals:
            self._check_owner_only_change()
        # Snapshot what the post-write reactions need to compare against.
        # sudo on the M2M: its read is filtered by the reader's company
        # visibility, so an owner manager who cannot see the removed company
        # would otherwise compute an empty diff and skip the revocation.
        old_shared = ({ws: ws.sudo().shared_company_ids for ws in self}
                      if 'shared_company_ids' in vals else {})
        old_tz = {ws: ws.tz for ws in self} if 'tz' in vals else {}

        res = super(HrRfidWebstack, self).write(vals)

        commands_env = self.env['hr.rfid.command']
        for ws, tz in old_tz.items():
            if tz == ws.tz:
                continue
            for ctrl in ws.controllers:
                commands_env.create([{
                    'webstack_id': ctrl.webstack_id.id,
                    'controller_id': ctrl.id,
                    'cmd': 'D7',
                }])
        for ws, shared in old_shared.items():
            removed = shared - ws.sudo().shared_company_ids
            if removed:
                ws._revoke_shared_company_access(removed)
        return res

    def unlink(self):
        self._check_owner_only_change()
        return super(HrRfidWebstack, self).unlink()

    # Commands to all controllers in webstack
    def _sync_clocks(self):
        for ws in self:
            ws.controllers.synchronize_clock_cmd()

    # Log system event for this webstack/s
    def sys_log(self, error_description, input_json=None):
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
        except requests.exceptions.ReadTimeout as e:
            _logger.error('Timeout %s', e.args)
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
            cmd_response = None
            try:
                cmd_response = command_id.webstack_id._execute_direct_cmd(
                    {'cmd': command_id.send_command(200)['cmd']})
                if cmd_response:
                    command_id.webstack_id.parse_response(cmd_response, direct_cmd=True)
                else:
                    command_id.status = 'Wait'
            except Exception as e:
                _logger.error('Direct execute failed for command %s on %s: %s',
                              command_id.cmd, command_id.controller_id.name, e)
                command_id.status = 'Wait'
            return cmd_response
        else:
            for ws in self:
                # TODO Store command in model as in execution
                cmd_response = ws._execute_direct_cmd(cmd)
                return cmd_response

    def _version_num(self):
        """FW version as a float, 0.0 for a missing / non-numeric value.

        The version string comes verbatim from the device (the classic
        heartbeat ``FW`` and the websocket ``hello`` ``fw``), so it is
        untrusted input and must never raise into a compute or a command
        builder. Single source of the parse for ``is_10_3`` / ``is_100_1`` /
        ``_compute_time_format``.
        """
        self.ensure_one()
        try:
            return float(self.version) if self.version else 0.0
        except (TypeError, ValueError):
            return 0.0

    def is_10_3(self):
        """
        Check if the hardware version is '10.3' or the version number is less than 1.40 for all instances of `HrRfidWebstack`.

        :return: True if all instances meet the conditions, False otherwise.
        """
        return all([(ws.hw_version == '10.3') or (ws._version_num() < 1.40) for ws in self])

    def is_50_1(self):
        return all([ws.hw_version == '50.1' for ws in self])

    def is_100_1(self):
        return all([(ws.hw_version == '100.1') and (ws._version_num() > 1.40) for ws in self])

    @api.model
    def _serial_is_100_1(self, serial):
        """SSOT device-model test: an iCON1XX 100.1 is identified by its SERIAL.

        Owner 2026-07-14: every 100.1 ships a serial starting with '4'; neither
        legacy 10.3 nor 50.1 ever do. The serial rides in the ``convertor``
        field of EVERY device POST (and is set at auto-create), so a 100.1 is
        identified from the very FIRST packet of a fresh HTTP re-discovery -
        before hw_version (absent over the HTTP heartbeat) or version (absent
        until the first heartbeat parse) exist. Taking the serial as the
        argument (not a record) lets a caller decide from
        ``post_data['convertor']`` before the webstack is even authenticated.

        Two uses, both keyed off this single fact:
        - PLAIN wire (INTEROP 2026-07-13): a 100.1 gets the bare plain-JSON
          reply; without this the plain ack collapsed to the legacy empty-body
          path and a re-discovered 100.1 command hung in "Process". Legacy 10.3
          (serial not '4') stays on the cmd-only wire.
        - WS AUTO-ENABLE (owner 2026-07-14): a 100.1 supports the real-time
          channel, so it is turned on automatically at discovery (opt-out) -
          no manual "Enable real-time" click needed for it to come up.
        """
        return (str(serial) if serial else '').startswith('4')

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
        if cmd.retries >= 5:
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

        # Websocket event-batch seam: over WS a queued command is delivered as
        # its own hr_rfid.cmd publish (create-publish / sync-on-connect /
        # re-publish cron), NOT piggybacked per event. Without this guard,
        # EACH event in a batch would re-enter here, flip/retry the same
        # pending command and burn its retry budget to a false silent Failure
        # (the batch is one transaction - the device cannot answer between
        # events). The handler runs the piggyback for at most the first event
        # of a batch (ws_skip_piggyback set once a command was captured).
        if self.env.context.get('ws_skip_piggyback'):
            return {'status': status_code}

        commands_env = self.env['hr.rfid.command'].sudo()
        processing_comm = commands_env.search([
            ('webstack_id', '=', self.id),
            ('status', '=', 'Process'),
        ], order='id asc', limit=1)

        if processing_comm:
            return self._retry_command(status_code, processing_comm, event)

        command_id = commands_env.search([
            ('webstack_id', '=', self.id),
            ('status', '=', 'Wait'),
        ], order='id asc', limit=1)

        if not command_id:
            return {'status': status_code}

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
        # Write the firmware version only when it actually changed. The value is
        # the same string on every heartbeat, but the assignment still goes
        # through Field.__set__ -> write() (odoo/orm/fields.py), so an
        # unconditional write broadcasts a dashboard refresh once per module per
        # heartbeat - measured at 92% of all the bus traffic this module set
        # produces. A firmware CHANGE is genuine news and still notifies.
        # Compare like with like: the field truncates at its size, so an
        # untruncated payload would never equal the stored value and the guard
        # would silently degrade back into a write on every heartbeat.
        version = str(post_data['FW'])[:self._fields['version'].size]
        if self.version != version:
            self.version = version
        # New firmware reports the controllers it currently detects on the bus in
        # the heartbeat. Pre-provision any we don't have locally yet so their
        # setup (F0) is queued proactively, before their first event, instead of
        # being onboarded lazily on that event. The queued F0 is delivered by the
        # check_for_unsent_cmd(200) below — no explicit send (see the method doc).
        self._provision_detected_controllers(post_data.get('controllers'))
        return self.check_for_unsent_cmd(200)

    def _provision_detected_controllers(self, detected_ids):
        """Onboard controllers the module reports as detected in its heartbeat
        (the ``controllers`` array) but that we do not have locally yet.

        Mirrors the manual discovery path :meth:`get_controllers` and the lazy
        event-path onboarding (``controllers/main.py`` ``_parse_event``), minus
        the inline command fire: create the ``hr.rfid.ctrl`` record and call
        :meth:`~odoo.addons.hr_rfid.models.hr_rfid_ctrl.HrRfidController.read_controller_information_cmd`
        to QUEUE the F0 (read information). We deliberately do NOT ``send_command``
        it — the ``check_for_unsent_cmd(200)`` that :meth:`parse_heartbeat` returns
        drains the queued F0 into the heartbeat response naturally.

        Add-only: a controller that drops out of the array is never removed (it
        may be temporarily offline yet still configured). No-op on old firmware
        that sends no ``controllers`` key. Works behind NAT because the heartbeat
        is module -> server (unlike :meth:`get_controllers`, which polls the
        module and cannot reach a NAT-ed webstack).

        :param detected_ids: list of RS-485 controller IDs from the heartbeat,
            or ``None``/empty on firmware that does not report them.
        """
        self.ensure_one()
        # Present only in new-firmware heartbeats; old firmware omits the key
        # entirely (post_data.get(...) -> None). Be strict about the shape so a
        # missing or malformed field can never break heartbeat command delivery.
        if not detected_ids or not isinstance(detected_ids, (list, tuple)):
            return
        if len(detected_ids) > MAX_DETECTED_CONTROLLERS:
            # A real bus never has this many — treat an oversized list as
            # malformed/hostile and skip it rather than mass-creating records.
            _logger.warning(
                "Webstack %s reported %d controllers in its heartbeat "
                "(hardware max %d); ignoring the oversized list.",
                self.name, len(detected_ids), MAX_DETECTED_CONTROLLERS)
            return
        ctrl_env = self.env['hr.rfid.ctrl'].sudo()
        known_ids = set(self.controllers.mapped('ctrl_id'))
        for ctrl_id in detected_ids:
            # Accept only a real, non-zero integer ID. 0 is the broadcast /
            # no-controller address (same guard the event path applies to
            # post_data['event']['id']); bool is an int subclass so exclude it.
            # Anything else in a stray payload is silently skipped.
            if not isinstance(ctrl_id, int) or isinstance(ctrl_id, bool) or not ctrl_id:
                continue
            if ctrl_id in known_ids:
                continue
            # Pre-provisioning is purely opportunistic: if it fails, the
            # controller is still onboarded lazily on its first event
            # (controllers/main.py::_parse_event). Keep each one strictly
            # best-effort inside a savepoint so one bad entry can never abort the
            # heartbeat's primary job — delivering queued commands via the
            # check_for_unsent_cmd(200) that parse_heartbeat returns. A savepoint
            # is required so a DB-level error does not leave the cursor aborted.
            try:
                with self.env.cr.savepoint():
                    controller = ctrl_env.create({
                        'name': 'Controller',
                        'ctrl_id': ctrl_id,
                        'webstack_id': self.id,
                    })
                    controller.read_controller_information_cmd()
            except Exception:
                _logger.warning(
                    "Webstack %s: could not pre-provision controller %s from the "
                    "heartbeat; it will be onboarded on its first event instead.",
                    self.name, ctrl_id, exc_info=True)
                continue
            known_ids.add(ctrl_id)

    def parse_response(self, post_data: dict, direct_cmd=False, command=None):
        """
        :param post_data: A dictionary containing the response data received from a request.
        :param direct_cmd: A boolean indicating whether the command was sent directly or not.
        :param command: Optional pre-matched command record (the websocket
            path correlates by command id - SPEC §5.4 ``cid``); when omitted
            the command is looked up by (controller, cmd) exactly as before.
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

        if command is None:
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
            return {'status': 200}

        # controller not response!
        if response['e'] != 0:
            if response['e'] == 20:  # controller not response!
                return self._retry_command(200, command)
            if response['e'] == 24 and command.retries < 5:
                # Device command buffer momentarily full (NO_QUADRANT - the
                # module stages at most 4 commands; INTEROP 2026-07-13):
                # transient by contract, so queue again instead of Failure.
                # The websocket chain (_ws_publish_next_command) or the
                # republish cron delivers it once a slot frees.
                command.write({
                    'status': 'Wait',
                    'retries': command.retries + 1,
                    'response': json.dumps(post_data),
                })
                return not direct_cmd and self.check_for_unsent_cmd(200)
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
            for i in range(2):
                input_masks += byte_data[i] & 0x7F << (i * 8)
            controller.process_input_masks(input_masks, output_relay_mask = byte_data[2:])
        if response['c'] == 'FC':
            apb_mode = response['d']
            for door in controller.door_ids:
                door.apb_mode = (door.number == '1' and (apb_mode & 1)) \
                                or (door.number == '2' and (apb_mode & 2))
        if response['c'] == 'FF': # Read time schedules for outputs
            byte_data = bytes.fromhex(response['d'])
            ts_for_read = set()
            for out in range(controller.outputs if controller.outputs <= 8 else 8):
                if (byte_data[out] & 0x0F) > 0:
                    ts_for_read.add(byte_data[out] & 0x0F)
                    ts_id = self.env['hr.rfid.time.schedule'].with_company(controller.webstack_id.company_id).search(
                        [('number', '=', byte_data[out] & 0x0F)]
                    )
                    if not ts_id:
                        _logger.error(f'Time schedule with number {byte_data[out] & 0x0F} not found for company {controller.company_id.name}')
                        continue
                    controller.with_context({'from_controller':True}).write({
                        'output_ts_ids': [Command.create({
                            'output_number': out + 1,
                            'time_schedule_id': ts_id.id,
                            'controller_id': controller.id,
                        })]
                    })

        if response['c'] == 'B0':
            # Read "cmd":{"id":31,"c":"B0","d":"01"}} - {"c":"B0","d":"01000000","e":0,"id":31}
            # Write "cmd":{"id":5,"c":"B0","d":"00010100"}} - {"c":"B0","d":"00","e":0,"id":5}
            if int(response['d'][0:2]) == 1: # Read
                controller.with_context(readed=True).write({
                    'alarm_lines_setup': '%02x%02x%02x' % (
                        int(response['d'][2:4], 16),
                        int(response['d'][4:6], 16),
                        int(response['d'][6:8], 16)),
                    'alarm_sensor_events': bool(1 if (int(response['d'][6:8], 16) & (1 << 4)) == 1 else 0)
                })
            else: # Write
                pass
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
            temperature = (lambda x: int(x, 10) if x.isdigit() else 0)(data[16:20])
            humidity = (lambda x: int(x, 10) if x.isdigit() else 0)(data[20:24])
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

            # The status poll runs every 5 minutes for the lifetime of the
            # installation. Its analog readings (voltages) differ on every read
            # and are declared telemetry, but the state it carries alongside -
            # inputs, outputs, alarm zones - is exactly what a monitoring
            # dispatcher watches. Write only what CHANGED, so an uneventful poll
            # carries telemetry alone and stays off the bus, while a real state
            # change still announces itself immediately.
            state = {
                'input_states': input_states,
                'output_states': output_states,
                'alarm_line_states': "{:02x}".format(Z1) + "{:02x}".format(Z2) + "{:02x}".format(Z3) + "{:02x}".format(
                    Z4),
                'hotel_readers': hotel[0],
                'hotel_readers_card_presence': hotel[1],
                'hotel_readers_buttons_pressed': hotel[2],
                'read_b3_cmd': bool(controller.read_b3_cmd or temperature != 0 or humidity != 0
                                    or controller.enabled_alarm_lines()),
            }
            telemetry = {'system_voltage': sys_voltage, 'input_voltage': input_voltage}
            changed = {name: value for name, value in state.items() if controller[name] != value}
            controller.write({**changed, **telemetry})
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

    # ================================================================
    # Demo data generation
    # ================================================================

    @api.model
    def _generate_demo_data(self):
        """Generate 60 working days of RFID events and configure time schedules.

        Called via <function> tag in demo XML during module installation.
        Follows the Odoo 19 hr_attendance._load_demo_data() pattern.
        """
        from random import randint, random as rand

        company = self.env.company

        # --- Time Schedule Setup ---
        ts_env = self.env['hr.rfid.time.schedule'].sudo()
        ts_configs = {
            1: ('Working Hours', '08001800000000000000000000000000' * 5 + '00000000000000000000000000000000' * 3),
            2: ('24/7 Access', '00002359000000000000000000000000' * 8),
            3: ('Extended Hours', '06002200000000000000000000000000' * 5 + '00000000000000000000000000000000' * 3),
            4: ('Visitor Hours', '09001700000000000000000000000000' * 5 + '00000000000000000000000000000000' * 3),
        }
        for number, (name, data) in ts_configs.items():
            ts = ts_env.search([('number', '=', number), ('company_id', '=', company.id)], limit=1)
            if ts:
                ts.write({'name': name, 'ts_data': '%02X' % number + data})

        # --- Resolve demo references ---
        def ref(xmlid):
            return self.env.ref(xmlid, raise_if_not_found=False)

        # (card_xmlid, reader_in_xmlid, reader_out_xmlid, [extra_reader_xmlids])
        card_defs = [
            ('hr_rfid.demo_card_1', 'hr_rfid.demo_ctrl_icon110_R1', 'hr_rfid.demo_ctrl_icon110_R2',
             ['hr_rfid.demo_ctrl_icon115_R1', 'hr_rfid.demo_ctrl_icon50_R1']),
            ('hr_rfid.demo_card_qdp', 'hr_rfid.demo_ctrl_icon110_R1', 'hr_rfid.demo_ctrl_icon110_R2',
             ['hr_rfid.demo_ctrl_icon115_R1', 'hr_rfid.demo_ctrl_relay_R1']),
            ('hr_rfid.demo_card_al', 'hr_rfid.demo_ctrl_icon110_R1', 'hr_rfid.demo_ctrl_icon110_R2',
             []),
            ('hr_rfid.demo_card_lur', 'hr_rfid.demo_ctrl_icon110_R1', 'hr_rfid.demo_ctrl_icon110_R2',
             ['hr_rfid.demo_ctrl_icon130_R1']),
            ('hr_rfid.demo_card_mit', 'hr_rfid.demo_ctrl_icon110_R1', 'hr_rfid.demo_ctrl_icon110_R2',
             ['hr_rfid.demo_ctrl_icon130_R2']),
        ]

        cards = []
        for card_ref, rin_ref, rout_ref, extra_refs in card_defs:
            card = ref(card_ref)
            rin = ref(rin_ref)
            rout = ref(rout_ref)
            if not (card and rin and rout):
                continue
            extras = [r for r in (ref(e) for e in extra_refs) if r]
            cards.append({
                'card_id': card.id,
                'employee_id': card.employee_id.id or False,
                'contact_id': card.contact_id.id or False,
                'reader_in': rin,
                'reader_out': rout,
                'extras': extras,
            })

        # --- Generate User Events (60 working days) ---
        now = datetime.now()
        event_vals = []

        for day_offset in range(1, 85):
            day = now - timedelta(days=day_offset)
            if day.weekday() >= 5:
                continue

            for c in cards:
                # Morning IN: base 08:00, ±10 min normal, 15% late (10-45 min)
                base_min = randint(-10, 5)
                if rand() < 0.15:
                    base_min = randint(10, 45)
                check_in = day.replace(hour=8, minute=0, second=randint(0, 59), microsecond=0) + timedelta(minutes=base_min)

                # Action: 88% granted, 4% denied, 4% TS denied, 4% APB denied
                r = rand()
                action = '1' if r >= 0.12 else ('2' if r < 0.04 else ('3' if r < 0.08 else '4'))

                rin = c['reader_in']
                event_vals.append({
                    'card_id': c['card_id'],
                    'employee_id': c['employee_id'],
                    'contact_id': c['contact_id'],
                    'reader_id': rin.id,
                    'door_id': rin.door_id.id,
                    'ctrl_addr': rin.controller_id.ctrl_id,
                    'event_action': action,
                    'event_time': check_in,
                })

                if action == '1':
                    # Evening OUT: 17:00-17:15, 10% overtime (+30-120 min)
                    overtime = randint(30, 120) if rand() < 0.10 else 0
                    check_out = day.replace(hour=17, minute=randint(0, 15), second=randint(0, 59), microsecond=0) + timedelta(minutes=overtime)
                    rout = c['reader_out']
                    event_vals.append({
                        'card_id': c['card_id'],
                        'employee_id': c['employee_id'],
                        'contact_id': c['contact_id'],
                        'reader_id': rout.id,
                        'door_id': rout.door_id.id,
                        'ctrl_addr': rout.controller_id.ctrl_id,
                        'event_action': '1',
                        'event_time': check_out,
                    })

                    # Extra events on secondary doors (40% per door)
                    for extra_r in c['extras']:
                        if rand() < 0.4:
                            extra_time = check_in + timedelta(hours=randint(1, 6), minutes=randint(0, 59))
                            event_vals.append({
                                'card_id': c['card_id'],
                                'employee_id': c['employee_id'],
                                'contact_id': c['contact_id'],
                                'reader_id': extra_r.id,
                                'door_id': extra_r.door_id.id,
                                'ctrl_addr': extra_r.controller_id.ctrl_id,
                                'event_action': '1',
                                'event_time': extra_time,
                            })

        # --- Generate System Events ---
        sys_vals = []
        ws = ref('hr_rfid.demo_module')
        sys_defs = [
            (ref('hr_rfid.demo_ctrl_icon115'), ref('hr_rfid.demo_ctrl_icon115_D1'), '25', 'Door held open > 30s'),
            (ref('hr_rfid.demo_ctrl_icon50'), ref('hr_rfid.demo_ctrl_icon50_D1'), '26', 'Door forced open'),
            (ref('hr_rfid.demo_ctrl_icon130'), None, '30', 'Controller power cycle'),
        ]
        ctrl_temp = ref('hr_rfid.demo_ctrl_temperature')

        if ws:
            for week in range(9):
                ts = now - timedelta(days=week * 7 + randint(1, 5))
                ts = ts.replace(hour=randint(8, 17), minute=randint(0, 59), second=0, microsecond=0)
                ctrl, door, act, desc = sys_defs[week % len(sys_defs)]
                if ctrl:
                    val = {
                        'event_action': act, 'webstack_id': ws.id,
                        'controller_id': ctrl.id, 'error_description': desc, 'timestamp': ts,
                    }
                    if door:
                        val['door_id'] = door.id
                    sys_vals.append(val)

            if ctrl_temp:
                for _ in range(5):
                    ts = now - timedelta(days=randint(5, 60))
                    ts = ts.replace(hour=randint(12, 17), minute=randint(0, 59), second=0, microsecond=0)
                    sys_vals.append({
                        'event_action': '51', 'webstack_id': ws.id,
                        'controller_id': ctrl_temp.id,
                        'error_description': 'Temperature exceeded threshold: %.1f C' % (26 + rand() * 8),
                        'timestamp': ts,
                    })

        # --- Bulk create ---
        if event_vals:
            self.env['hr.rfid.event.user'].sudo().with_context(demo_bulk_create=True).create(event_vals)
            _logger.info('Generated %d demo RFID user events', len(event_vals))
        if sys_vals:
            self.env['hr.rfid.event.system'].sudo().create(sys_vals)
            _logger.info('Generated %d demo RFID system events', len(sys_vals))