# -*- coding: utf-8 -*-
from odoo import http, fields, exceptions, _
from odoo.http import request
from enum  import Enum

import datetime
import json
import traceback
import psycopg2
import logging
import time

_logger = logging.getLogger(__name__)


class BadTimeException(Exception):
    pass


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
    max_card_count = 9
    max_events_count = 10


class WebRfidController(http.Controller):
    def __init__(self, *args, **kwargs):
        self._post = None
        self._vending_hw_version = None
        self._webstacks_env = None
        self._webstack = None
        self._ws_db_update_dict = None
        self._time_format = '%m.%d.%y %H:%M:%S'
        super(WebRfidController, self).__init__(*args, **kwargs)

    def _log_cmd_error(self, description, command, error, status_code):
        command.write({
            'status': 'Failure',
            'error': error,
            'ex_timestamp': fields.datetime.now(),
            'response': json.dumps(self._post),
        })

        self._report_sys_ev(description, command.controller_id)
        return self._check_for_unsent_cmd(status_code)

    def _check_for_unsent_cmd(self, status_code, event=None):
        commands_env = request.env['hr.rfid.command'].sudo()

        processing_comm = commands_env.search([
            ('webstack_id', '=', self._webstack.id),
            ('status', '=', 'Process'),
        ])

        if len(processing_comm) > 0:
            processing_comm = processing_comm[-1]
            self._retry_command(status_code, processing_comm, event)

        command = commands_env.search([
            ('webstack_id', '=', self._webstack.id),
            ('status', '=', 'Wait'),
        ])

        if len(command) == 0:
            return { 'status': status_code }

        command = command[-1]

        if event is not None:
            event.command_id = command
        return self._send_command(command, status_code)

    def _retry_command(self, status_code, cmd, event):
        if cmd.retries == 5:
            cmd.status = 'Failure'
            return self._check_for_unsent_cmd(status_code, event)

        cmd.retries = cmd.retries + 1

        if event is not None:
            event.command_id = cmd
        return self._send_command(cmd, status_code)

    def _parse_heartbeat(self):
        self._ws_db_update_dict['version'] = str(self._post['FW'])
        return self._check_for_unsent_cmd(200)

    def _parse_event(self):
        controller = self._webstack.controllers.filtered(lambda r: r.ctrl_id == self._post['event']['id'])

        if len(controller) == 0:
            ctrl_env = request.env['hr.rfid.ctrl'].sudo()
            cmd_env = request.env['hr.rfid.command'].sudo()

            controller = ctrl_env.create({
                'name': 'Controller',
                'ctrl_id': self._post['event']['id'],
                'webstack_id': self._webstack.id,
            })

            command = cmd_env.read_controller_information_cmd(controller)

            return self._send_command(command, 400)

        card_env = request.env['hr.rfid.card'].sudo()
        workcodes_env = request.env['hr.rfid.workcode'].sudo()
        card = card_env.search([ ('number', '=', self._post['event']['card']) ])
        reader = None
        event_action = self._post['event']['event_n']

        if event_action == 30:
            cmd_env = request.env['hr.rfid.command'].sudo()
            self._report_sys_ev('Controller restarted', controller)
            cmd_env.synchronize_clock_cmd(controller)
            return self._check_for_unsent_cmd(200)

        reader_num = self._post['event']['reader']
        if reader_num == 0:
            reader_num = ((self._post['event']['event_n'] - 3) % 4) + 1
        else:
            reader_num = reader_num & 0x07
        for it in controller.reader_ids:
            if it.number == reader_num:
                reader = it
                break

        if reader is None:
            self._report_sys_ev('Could not find a reader with that id', controller)
            return self._check_for_unsent_cmd(200)

        door = reader.door_id

        ev_env = request.env['hr.rfid.event.user'].sudo()

        if len(card) == 0:
            if event_action == 64 and controller.hw_version != self._vending_hw_version:
                cmd_env = request.env['hr.rfid.command'].sudo()
                cmd = {
                    'webstack_id': controller.webstack_id.id,
                    'controller_id': controller.id,
                    'cmd': 'DB',
                    'status': 'Process',
                    'ex_timestamp': fields.Datetime.now(),
                    'cmd_data': '40%02X00' % (4 + 4*(reader.number - 1)),
                }
                cmd = cmd_env.create(cmd)
                cmd_js = {
                    'status': 200,
                    'cmd': {
                        'id': cmd.controller_id.ctrl_id,
                        'c': cmd.cmd[:2],
                        'd': cmd.cmd_data,
                    }
                }
                cmd.request = json.dumps(cmd_js)
                self._report_sys_ev('Could not find the card', controller)
                return cmd_js
            elif event_action in [ 21, 22, 23, 24 ]:
                event_dict = {
                    'ctrl_addr': controller.ctrl_id,
                    'door_id': reader.door_id.id,
                    'reader_id': reader.id,
                    'event_time': self._get_ws_time_str(),
                    'event_action': '5',  # Exit button
                }
                event = ev_env.create(event_dict)
                return self._check_for_unsent_cmd(200, event)

            self._report_sys_ev('Could not find the card', controller)
            return self._check_for_unsent_cmd(200)

        # External db event, controller requests for permission to open or close door
        if event_action == 64 and controller.hw_version != self._vending_hw_version:
            ret = request.env['hr.rfid.access.group.door.rel'].sudo().search([
                ('access_group_id', 'in', card.get_owner().hr_rfid_access_group_ids.ids),
                ('door_id', '=', reader.door_id.id)
            ])
            return self._respond_to_ev_64(len(ret) > 0 and card.card_active is True,
                                          controller, reader, card)

        # Turnstile controller. If the 7th bit is not up, then there was no actual entry
        if controller.hw_version == '9' and (self._post['event']['reader'] & 64) == 0:
            event_action = 6
        else:
            event_action = ((event_action - 3) % 4) + 1

        # Relay controller
        if controller.is_relay_ctrl() and event_action == 1 and controller.mode == 3:
            dt = self._post['event']['dt']
            if len(dt) == 24:
                chunks = [ dt[0:6], dt[6:12], dt[12:18], dt[18:24] ]
                print('Chunks=' + str(chunks))
                door_number = 0
                for i in range(len(chunks)):
                    chunk = chunks[i]
                    n1 = int(chunk[:2])
                    n2 = int(chunk[2:4])
                    n3 = int(chunk[4:])
                    door_number |= n1*100 + n2*10 + n3
                    if i != len(chunks)-1:
                        door_number <<= 8
                for _door in reader.door_ids:
                    if _door.number == door_number:
                        door = _door
                        break

        event_dict = {
            'ctrl_addr': controller.ctrl_id,
            'door_id': door.id,
            'reader_id': reader.id,
            'card_id': card.id,
            'event_time': self._get_ws_time_str(),
            'event_action': str(event_action),
        }

        if reader.mode == '03' and controller.hw_version != self._vending_hw_version:  # Card and workcode
            wc = workcodes_env.search([
                ('workcode', '=', self._post['event']['dt'])
            ])
            if len(wc) == 0:
                event_dict['workcode'] = self._post['event']['dt']
            else:
                event_dict['workcode_id'] = wc.id

        self._get_card_owner(event_dict, card)
        event = ev_env.create(event_dict)

        return self._check_for_unsent_cmd(200, event)

    def _parse_response(self):
        command_env = request.env['hr.rfid.command'].sudo()
        response = self._post['response']
        controller = None

        for ctrl in self._webstack.controllers:
            if ctrl.ctrl_id == response['id']:
                controller = ctrl
                break

        if controller is None:
            self._report_sys_ev('Module sent us a response from a controller that does not exist')
            return self._check_for_unsent_cmd(200)

        command = command_env.search([ ('webstack_id', '=', self._webstack.id),
                                       ('controller_id', '=', controller.id),
                                       ('status', '=', 'Process'),
                                       ('cmd', '=', response['c']), ], limit=1)

        if len(command) == 0 and response['c'] == 'DB':
            command = command_env.search([ ('webstack_id', '=', self._webstack.id),
                                           ('controller_id', '=', controller.id),
                                           ('status', '=', 'Process'),
                                           ('cmd', '=', 'DB2'), ], limit=1)

        if len(command) == 0:
            self._report_sys_ev('Controller sent us a response to a command we never sent')
            return self._check_for_unsent_cmd(200)

        if response['e'] != 0:
            command.write({
                'status': 'Failure',
                'error': str(response['e']),
                'ex_timestamp': fields.datetime.now(),
                'response': json.dumps(self._post),
            })
            return self._check_for_unsent_cmd(200)

        if response['c'] == 'F0':
            self._parse_f0_response(command, controller)

        if response['c'] == 'F6':
            data = response['d']
            readers = [None, None, None, None]
            for it in controller.reader_ids:
                readers[it.number-1] = it
            for i in range(4):
                if readers[i] is not None:
                    mode = str(data[i*6:i*6+2])
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

            def bytes_to_num(start, digits):
                digits = digits-1
                res = 0
                for j in range(digits+1):
                    multiplier = 10 ** (digits-j)
                    res = res + int(data[start:start+2], 16) * multiplier
                    start = start + 2
                return res

            entrance = [ bytes_to_num(0, 1), bytes_to_num(1, 1) ]
            exit = [ bytes_to_num(2, 1), bytes_to_num(3, 1) ]
            usys = [ bytes_to_num(4, 1), bytes_to_num(5, 1) ]
            uin = [ bytes_to_num(6, 1), bytes_to_num(7, 1) ]
            temperature = bytes_to_num(8, 2)
            humidity = bytes_to_num(10, 2)
            Z1 = bytes_to_num(12, 1)
            Z2 = bytes_to_num(13, 1)
            Z3 = bytes_to_num(14, 1)
            Z4 = bytes_to_num(15, 1)

            TOS = bytes_to_num(16, 1)   * 10000 \
                  + bytes_to_num(17, 1) * 1000 \
                  + bytes_to_num(18, 1) * 100 \
                  + bytes_to_num(19, 1) * 10 \
                  + bytes_to_num(20, 1)

            DT = [ bytes_to_num(21, 1), bytes_to_num(22, 1), bytes_to_num(23, 1) ]

            if temperature >= 999:
                temperature -= 1000
                temperature *= -1
            temperature /= 10

            humidity /= 10

            sys_voltage =  ((usys[0] & 0xF0) >> 4) * 1000
            sys_voltage +=  (usys[0] & 0x0F)       * 100
            sys_voltage += ((usys[1] & 0xF0) >> 4) * 10
            sys_voltage +=  (usys[1] & 0x0F)
            sys_voltage = (sys_voltage * 8) / 5

            input_voltage =  ((uin[0] & 0xF0) >> 4) * 1000
            input_voltage +=  (uin[0] & 0x0F)       * 100
            input_voltage += ((uin[1] & 0xF0) >> 4) * 10
            input_voltage +=  (uin[1] & 0x0F)
            input_voltage = (input_voltage * 8) / 5

            controller.temperature = temperature
            controller.humidity = humidity
            controller.system_voltage = sys_voltage
            controller.input_voltage = input_voltage

        command.write({
            'status': 'Success',
            'ex_timestamp': fields.datetime.now(),
            'response': json.dumps(self._post),
        })

        return self._check_for_unsent_cmd(200)

    def _parse_f0_cmd(self, data):
        def bytes_to_num(start, digits):
            digits = digits-1
            res = 0
            for j in range(digits+1):
                multiplier = 10 ** (digits-j)
                res = res + int(data[start:start+2], 16) * multiplier
                start = start + 2
            return res

        return {
            F0Parse.hw_ver: str(bytes_to_num(0, 2)),
            F0Parse.serial_num: str(bytes_to_num(4, 4)),
            F0Parse.sw_ver: str(bytes_to_num(12, 3)),
            F0Parse.inputs: bytes_to_num(18, 3),
            F0Parse.outputs: bytes_to_num(24, 3),
            F0Parse.time_schedules: bytes_to_num(32, 2),
            F0Parse.io_table_lines: bytes_to_num(36, 2),
            F0Parse.alarm_lines: bytes_to_num(40, 1),
            F0Parse.mode: int(data[42:44], 16),
            F0Parse.max_cards_count: bytes_to_num(44, 5),
            F0Parse.max_events_count: bytes_to_num(54, 5),
        }

    def _parse_f0_response(self, command, controller):
        ctrl_env = request.env['hr.rfid.ctrl'].sudo()
        response = self._post['response']
        data = response['d']
        ctrl_mode = int(data[42:44], 16)
        external_db = (ctrl_mode & 0x20) > 0
        relay_time_factor = '1' if ctrl_mode & 0x40 else '0'
        dual_person_mode = (ctrl_mode & 0x08) > 0
        ctrl_mode = ctrl_mode & 0x07

        f0_parse = self._parse_f0_cmd(data)

        hw_ver = f0_parse[F0Parse.hw_ver]

        if (ctrl_mode < 1 or ctrl_mode > 4):
            return self._log_cmd_error('F0 command failure, controller sent '
                                       'us a wrong mode', command, '31', 200)

        readers_count = int(data[30:32], 16)

        mode_reader_relation = { 1: [2], 2: [2, 4], 3: [4], 4: [4] }

        if not ctrl_env.hw_version_is_for_relay_ctrl(hw_ver) and \
                readers_count not in mode_reader_relation[ctrl_mode]:
            return self._log_cmd_error('F0 sent us a wrong reader-controller '
                                       'mode combination', command, '31', 200)

        reader_env = request.env['hr.rfid.reader'].sudo()
        door_env = request.env['hr.rfid.door'].sudo()

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

        if len(old_ctrl) > 0:
            old_ctrl.webstack_id = controller.webstack_id

        old_reader_count = len(controller.reader_ids)
        old_door_count = len(controller.door_ids)
        new_reader_count = 0
        new_door_count = 0

        def create_door(name, number):
            # If the controller is a vending controller
            global new_door_count

            door_dict = {
                'name': name,
                'number': number,
                'controller_id': controller.id,
            }

            if new_door_count < old_door_count:
                new_door_count += 1
                _door = controller.door_ids[new_door_count-1]
                _door.write(door_dict)
                return _door

            if hw_ver == self._vending_hw_version:
                return None
            return door_env.create(door_dict)

        def create_reader(name, number, reader_type, door_id=None):
            create_dict = {
                'name': name,
                'number': number,
                'reader_type': reader_type,
                'controller_id': controller.id,
            }

            global new_reader_count

            if door_id is not None:
                create_dict['door_id'] = door_id

            if new_reader_count < old_reader_count:
                new_reader_count += 1
                _reader = controller.reader_ids[new_reader_count-1]
                _reader.write(create_dict)
                return _reader

            return reader_env.create(create_dict)

        def add_door_to_reader(_reader, _door):
            _reader.door_ids += _door

        def gen_d_name(door_num, controller_id):
            return 'Door ' + str(door_num) + ' of ctrl ' + str(controller_id)

        if controller.hw_version_is_for_relay_ctrl(hw_ver):
            if ctrl_mode == 1 or ctrl_mode == 3:
                reader = create_reader('R1', 1, '0')
                for i in range(outputs):
                    door = create_door(gen_d_name(i+1, controller.id), i+1)
                    add_door_to_reader(reader, door)
                for i in range(1, readers_count):
                    create_reader('R' + str(i+1), i+1, '0')
            elif ctrl_mode == 2:
                if outputs > 16 and readers_count < 2:
                    return self._log_cmd_error('F0 sent us too many outputs and not enough readers',
                                               command, '31', 200)
                reader = create_reader('R1', 1, '0')
                for i in range(outputs):
                    door = create_door(gen_d_name(i+1, controller.id), i+1)
                    add_door_to_reader(reader, door)
                if outputs > 16:
                    reader = create_reader('R2', 2, '0')
                    for i in range(outputs-16):
                        door = create_door(gen_d_name(i+1, controller.id), i+1)
                        add_door_to_reader(reader, door)
                    for i in range(2, readers_count):
                        create_reader('R' + str(i+1), i+1, '0')
                else:
                    for i in range(1, readers_count):
                        create_reader('R' + str(i+1), i+1, '0')
            else:
                raise exceptions.ValidationError(_('Got controller mode=%d for hw_ver=%s???')
                                                 % (ctrl_mode, hw_ver))
        else:
            if ctrl_mode == 1 or ctrl_mode == 3:
                last_door = create_door(gen_d_name(1, controller.id), 1)
                last_door = last_door.id
                create_reader('R1', 1, '0', last_door)
                create_reader('R2', 2, '1', last_door)
            elif ctrl_mode == 2 and readers_count == 4:
                last_door = create_door(gen_d_name(1, controller.id), 1)
                last_door = last_door.id
                create_reader('R1', 1, '0', last_door)
                create_reader('R2', 2, '1', last_door)
                last_door = create_door(gen_d_name(2, controller.id), 2)
                last_door = last_door.id
                create_reader('R3', 3, '0', last_door)
                create_reader('R4', 4, '1', last_door)
            else:  # (ctrl_mode == 2 and readers_count == 2) or ctrl_mode == 4
                last_door = create_door(gen_d_name(1, controller.id), 1)
                last_door = last_door.id
                create_reader('R1', 1, '0', last_door)
                last_door = create_door(gen_d_name(2, controller.id), 2)
                last_door = last_door.id
                create_reader('R2', 2, '0', last_door)

            if ctrl_mode == 3:
                last_door = create_door(gen_d_name(2, controller.id), 2)
                last_door = last_door.id
                create_reader('R3', 3, '0', last_door)
                last_door = create_door(gen_d_name(3, controller.id), 3)
                last_door = last_door.id
                create_reader('R4', 4, '0', last_door)
            elif ctrl_mode == 4:
                last_door = create_door(gen_d_name(3, controller.id), 3)
                last_door = last_door.id
                create_reader('R3', 3, '0', last_door)
                last_door = create_door(gen_d_name(4, controller.id), 4)
                last_door = last_door.id
                create_reader('R4', 4, '0', last_door)

        if old_reader_count > new_reader_count:
            controller.reader_ids[old_reader_count : new_reader_count].unlink()
        if old_door_count > new_door_count:
            controller.reader_ids[old_door_count : new_door_count].unlink()

        controller.write({
            'name': 'Controller ' + serial_num + ' ' + str(controller.ctrl_id),
            'hw_version': hw_ver,
            'serial_number': serial_num,
            'sw_version': sw_ver,
            'inputs': inputs,
            'outputs': outputs,
            'readers': readers_count,
            'time_schedules': time_schedules,
            'io_table_lines': io_table_lines,
            'alarm_lines': alarm_lines,
            'mode': ctrl_mode,
            'external_db': external_db,
            'relay_time_factor': relay_time_factor,
            'dual_person_mode': dual_person_mode,
            'max_cards_count': max_cards_count,
            'max_events_count': max_events_count,
        })

        cmd_env = request.env['hr.rfid.command'].sudo()
        cmd_env.synchronize_clock_cmd(controller)
        cmd_env.delete_all_cards_cmd(controller)
        cmd_env.delete_all_events_cmd(controller)
        cmd_env.read_readers_mode_cmd(controller)
        cmd_env.read_io_table(controller)

        if not controller.is_relay_ctrl() and (ctrl_mode == 1 or ctrl_mode == 3):
            cmd_env.read_anti_pass_back_mode_cmd(controller)

    def _report_sys_ev(self, description, controller=None):
        sys_ev_env = request.env['hr.rfid.event.system'].sudo()

        sys_ev = {
            'webstack_id': self._webstack.id,
            'error_description': description,
            'input_js': json.dumps(self._post),
        }

        if 'event' in self._post:
            sys_ev['timestamp'] = self._get_ws_time_str()
            sys_ev['event_action'] = str(self._post['event']['event_n'])
        else:
            sys_ev['timestamp'] = datetime.datetime.now()

        if controller is not None:
            sys_ev['controller_id'] = controller.id

        sys_ev_env.create(sys_ev)

    def _respond_to_ev_64(self, open_door, controller, reader, card):
        cmd_env = request.env['hr.rfid.command'].sudo()
        ev_env = request.env['hr.rfid.event.user'].sudo()
        open_door = 3 if open_door is True else 4
        cmd = {
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'DB',
            'status': 'Process',
            'ex_timestamp': fields.Datetime.now(),
        }
        if not controller.is_relay_ctrl():
            cmd['cmd_data'] = '40%02X00' % (open_door + 4*(reader.number - 1))
        else:
            data = 0
            user_doors = card.get_owner().get_doors()
            for door in reader.door_ids:
                if door in user_doors:
                    data |= 1 << (door.number - 1)
            cmd['cmd_data'] = '4000' + request.env['hr.rfid.door'].create_rights_int_to_str(data)
        event = {
            'ctrl_addr': controller.ctrl_id,
            'door_id': reader.door_id.id,
            'reader_id': reader.id,
            'card_id': card.id,
            'event_time': self._get_ws_time_str(),
            'event_action': '64',
        }
        self._get_card_owner(event, card)
        cmd = cmd_env.create(cmd)
        cmd_js = {
            'status': 200,
            'cmd': {
                'id': cmd.controller_id.ctrl_id,
                'c': cmd.cmd[:2],
                'd': cmd.cmd_data,
            }
        }
        cmd.request = json.dumps(cmd_js)
        event['command_id'] = cmd.id
        ev_env.create(event)
        return cmd_js

    def _get_ws_time_str(self):
        return self._get_ws_time().strftime('%m.%d.%y %H:%M:%S')

    def _get_ws_time(self):
        t = self._post['event']['date'] + ' ' + self._post['event']['time']
        try:
            ws_time = datetime.datetime.strptime(t, self._time_format)
            ws_time -= self._get_tz_offset(self._webstack)
        except ValueError:
            raise BadTimeException
        return ws_time

    @staticmethod
    def _get_tz_offset(webstack):
        tz_h = int(webstack.tz_offset[:3], 10)
        tz_m = int(webstack.tz_offset[3:], 10)
        return datetime.timedelta(hours=tz_h, minutes=tz_m)

    @staticmethod
    def _get_card_owner(event_dict: dict, card):
        if len(card.employee_id) == 0:
            event_dict['contact_id'] = card.contact_id.id
        else:
            event_dict['employee_id'] = card.employee_id.id

    @staticmethod
    def _send_command(command, status_code):
        command.status = 'Process'

        json_cmd = {
            'status': status_code,
            'cmd': {
                'id': command.controller_id.ctrl_id,
                'c': command.cmd[:2],
                'd': command.cmd_data,
            }
        }

        if command.cmd == 'D1':
            if not command.controller_id.is_relay_ctrl():
                card_num = ''.join(list('0' + ch for ch in command.card_number))
                pin_code = ''.join(list('0' + ch for ch in command.pin_code))
                ts_code = str(command.ts_code)
                rights_data = '{:02X}'.format(command.rights_data)
                rights_mask = '{:02X}'.format(command.rights_mask)
                json_cmd['cmd']['d'] = card_num + pin_code + ts_code + rights_data + rights_mask
            else:
                card_num = ''.join(list('0' + ch for ch in command.card_number))
                rights_data = '%03d%03d%03d%03d' % (
                    (command.rights_data >> (3*8)) & 0xFF,
                    (command.rights_data >> (2*8)) & 0xFF,
                    (command.rights_data >> (1*8)) & 0xFF,
                    (command.rights_data >> (0*8)) & 0xFF,
                )
                if command.controller_id.mode == 3:
                    rights_mask = '255255255255'
                else:
                    rights_mask = '%03d%03d%03d%03d' % (
                        (command.rights_mask >> (3*8)) & 0xFF,
                        (command.rights_mask >> (2*8)) & 0xFF,
                        (command.rights_mask >> (1*8)) & 0xFF,
                        (command.rights_mask >> (0*8)) & 0xFF,
                    )
                rights_data = ''.join(list('0' + ch for ch in rights_data))
                rights_mask = ''.join(list('0' + ch for ch in rights_mask))
                json_cmd['cmd']['d'] = card_num + rights_data + rights_mask

        if command.cmd == 'D7':
            dt = datetime.datetime.now()
            dt += WebRfidController._get_tz_offset(command.webstack_id)

            json_cmd['cmd']['d'] = '{:02}{:02}{:02}{:02}{:02}{:02}{:02}'.format(
                dt.second, dt.minute, dt.hour, dt.weekday() + 1, dt.day, dt.month, dt.year % 100
            )

        command.request = json.dumps(json_cmd)

        return json_cmd

    @http.route(['/hr/rfid/event'], type='json', auth='none', method=['POST'], csrf=False)
    def post_event(self, **post):
        print('post=' + str(post))
        t0 = time.time()
        _logger.debug('Received=' + str(post))
        if len(post) == 0:
            # Controllers with no odoo functionality use the dd/mm/yyyy format
            self._time_format = '%d.%m.%y %H:%M:%S'
            self._post = request.jsonrequest
        else:
            self._time_format = '%m.%d.%y %H:%M:%S'
            self._post = post

        if 'convertor' not in post:
            return self._parse_raw_data()

        self._vending_hw_version = '16'
        self._webstacks_env = request.env['hr.rfid.webstack'].sudo()
        self._webstack = self._webstacks_env.search([ ('serial', '=', str(post['convertor'])) ])
        self._ws_db_update_dict = {
            'last_ip': request.httprequest.environ['REMOTE_ADDR'],
            'updated_at': fields.Datetime.now(),
        }
        try:
            if len(self._webstack) == 0:
                new_webstack = {
                    'name': 'Module ' + str(post['convertor']),
                    'serial': str(post['convertor']),
                    'key': post['key'],
                    'last_ip': request.httprequest.environ['REMOTE_ADDR'],
                    'updated_at': fields.Datetime.now()
                }
                self._webstacks_env.create(new_webstack)
                return { 'status': 400 }

            if self._webstack.key != post['key']:
                self._report_sys_ev('Webstack key and key in json did not match')
                return { 'status': 400 }

            if not self._webstack.ws_active:
                self._webstack.write(self._ws_db_update_dict)
                self._report_sys_ev('Webstack is not active')
                return { 'status': 400 }

            result = {
                'status': 400
            }

            if 'heartbeat' in post:
                result = self._parse_heartbeat()
            elif 'event' in post:
                result = self._parse_event()
            elif 'response' in post:
                result = self._parse_response()

            self._webstack.write(self._ws_db_update_dict)
            t1 = time.time()
            _logger.debug('Took %2.03f time to form response=%s' % ((t1-t0), str(result)))
            print('ret=' + str(result))
            return result
        except (KeyError, exceptions.UserError, exceptions.AccessError, exceptions.AccessDenied,
                exceptions.MissingError, exceptions.ValidationError, exceptions.DeferredException,
                psycopg2.DataError, ValueError) as __:
            request.env['hr.rfid.event.system'].sudo().create([{
                'webstack_id': self._webstack.id,
                'timestamp': fields.Datetime.now(),
                'error_description': traceback.format_exc(),
                'input_js': json.dumps(self._post),
            }])
            _logger.debug('Caught an exception, returning status=500 and creating a system event')
            print('Caught an exception, returning status=500 and creating a system event')
            return { 'status': 500 }
        except BadTimeException:
            t = self._post['event']['date'] + ' ' + self._post['event']['time']
            ev_num = str(self._post['event']['event_n'])
            controller = self._webstack.controllers.filtered(lambda r: r.ctrl_id == self._post['event']['id'])
            sys_ev_dict = {
                'webstack_id': self._webstack.id,
                'controller_id': controller.id,
                'timestamp': fields.Datetime.now(),
                'event_action': ev_num,
                'error_description': 'Controller sent us an invalid date or time: ' + t,
                'input_js': json.dumps(self._post),
            }
            request.env['hr.rfid.event.system'].sudo().create(sys_ev_dict)
            _logger.debug('Caught a time error, returning status=200 and creating a system event')
            print('Caught a time error, returning status=200 and creating a system event')
            return { 'status': 200 }

    def _parse_raw_data(self):
        if 'serial' in self._post and 'security' in self._post and 'events' in self._post:
            return self._parse_barcode_device()

        return { 'status': 200 }

    def _parse_barcode_device(self):
        post = self._post
        ret = request.env['hr.rfid.raw.data'].create([{
            'do_not_save': True,
            'identification': post['serial'],
            'security': post['security'],
            'data': json.dumps(post),
        }])

        ret_data = ret.return_data

        if ret.do_not_save is True:
            ret.unlink()

        return json.loads(ret_data)
