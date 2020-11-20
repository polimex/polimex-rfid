from odoo import fields, models, api, exceptions, _
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


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
            ('event_time', '<', today - lifetime)
        ])
        res.unlink()

        return self.env['hr.rfid.event.system'].delete_old_events()

    @api.multi
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
                name += self.action_selection[int(record.event_action) - 1][1]
            else:
                name += 'Request Instructions'
            if record.door_id:
                name += ' @ ' + record.door_id.name
            record.name = name

    @api.multi
    def _compute_user_ev_action_str(self):
        for record in self:
            record.action_string = 'Access ' + self.action_selection[int(record.event_action) - 1][1]

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
                        ('event_time', '>=', datetime.now() - timedelta(hours=12)),
                        ('employee_id', '=', rec.employee_id.id),
                        ('id', '!=', rec.id),
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
            ('timestamp', '<', today - lifetime)
        ])
        res.unlink()

        return True

    @api.multi
    def _compute_sys_ev_name(self):
        for record in self:
            record.name = str(record.webstack_id.name) + '-' + str(record.controller_id.name) + \
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

    @api.multi
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
        default=_default_card_number,
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

    @api.multi
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

    @api.multi
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
            ts_code[reader.number - 1] = time_schedule.number
            ts_code = '%02X%02X%02X%02X' % (ts_code[0], ts_code[1], ts_code[2], ts_code[3])
            self.add_remove_card(card_number, door.controller_id.id, pin_code, ts_code,
                                 1 << (reader.number - 1), 1 << (reader.number - 1))

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
                                 0, 1 << (reader.number - 1))

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

        controllers = ws_env.search([]).mapped('controllers')

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

            if cmd not in ['DB', 'D9', 'D5', 'DE', 'D7', 'F0', 'FC', 'D6', 'B3']:
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
            elif cmd in ['D9', 'D5', 'DE', 'D6']:
                res.cmd_data = cmd_data
                continue
            elif cmd in ['D7', 'F0', 'FC', 'B3']:
                continue

            records += super(HrRfidCommands, self).create([vals])

        return records

    @api.multi
    def write(self, vals):
        self._check_save_comms(vals)

        if 'error' in vals and vals['error'] not in self.error_codes:
            vals['error'] = '-1'

        return super(HrRfidCommands, self).write(vals)