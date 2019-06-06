# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions
from datetime import datetime, timedelta
import logging
import socket
import http.client
import json
import base64

_logger = logging.getLogger(__name__)


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

    ws_active = fields.Boolean(
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

    _sql_constraints = [ ('rfid_webstack_serial_unique', 'unique(serial)',
                          'Serial number for webstacks must be unique!') ]

    @api.one
    def action_set_active(self):
        self.ws_active = True

    @api.one
    def action_set_inactive(self):
        self.ws_active = False

    @api.one
    def action_set_webstack_settings(self):
        odoo_url = str(self.env['ir.config_parameter'].get_param('web.base.url'))
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
            conn = http.client.HTTPConnection(str(host), 80, timeout=2)
            conn.request("POST", "/protect/uart/conf", js_uart_conf, req_headers)
            response = conn.getresponse()
            conn.close()
            code = response.getcode()
            body = response.read()
            if code != 200:
                raise exceptions.ValidationError('When trying to setup /protect/uart/conf the module '
                                                 'returned code ' + str(code) + ' with body:\n' +
                                                 body.decode())

            conn = http.client.HTTPConnection(str(host), 80, timeout=2)
            conn.request("POST", "/protect/config.htm", config_params, req_headers)
            response = conn.getresponse()
            conn.close()
            code = response.getcode()
            body = response.read()
            if code != 200:
                raise exceptions.ValidationError('When trying to setup /protect/config.htm the module '
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
            conn = http.client.HTTPConnection(str(host), 80, timeout=2)
            conn.request("GET", "/config.json")
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

    @api.multi
    def _compute_http_link(self):
        for record in self:
            if record.last_ip != '' and record.last_ip is not False:
                link = 'http://' + record.last_ip + '/'
                record.http_link = link
            else:
                record.http_link = ''

    @api.model
    def _module_discovery(self):
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_sock.bind(("", 30303))

        send_msg = b'Discovery:'
        res = udp_sock.sendto(send_msg, ('<broadcast>', 30303))
        if res is False:
            udp_sock.close()
            return

        while True:
            udp_sock.settimeout(0.5)
            try:
                data, addr = udp_sock.recvfrom(1024)
                data = data.decode().split('\n')[:-1]
                data = list(map(str.strip, data))
                if len(data) == 0 or len(data) > 100:
                    continue
                if len(self.search([('serial', '=', data[4])])) > 0:
                    continue
                module = {
                    'last_ip':    addr[0],
                    'name':       data[0],
                    'version':    data[3],
                    'hw_version': data[2],
                    'serial':     data[4],
                    'available': 'u',
                }
                env = self.env['hr.rfid.webstack'].sudo()
                module = env.create(module)
                try:
                    module.action_check_if_ws_available()
                except exceptions.ValidationError as __:
                    pass
            except socket.timeout:
                break

        udp_sock.close()

    @api.model
    def _deconfirm_webstack(self, ws):
        ws.available = 'u'

    @api.model
    def _confirm_webstack(self, ws):
        ws.available = 'c'


class HrRfidController(models.Model):
    _name = 'hr.rfid.ctrl'
    _inherit = ['mail.thread']
    _description = 'Controller'

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

    max_cards_count = fields.Integer(
        string='Maximum Cards',
        help='Maximum amount of cards the controller can hold in memory',
    )

    max_events_count = fields.Integer(
        string='Maximum Events',
        help='Maximum amount of events the controller can hold in memory',
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

    reader_ids = fields.One2many(
        'hr.rfid.reader',
        'door_id',
        string='Readers',
        help='Readers that open this door',
    )

    @api.multi
    def write(self, vals):
        for door in self:
            old_card_type = None
            if 'card_type' in vals:
                old_card_type = door.card_type.id

            old_acc_gr_ids = {}
            old_ts_ids = set()
            acc_gr_door_rel_env = self.env['hr.rfid.access.group.door.rel']

            if 'door_ids' in vals:
                door_id_changes = vals['door_ids']

                for change in door_id_changes:
                    if change[0] == 1:
                        if 'access_group_id' in change[2]:
                            old_acc_gr_ids[change[1]] = change[2]['access_group_id']
                        if 'time_schedule_id' in change[2]:
                            old_ts_ids.add(change[2]['time_schedule_id'])

            super(HrRfidDoor, door).write(vals)

            if old_card_type is not None:
                commands_env = self.env['hr.rfid.command']

                for acc_gr_rel in door.access_group_ids:
                    for user in acc_gr_rel.access_group_id.employee_ids:
                        for card in user.hr_rfid_card_ids:
                            if card.card_type.id == old_card_type:
                                commands_env.remove_card(door.id, acc_gr_rel. time_schedule_id.id,
                                                         user.hr_rfid_pin_code, card_id=card.id)
                            commands_env.add_card(door.id, acc_gr_rel. time_schedule_id.id,
                                                  user.hr_rfid_pin_code, card_id=card.id)

            for rel_id, prev_acc_gr_id in old_acc_gr_ids.items():
                acc_gr_door_rel_env.access_group_changed(rel_id, prev_acc_gr_id)

            for rel_id in old_ts_ids:
                acc_gr_door_rel_env.time_schedule_changed(rel_id)

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

    door_id = fields.Many2one(
        'hr.rfid.door',
        string='Door',
        help='Door the reader opens',
        required=True,
        ondelete='cascade',
    )

    @api.multi
    def _compute_reader_name(self):
        for record in self:
            record.name = record.door_id.name + ' ' + \
                          self.reader_types[int(record.reader_type)][1] + \
                          ' Reader'


class HrRfidUserEvent(models.Model):
    _name = 'hr.rfid.event.user'
    _description = "RFID User Event"
    _order = 'event_time desc'

    name = fields.Char(
        compute='_compute_user_ev_name'
    )

    ctrl_addr = fields.Integer(
        string='Controller ID',
        required=True,
        help='ID the controller differentiates itself from the others with on the same webstack'
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='User',
        help='User affected by this event',
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
        required=True,
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
        required=True,
        ondelete='cascade',
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
        event_lifetime = self.env['ir.config_parameter'].get_param('hr_rfid.event_lifetime')
        if event_lifetime is None:
            return False

        lifetime = timedelta(days=int(event_lifetime))
        today = datetime.today()
        res = self.search([
            ('event_time', '<', today-lifetime)
        ])
        res.unlink()

        return self.env['hr.rfid.event.system'].delete_old_events()

    @api.multi
    def _compute_user_ev_name(self):
        for record in self:
            record.name = record.employee_id.name + ' - ' + \
                          self.action_selection[int(record.event_action)-1][1] +\
                          ' @ ' + record.door_id.name

    @api.multi
    def _compute_user_ev_action_str(self):
        for record in self:
            record.action_string = 'Access ' + self.action_selection[int(record.event_action)-1][1]


class HrRfidSystemEvent(models.Model):
    _name = 'hr.rfid.event.system'
    _description = 'RFID System Event'
    _order = 'timestamp desc'

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

    error_description = fields.Text(
        string='Description',
        help='Description on why the error happened',
    )

    @api.model
    def delete_old_events(self):
        event_lifetime = self.env['ir.config_parameter'].get_param('hr_rfid.event_lifetime')
        if event_lifetime is None:
            return False

        lifetime = timedelta(days=int(event_lifetime))
        today = datetime.today()
        res = self.search([
            ('timestamp', '<', today-lifetime)
        ])
        res.unlink()

        return True

    @api.multi
    def _compute_sys_ev_name(self):
        for record in self:
            record.name = str(record.webstack_id.name) + '-' + str(record.controller_id.name) +\
                          ' at ' + str(record.timestamp)


class HrRfidSystemEventWizard(models.TransientModel):
    _name = 'hr.rfid.event.sys.wiz'
    _description = 'Add card to employee/contact'

    def _default_sys_ev(self):
        return self.env['hr.rfid.event.system'].browse(self._context.get('active_ids'))

    sys_ev_id = fields.Many2one(
        'hr.rfid.event.system',
        string='System event',
        required=True,
        default=_default_sys_ev,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Card owner (employee)',
    )

    contact_id = fields.Many2one(
        'res.partner',
        stirng='Card owner (contact)',
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

    card_active = fields.Boolean(
        string='Active',
        help='Whether the card is active or not',
        track_visibility='onchange',
        default=True,
    )

    @api.multi
    def add_card(self):
        self.ensure_one()

        js = json.loads(self.sys_ev_id.error_description.split('\n')[-1])
        card_number = js['event']['card']

        if len(self.contact_id) == len(self.employee_id):
            raise exceptions.ValidationError('Card cannot have both or neither a contact owner and an employee owner.')

        card_env = self.env['hr.rfid.card']
        new_card = {
            'number': card_number,
            'card_type': self.card_type.id,
            'activate_on': self.activate_on,
            'deactivate_on': self.deactivate_on,
            'card_active': self.card_active,
        }
        if len(self.contact_id) > 0:
            new_card['contact_id'] = self.contact_id.id
        else:
            new_card['employee_id'] = self.employee_id.id
        card_env.create(new_card)


class HrRfidCommands(models.Model):
    # Commands we have queued up to send to the controllers
    _name = 'hr.rfid.command'
    _order = 'status desc, cr_timestamp asc, id'
    _description = 'Command to controller'

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

    pin_code = fields.Char()
    ts_code = fields.Integer()
    rights_data = fields.Integer()
    rights_mask = fields.Integer()

    @api.model
    def create_d1_cmd(self, ws_id, ctrl_id, card_num, pin_code, ts_code, rights_data, rights_mask):
        self.create([{
            'webstack_id': ws_id,
            'controller_id': ctrl_id,
            'cmd': 'D1',
            'cr_timestamp': fields.datetime.now(),
            'card_number': card_num,
            'pin_code': pin_code,
            'ts_code': ts_code,
            'rights_data': rights_data,
            'rights_mask': rights_mask,
        }])

    @api.model
    def add_remove_card(self, card_number, ctrl_id, pin_code, ts_code, rights_mask, rights_data):
        ctrl = self.env['hr.rfid.ctrl'].browse(ctrl_id)
        commands_env = self.env['hr.rfid.command']

        old_cmd = commands_env.search([
            ('cmd', '=', 'D1'),
            ('status', '=', 'Wait'),
            ('card_number', '=', card_number),
            ('controller_id', '=', ctrl.id),
        ])

        if len(old_cmd) == 0:
            commands_env.create_d1_cmd(ctrl.webstack_id.id, ctrl.id,
                                       card_number, pin_code, ts_code, rights_data, rights_mask)
        else:
            write_dict = {
                'pin_code': pin_code,
                'ts_code': ts_code,
            }
            new_rights_data = 0
            new_rights_mask = 0
            for i in range(8):
                bit = 1 << i
                if rights_mask & bit == 0 and old_cmd.rights_mask & bit > 0:
                    new_rights_mask |= old_cmd.rights_mask & bit
                    new_rights_data |= old_cmd.rights_data & bit
                else:
                    new_rights_mask |= rights_data & bit
                    new_rights_data |= rights_mask & bit

            write_dict['rights_mask'] = new_rights_mask
            write_dict['rights_data'] = new_rights_data

            old_cmd.write(write_dict)

    @api.model
    def add_card(self, door_id, ts_id, pin_code, card_id, ignore_active=False):
        door = self.env['hr.rfid.door'].browse(door_id)

        time_schedule = self.env['hr.rfid.time.schedule'].browse(ts_id)

        card = self.env['hr.rfid.card'].browse(card_id)
        card_number = card.number
        card_type = card.card_type

        if ignore_active is False and card.card_active is False:
            return

        if card_type != door.card_type:
            return

        for reader in door.reader_ids:
            ts_code = str(time_schedule.number << ((reader.number-1) * 8))
            self.add_remove_card(card_number, door.controller_id.id, pin_code, ts_code,
                                 1 << (reader.number-1), 1 << (reader.number-1))

    @api.model
    def remove_card(self, door_id, ts_id, pin_code, card_number=None, card_id=None, ignore_active=False):
        door = self.env['hr.rfid.door'].browse(door_id)

        time_schedule = self.env['hr.rfid.time.schedule'].browse(ts_id)

        if card_id is not None:
            card = self.env['hr.rfid.card'].browse(card_id)
            card_number = card.number
            if ignore_active is False and card.card_active is False:
                return

        for reader in door.reader_ids:
            ts_code = str(time_schedule.number << ((reader.number-1) * 8))
            self.add_remove_card(card_number, door.controller_id.id, pin_code, ts_code,
                                 1 << (reader.number-1), 0)

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
        ctrl_env = self.env['hr.rfid.ctrl']
        commands_env = self.env['hr.rfid.command']

        controllers = ctrl_env.search([('webstack_id.ws_active', '=', True)])

        for ctrl in controllers:
            commands_env.create({
                'webstack_id': ctrl.webstack_id.id,
                'controller_id': ctrl.id,
                'cmd': 'D7',
                'cr_timestamp': fields.datetime.now(),
            })




