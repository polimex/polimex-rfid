import datetime
import json
from datetime import timedelta

from odoo.addons.hr_rfid.models.hr_rfid_door import HrRfidDoor
from odoo.addons.hr_rfid.controllers.polimex import bytes_to_num
from odoo import fields, models, api, exceptions, _, SUPERUSER_ID
from enum import Enum

import logging

_logger = logging.getLogger(__name__)
from odoo.addons.hr_rfid.controllers import polimex


class F0Parse(Enum):
    hw_ver = 0
    serial_num = 1
    sw_ver = 2
    inputs = 3
    outputs = 4
    time_schedules = 5
    io_table_lines = 6
    alarm_lines = 7
    mode = 8
    max_cards_count = 9
    max_events_count = 10


class HrRfidCommands(models.Model):
    # Commands we have queued up to send to the controllers
    _name = 'hr.rfid.command'
    _description = 'Command to controller'
    _inherit = 'balloon.mixin'
    _order = 'create_date desc, id desc'

    commands = [
        ('F0', _('Read System Information')),
        ('F1', _('Read/Search Card And Info')),
        ('F2', _('Read Group of Cards')),
        ('F3', _('Read Time Schedules')),
        ('F4', _('Read Holiday List')),
        ('F5', _('Read Controller Mode')),
        ('F6', _('Read Readers Mode')),
        ('F7', _('Read System Clock')),
        ('F8', _('Read Duress Mode')),
        ('F9', _('Read Input/Output Table')),
        ('FB', _('Read Inputs Flags')),
        ('FC', _('Read Anti-Passback Mode')),
        ('FD', _('Read Fire & Security Status')),
        ('FE', _('Read FireTime, Sound_Time')),
        ('FF', _('Read Output T/S Table')),
        ('D0', _('Write Controller ID')),
        ('D1', _('Add/Delete Card')),
        ('D2', _('Delete Card')),
        ('D3', _('Write Time Schedules')),
        ('D4', _('Write Holiday List')),
        ('D5', _('Write Controller Mode')),
        ('D6', _('Write Readers Mode')),
        ('D7', _('Write Controller System Clock')),
        ('D8', _('Write Duress Mode')),
        ('D9', _('Write Input/Output Table')),
        ('DA', _('Delete Last Event')),
        ('DB', _('Open Output')),
        ('DB2', _('Sending Balance To Vending Machine')),
        ('DC', _('System Initialization')),
        ('DD', _('Write Input Flags')),
        ('DE', _('Write Anti-Passback Mode')),
        ('DF', _('Write Outputs T/S Table')),
        ('B1', _('Read/Write temperature range')),
        ('B3', _('Read Controller Status')),
        ('B4', _('Read/Write Hotel buttons sense')),
    ]

    statuses = [
        ('Wait', _('Command Waiting for Webstack Communication')),
        ('Process', _('Command Processing')),
        ('Success', _('Command Execution Successful')),
        ('Failure', _('Command Execution Unsuccessful')),
    ]

    errors = [
        ('-1', _('Unknown Error')),
        ('0', _('No Error')),
        ('1', _('I2C Error')),
        ('2', _('I2C Error')),
        ('3', _('RS485 Error')),
        ('4', _('Wrong Value/Parameter')),
        ('5', _('CRC Error')),
        ('6', _('Memory Error')),
        ('7', _('Cards Overflow')),
        ('8', _('Not Use')),
        ('9', _('Card Not Found')),
        ('10', _('No Cards')),
        ('11', _('Not Use')),
        ('12', _('Controller Busy, Local Menu Active or Master Card Mode in Use')),
        ('13', _('1-Wire Error')),
        ('14', _('Unknown Command')),
        ('20', _('No Response from controller (WebSDK)')),
        ('21', _('Bad JSON Structure (WebSDK)')),
        ('22', _('Bad CRC from Controller (WebSDK)')),
        ('23', _('Bridge is Currently in Use (WebSDK)')),
        ('24', _('Internal Error, Try Again (WebSDK)')),
        ('30', _('No response from the Module')),
        ('31', _('Incorrect Data Response')),
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
    create_date = fields.Datetime(index=True)

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
        # size=10,
        index=True,
    )

    retries = fields.Integer(
        string='Command retries',
        help='How many times the command failed to run and has been retried',
        default=0,
    )

    pin_code = fields.Char(string='Pin Code (debug info)')
    ts_code = fields.Char(string='TS Code (debug info)', size=8)

    rights_data = fields.Char(string='Rights Data (debug info)')
    rights_mask = fields.Char(string='Rights Mask (debug info)')

    alarm_right = fields.Boolean(string='Alarm Data (debug info)', default=False)

    @api.depends('cmd')
    def _compute_cmd_name(self):
        def find_desc(cmd):
            for it in HrRfidCommands.commands:
                if it[0] == cmd:
                    return it[1]

        for record in self:
            record.name = str(record.cmd) + ' ' + find_desc(record.cmd)

    @api.autovacuum
    def _gc_clean_old_commands(self):
        res = self.env['hr.rfid.command'].search([
            ('create_date', '<', fields.Datetime.now() - timedelta(days=14))
        ], limit=1000)
        res.unlink()
        # self._cr.execute("""
        #             DELETE FROM hr_rfid_command
        #             WHERE create_date < NOW() - INTERVAL '14 days'
        #         """)
        _logger.info("GC'd %d old rfid cmd entries", self._cr.rowcount)

    def resend_action(self):
        for c in self.filtered(lambda cmd: cmd.status in ['Failure', 'Process']):
            c.write({
                'status': 'Wait',
                'retries': c.retries + 1,
                'response': None,
                'error': 0,
            })
        return self.balloon_success(
            title=_("Command resend"),
            message=_("The command is marked for execution again.")
        )

    # Command to controller
    @api.model
    def read_controller_information_cmd(self, controller):
        return self.with_user(SUPERUSER_ID).create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'F0',
        }])

    @api.model
    def read_cards_cmd(self, controller, position=0, count=0):
        if count == 0:
            return self.with_user(SUPERUSER_ID).create([{
                'webstack_id': controller.webstack_id.id,
                'controller_id': controller.id,
                'cmd': 'F2',
                'cmd_data': '0000000000',
            }])
        else:
            if (controller.cards_count > 0) and (controller.cards_count >= position):
                if controller.cardCount < (position + polimex.READ_CARDS_BLOCK_SIZE):
                    count.push(controller.card_count - position + 1)
                else:
                    count.push(polimex.READ_CARDS_BLOCK_SIZE)
                return self.with_user(SUPERUSER_ID).create([{
                    'webstack_id': controller.webstack_id.id,
                    'controller_id': controller.id,
                    'cmd': 'F2',
                    'cmd_data': ''.join(['0%s' % d for d in ('%.5d' % position)]) + '%.2d' % count,
                }])
            else:
                pass

    @api.model
    def read_readers_mode_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'F6',
        }])

    @api.model
    def read_anti_pass_back_mode_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'FC',
        }])

    @api.model
    def _system_init(self, controller, data):
        '''
        Data = 1, 2, 3, 4 ..type of system event operation
        '''
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'DC',
            'cmd_data': '%.2d%.2d' % (data, data),
        }])

    @api.model
    def delete_all_cards_cmd(self, controller):
        return self._system_init(controller, 3)

    @api.model
    def delete_all_events_cmd(self, controller):
        return self._system_init(controller, 4)

    @api.model
    def create_d1_cmd(self, ws_id, ctrl_id, card_num, pin_code, ts_code, rights_data, rights_mask, alarm_right):
        cmd_dict = {
            'webstack_id': ws_id,
            'controller_id': ctrl_id,
            'cmd': 'D1',
            'card_number': card_num,
            'pin_code': pin_code,
            'ts_code': ts_code,
            'rights_data': rights_data,
            'rights_mask': rights_mask,
            'alarm_right': alarm_right,
        }
        return self.create([cmd_dict])

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
    def add_remove_card(self, card_number, ctrl_id, pin_code, ts_code, rights_data, rights_mask, alarm_right):
        ctrl = self.env['hr.rfid.ctrl'].browse(ctrl_id)
        commands_env = self.env['hr.rfid.command'].with_user(SUPERUSER_ID)

        old_cmd = commands_env.search([
            ('cmd', '=', 'D1'),
            ('status', '=', 'Wait'),
            ('card_number', '=', card_number),
            ('controller_id', '=', ctrl.id),
            ('alarm_right', '=', alarm_right),
        ])

        if not old_cmd:
            if rights_mask != 0:
                self.create_d1_cmd(ctrl.webstack_id.id, ctrl_id, card_number,
                                   pin_code, ts_code, rights_data, rights_mask, alarm_right)
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

            new_rights_data = (rights_data | int(old_cmd.rights_data))
            new_rights_data ^= (rights_mask & int(old_cmd.rights_data))
            new_rights_data ^= (rights_data & int(old_cmd.rights_mask))
            new_rights_mask = rights_mask | int(old_cmd.rights_mask)
            new_rights_mask ^= (rights_mask & int(old_cmd.rights_data))
            new_rights_mask ^= (rights_data & int(old_cmd.rights_mask))

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
                new_rights_data = (rights_data | int(old_cmd.rights_data))
                new_rights_data ^= (rights_mask & int(old_cmd.rights_data))
                new_rights_data ^= (rights_data & int(old_cmd.rights_mask))
                new_rights_mask = rights_mask | int(old_cmd.rights_mask)
                new_rights_mask ^= (rights_mask & int(old_cmd.rights_data))
                new_rights_mask ^= (rights_data & int(old_cmd.rights_mask))

            old_cmd.write({
                'rights_mask': new_rights_mask,
                'rights_data': new_rights_data,
            })

    @api.model
    def add_card(self, door_id, ts_id, pin_code, card_id, alarm_right):
        door = door_id and isinstance(door_id, HrRfidDoor) and door_id or self.env['hr.rfid.door'].browse(door_id)
        door = self.env['hr.rfid.door'].browse(door_id)
        time_schedule = self.env['hr.rfid.time.schedule'].browse(ts_id)
        card = self.env['hr.rfid.card'].browse(card_id)
        card_number = card.internal_number

        if door.controller_id.is_relay_ctrl():
            return self._add_card_to_relay(door_id, card_id)

        for reader in door.reader_ids:
            ts_code = [0, 0, 0, 0]
            ts_code[reader.number - 1] = time_schedule.number
            ts_code = '%02X%02X%02X%02X' % (ts_code[0], ts_code[1], ts_code[2], ts_code[3])
            self.add_remove_card(
                card_number=card_number,
                ctrl_id=door.controller_id.id,
                pin_code=pin_code,
                ts_code=ts_code,
                rights_data=1 << (reader.number - 1),
                rights_mask=1 << (reader.number - 1),
                alarm_right=alarm_right
            )

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
            # TODO Why this is here?!
            # if door.reader_ids.number == 2:
            #     rdata *= 0x10000
            rmask = rdata
        elif ctrl.mode == 3:
            rdata = door.number
            rmask = -1
        else:
            raise exceptions.ValidationError(_('Controller %s has mode=%d, which is not supported!')
                                             % (ctrl.name, ctrl.mode))

        self._add_remove_card_relay(card.internal_number, ctrl.id, rdata, rmask)

    @api.model
    def remove_card(self, door_id, pin_code, card_number=None, card_id=None):
        door = self.env['hr.rfid.door'].browse(door_id)

        if card_id is not None:
            card = self.env['hr.rfid.card'].browse(card_id)
            card_number = card.internal_number

        if door.controller_id.is_relay_ctrl():
            return self._remove_card_from_relay(door_id, card_number)

        for reader in door.reader_ids:
            self.add_remove_card(
                card_number=card_number,
                ctrl_id=door.controller_id.id,
                pin_code=pin_code,
                ts_code='00000000',
                rights_data=0,
                rights_mask=1 << (reader.number - 1),
                alarm_right=True)

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
        card_door_rel_id = self.env['hr.rfid.card.door.rel'].search([
            ('card_id', '=', card.id),
            ('door_id', '=', door.id),
        ])
        self.add_remove_card(
            card_number=card.internal_number,
            ctrl_id=door.controller_id.id,
            pin_code=card.get_owner().hr_rfid_pin_code,
            ts_code='00000000',
            rights_data=rights if can_exit else 0,
            rights_mask=rights,
            alarm_right=card_door_rel_id.alarm_right
        )

    @api.model
    def _update_commands(self):
        failed_commands = self.search([
            ('status', '=', 'Process'),
            ('create_date', '<', str(fields.datetime.now() - timedelta(minutes=1)))
        ])

        for it in failed_commands:
            it.write({
                'status': 'Failure',
                'error': '30',
            })

        failed_commands = self.search([
            ('status', '=', 'Wait'),
            ('create_date', '<', str(fields.datetime.now() - timedelta(minutes=1)))
        ])

        for it in failed_commands:
            it.write({
                'status': 'Failure',
                'error': '30',
            })

    @api.model
    def _sync_clocks(self):
        ws_env = self.env['hr.rfid.webstack']

        ws_env.search([('active', '=', True)]).mapped('controllers').synchronize_clock_cmd()

    @api.model
    def _read_statuses(self):
        self.env['hr.rfid.ctrl'].search([('read_b3_cmd', '=', True)]).read_status()

    def _check_save_comms(self, vals):
        save_comms = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.save_webstack_communications') in [
            'true', 'True']
        if not save_comms:
            if 'request' in vals:
                vals.pop('request')
            if 'response' in vals:
                vals.pop('response')

    @api.model
    def find_last_wait(self, vals):
        '''
        cmd:str - command code
        command:dict - command record dict
        '''
        domain = [
            ('webstack_id', '=', vals['webstack_id']),
            ('controller_id', '=', vals['controller_id']),
            ('cmd', '=', vals['cmd']),
            ('status', '=', 'Wait'),
        ]
        if 'cmd_data' in vals.keys():
            domain.append(('cmd_data', '=', vals['cmd_data']))
        ret = self.search(domain)
        if len(ret) > 0:
            return ret[-1]
        return ret

    @api.model
    def in_command_execution(self):
        pass

    @api.model_create_multi
    def create(self, vals_list: list):
        records = self.env['hr.rfid.command']
        for vals in vals_list:
            self._check_save_comms(vals)

            cmd = vals['cmd']

            if cmd not in ['DB', 'D9', 'D5', 'DE', 'D7', 'F0', 'FC', 'D6', 'B3']:
                records += super(HrRfidCommands, self).create([vals])
                continue

            res = self.find_last_wait(vals)

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

            if records and len(records) == 1 and not records.webstack_id.is_limit_executed_cmd_reached() and records.webstack_id.active:
                records.webstack_id.direct_execute(command_id=records)

        return records

    def write(self, vals):
        self._check_save_comms(vals)

        if 'error' in vals and vals['error'] not in self.error_codes:
            vals['error'] = '-1'

        return super(HrRfidCommands, self).write(vals)

    # Command Response Parsers
    def log_cmd_error_and_return_next(self, description, error, status_code, post_data='{}'):
        self.ensure_one()
        self.write({
            'status': 'Failure',
            'error': error,
            'ex_timestamp': fields.Datetime.now(),
            'response': json.dumps(post_data),
        })
        self.controller_id.report_sys_ev(description, post_data=post_data)
        return self.controller_id.webstack_id.check_for_unsent_cmd(status_code)

    @api.model
    def _parse_f0_cmd(self, data):
        return {
            F0Parse.hw_ver: str(bytes_to_num(data, 0, 2)),
            F0Parse.serial_num: str(bytes_to_num(data, 4, 4)),
            F0Parse.sw_ver: str(bytes_to_num(data, 12, 3)),
            F0Parse.inputs: bytes_to_num(data, 18, 3),
            F0Parse.outputs: bytes_to_num(data, 24, 3),
            F0Parse.time_schedules: bytes_to_num(data, 32, 2),
            F0Parse.io_table_lines: bytes_to_num(data, 36, 2),
            F0Parse.alarm_lines: bytes_to_num(data, 40, 1),
            F0Parse.mode: int(data[42:44], 16),
            F0Parse.max_cards_count: bytes_to_num(data, 44, 5),
            F0Parse.max_events_count: bytes_to_num(data, 54, 5),
        }

    def parse_f0_response(self, post_data: dict):
        self.ensure_one()
        ctrl_env = self.env['hr.rfid.ctrl'].with_user(SUPERUSER_ID)
        response = post_data['response']
        data = response['d']
        ctrl_mode = int(data[42:44], 16)
        external_db = (ctrl_mode & 0x20) > 0
        relay_time_factor = '1' if ctrl_mode & 0x40 else '0'
        dual_person_mode = (ctrl_mode & 0x08) > 0
        ctrl_mode = ctrl_mode & 0x07

        f0_parse = self._parse_f0_cmd(data)

        hw_ver = f0_parse[F0Parse.hw_ver]

        if ctrl_mode < 1 or ctrl_mode > 4:
            return self.log_cmd_error_and_return_next('F0 command failure, controller sent '
                                                      'us a wrong mode', '31', 200, post_data=post_data)

        readers_count = int(data[30:32], 16)

        mode_reader_relation = {1: [1, 2], 2: [2, 4], 3: [4], 4: [4]}

        if hw_ver not in ['22', '30', '31', '32'] and \
                readers_count not in mode_reader_relation[ctrl_mode]:
            return self.log_cmd_error_and_return_next('F0 sent us a wrong reader-controller '
                                                      'mode combination', '31', 200, post_data=post_data)

        reader_env = self.env['hr.rfid.reader'].with_user(SUPERUSER_ID)
        door_env = self.env['hr.rfid.door'].with_user(SUPERUSER_ID)

        sw_ver = f0_parse[F0Parse.sw_ver]
        inputs = f0_parse[F0Parse.inputs]
        outputs = f0_parse[F0Parse.outputs]
        time_schedules = f0_parse[F0Parse.time_schedules]
        io_table_lines = f0_parse[F0Parse.io_table_lines]
        alarm_lines = f0_parse[F0Parse.alarm_lines]
        max_cards_count = f0_parse[F0Parse.max_cards_count]
        max_events_count = f0_parse[F0Parse.max_events_count]
        serial_num = f0_parse[F0Parse.serial_num]

        old_ctrl = ctrl_env.search([
            ('serial_number', '=', serial_num)
        ], limit=1)

        ctrl_already_existed = False
        if old_ctrl:
            if old_ctrl.webstack_id == self.controller_id.webstack_id:
                ctrl_already_existed = True
            else:
                old_ctrl.webstack_id = self.controller_id.webstack_id

        old_reader_count = len(self.controller_id.reader_ids)
        old_door_count = len(self.controller_id.door_ids)
        new_reader_count = 0
        new_door_count = 0

        def create_door(name, number):
            # If the controller is a vending controller
            nonlocal old_door_count
            nonlocal new_door_count

            door_dict = {
                'name': name,
                'number': number,
                'controller_id': self.controller_id.id,
            }

            if new_door_count < old_door_count:
                new_door_count += 1
                _door = self.controller_id.door_ids[new_door_count - 1]
                door_dict.pop('name')
                _door.write(door_dict)
                return _door

            if self.controller_id.is_vending_ctrl(hw_ver):
                return None
            return door_env.create(door_dict)

        def create_reader(name, number, reader_type, door_id=None):
            create_dict = {
                'name': '%s (%s)' % (name, (reader_type == '0') and _('In') or _('Out')),
                'number': number,
                'reader_type': reader_type,
                'controller_id': self.controller_id.id,
            }

            nonlocal old_reader_count
            nonlocal new_reader_count

            if door_id is not None:
                create_dict['door_id'] = door_id

            if new_reader_count < old_reader_count:
                new_reader_count += 1
                _reader = self.controller_id.reader_ids[new_reader_count - 1]
                create_dict.pop('name')
                _reader.write(create_dict)
                return _reader

            return reader_env.create(create_dict)

        def add_door_to_reader(_reader, _door):
            _reader.door_ids += _door

        def gen_d_name(door_num, controller_id):
            name = _('Door %d of ctrl id %d (%s)') % (door_num, controller_id.ctrl_id, controller_id.name)
            return name

        if self.controller_id.is_relay_ctrl(hw_ver):
            if ctrl_mode == 1 or ctrl_mode == 3:
                reader = create_reader('R1', 1, '0')
                for i in range(outputs):
                    door = create_door(gen_d_name(i + 1, self.controller_id), i + 1)
                    add_door_to_reader(reader, door)
                for i in range(1, readers_count):
                    create_reader('R' + str(i + 1), i + 1, '0')
            elif ctrl_mode == 2:

                if outputs > 16 and readers_count < 2:
                    return self.log_cmd_error_and_return_next('F0 sent us too many outputs and not enough readers',
                                                              '31', 200, post_data=post_data)
                io_size = 8 if outputs % 8 == 0 else 10
                io_count = outputs // io_size
                reader1 = create_reader('R1', 1, '0')
                reader2 = create_reader('R2', 2, '0')
                if io_count == 1:
                    for i in range(io_size):
                        door = create_door(gen_d_name(i + 1, self.controller_id), i + 1)
                        add_door_to_reader(reader1, door)
                elif io_count == 2:
                    for i in range(io_size):
                        door = create_door(gen_d_name(i + 1, self.controller_id), i + 1)
                        add_door_to_reader(reader1, door)
                    # for i in range(io_size, io_size*io_count):
                    #     door = create_door(gen_d_name(i + 1, self.controller_id), i + 1) # !!!!!!!!!!!!!!!!!!
                    #     add_door_to_reader(reader2, door)
                    for i in range(io_size):
                        door = create_door(gen_d_name(io_size+i + 1, self.controller_id), 16 + i + 1)
                        add_door_to_reader(reader2, door)
                elif io_count == 3:
                    for i in range(min(io_size * 2, 16)):
                        door = create_door(gen_d_name(i + 1, self.controller_id), i + 1)
                        add_door_to_reader(reader1, door)
                    for i in range(16, 16 + io_size):
                        door = create_door(gen_d_name(i + 1, self.controller_id), i + 1)
                        add_door_to_reader(reader2, door)
                elif io_count == 4:
                    for i in range(min(io_size * 2, 16)):
                        door = create_door(gen_d_name(i + 1, self.controller_id), i + 1)
                        add_door_to_reader(reader1, door)
                    for i in range(min(io_size * 2, 16), min(io_size*io_count, 32)):
                        door = create_door(gen_d_name(i + 1, self.controller_id), i + 1)
                        add_door_to_reader(reader2, door)

            else:
                raise exceptions.ValidationError(_('Got controller mode=%d for hw_ver=%s???')
                                                 % (ctrl_mode, hw_ver))
        else:
            if ctrl_mode == 1 or ctrl_mode == 3:
                last_door = create_door(gen_d_name(1, self.controller_id), 1)
                last_door = last_door.id
                create_reader('R1', 1, '0', last_door)
                if readers_count > 1:
                    create_reader('R2', 2, '1', last_door)
            elif ctrl_mode == 2 and readers_count == 4:
                last_door = create_door(gen_d_name(1, self.controller_id), 1)
                last_door = last_door.id
                create_reader('R1', 1, '0', last_door)
                create_reader('R2', 2, '1', last_door)
                last_door = create_door(gen_d_name(2, self.controller_id), 2)
                last_door = last_door.id
                create_reader('R3', 3, '0', last_door)
                create_reader('R4', 4, '1', last_door)
            else:  # (ctrl_mode == 2 and readers_count == 2) or ctrl_mode == 4
                # print('harware version', hw_ver)
                last_door = create_door(gen_d_name(1, self.controller_id), 1)
                if last_door:
                    last_door = last_door.id
                else:
                    last_door = None
                create_reader('R1', 1, '0', last_door)
                last_door = create_door(gen_d_name(2, self.controller_id), 2)
                if last_door:
                    last_door = last_door.id
                else:
                    last_door = None
                create_reader('R2', 2, '0', last_door)

            if ctrl_mode == 3:
                last_door = create_door(gen_d_name(2, self.controller_id), 2)
                last_door = last_door.id
                create_reader('R3', 3, '0', last_door)
                last_door = create_door(gen_d_name(3, self.controller_id), 3)
                last_door = last_door.id
                create_reader('R4', 4, '0', last_door)
            elif ctrl_mode == 4:
                last_door = create_door(gen_d_name(3, self.controller_id), 3)
                last_door = last_door.id
                create_reader('R3', 3, '0', last_door)
                last_door = create_door(gen_d_name(4, self.controller_id), 4)
                last_door = last_door.id
                create_reader('R4', 4, '0', last_door)

        if old_reader_count > new_reader_count:
            self.controller_id.reader_ids[new_reader_count: old_reader_count].unlink()
        if old_door_count > new_door_count:
            self.controller_id.door_ids[new_door_count: old_door_count].unlink()

        if self.controller_id.serial_number is False:
            self.controller_id.name = _('{hw_type} SN:{serial} ID:{id}').format(
                hw_type=self.controller_id.get_ctrl_model_name(hw_ver),
                serial=serial_num,
                id=self.controller_id.ctrl_id
            )

        ctrl_dict = {
            'hw_version': hw_ver,
            'serial_number': serial_num,
            'sw_version': sw_ver,
            'inputs': inputs,
            'outputs': outputs,
            'readers': readers_count,
            'time_schedules': time_schedules,
            'io_table_lines': io_table_lines,
            # 'io_table': self.controller_id.get_default_io_table(hw_ver, sw_ver, ctrl_mode),
            'alarm_lines': alarm_lines,
            'mode': ctrl_mode,
            'external_db': external_db,
            'relay_time_factor': relay_time_factor,
            'dual_person_mode': dual_person_mode,
            'max_cards_count': max_cards_count,
            'max_events_count': max_events_count,
            'last_f0_read': fields.datetime.now(),
        }
        if ctrl_mode != self.controller_id.mode and self.controller_id.mode is not None and ctrl_already_existed:
            # ctrl_dict['io_table'] = polimex.get_default_io_table(hw_ver, sw_ver, ctrl_mode)
            self.controller_id.write(ctrl_dict)
            new_io = polimex.get_default_io_table(int(hw_ver), ctrl_mode)
            if new_io:
                self.controller_id.change_io_table(new_io)
        else:
            self.controller_id.write(ctrl_dict)

        cmd_env = self.env['hr.rfid.command'].sudo()

        if not ctrl_already_existed:
            if self.controller_id.alarm_lines > 0:
                self.controller_id._setup_alarm_lines()
            self.controller_id.synchronize_clock_cmd()
            self.controller_id.delete_all_cards_cmd()
            self.controller_id.delete_all_events_cmd()
            if not self.controller_id.is_temperature_ctrl():
                self.controller_id.read_readers_mode_cmd()
            self.controller_id.read_io_table_cmd()
            self.controller_id.read_status()
            self.controller_id.read_input_masks_cmd()

        if self.controller_id.is_temperature_ctrl():
            self.controller_id.read_cards_cmd()
            self.controller_id.temp_range_cmd()
        if not self.controller_id.is_relay_ctrl() and \
                not self.controller_id.is_temperature_ctrl() and \
                ((self.controller_id.readers == 2 and ctrl_mode == 1) or (self.controller_id.readers > 2 and ctrl_mode < 4)):
            cmd_env.read_anti_pass_back_mode_cmd(self.controller_id)

    # Communication Helpers
    def send_command(self, status_code):
        if len(self) > 1:
            command = self[0]
        else:
            command = self
        command.status = 'Process'
        cmd = {
            'cmd': {
                'id': command.controller_id.ctrl_id,
                'c': command.cmd[:2],
                'd': command.cmd_data,
            }
        }
        json_cmd = {
            'status': status_code,
            'cmd': cmd['cmd']
        }
        # Commands addons
        if command.cmd == 'D1':
            if command.controller_id.is_temperature_ctrl():
                sensor_uid = ''.join(["0"+c for c in command.card_number])
                json_cmd['cmd']['d'] = sensor_uid + "%.2d" % int(command.pin_code) + "%.2d" % int(command.ts_code)
                pass
            elif command.controller_id.is_relay_ctrl():
                card_num = ''.join(list('0' + ch for ch in command.card_number))
                rights_data = '%03d%03d%03d%03d' % (
                    (int(command.rights_data) >> (3 * 8)) & 0xFF,
                    (int(command.rights_data) >> (2 * 8)) & 0xFF,
                    (int(command.rights_data) >> (1 * 8)) & 0xFF,
                    (int(command.rights_data) >> (0 * 8)) & 0xFF,
                )
                if command.controller_id.mode == 3:
                    rights_mask = '255255255255'
                else:
                    rights_mask = '%03d%03d%03d%03d' % (
                        (int(command.rights_mask) >> (3 * 8)) & 0xFF,
                        (int(command.rights_mask) >> (2 * 8)) & 0xFF,
                        (int(command.rights_mask) >> (1 * 8)) & 0xFF,
                        (int(command.rights_mask) >> (0 * 8)) & 0xFF,
                    )
                rights_data = ''.join(list('0' + ch for ch in rights_data))
                rights_mask = ''.join(list('0' + ch for ch in rights_mask))
                json_cmd['cmd']['d'] = card_num + rights_data + rights_mask
            else:
                card_num = ''.join(list('0' + ch for ch in command.card_number))
                pin_code = ''.join(list('0' + ch for ch in command.pin_code))
                ts_code = str(command.ts_code)
                rights_data = '{:02X}'.format(int(command.rights_data))
                rights_mask = '{:02X}'.format(int(command.rights_mask))
                if command.controller_id.is_alarm_ctrl():
                    json_cmd['cmd']['d'] = card_num + pin_code + ts_code + rights_data + rights_mask + (
                            command.alarm_right and rights_data or '00') + (
                                                   command.alarm_right and rights_mask or '00')
                else:
                    json_cmd['cmd']['d'] = card_num + pin_code + ts_code + rights_data + rights_mask

        if command.cmd == 'D7':
            dt = datetime.datetime.now()
            dt += command.webstack_id._get_tz_offset()

            json_cmd['cmd']['d'] = '{:02}{:02}{:02}{:02}{:02}{:02}{:02}'.format(
                dt.second, dt.minute, dt.hour, dt.weekday() + 1, dt.day, dt.month, dt.year % 100
            )
        command.request = json.dumps(json_cmd)
        return json_cmd
