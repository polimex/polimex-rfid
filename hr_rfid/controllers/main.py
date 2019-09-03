# -*- coding: utf-8 -*-

from odoo import http, fields, exceptions
from odoo.http import request
import datetime
import json
import traceback


class WebRfidController(http.Controller):
    @http.route(['/hr/rfid/event'], type='json', auth='none', method=['POST'], csrf=False)
    def post_event(self, **post):
        print('received=' + str(post))
        webstacks_env = request.env['hr.rfid.webstack'].sudo()
        webstack = webstacks_env.search([ ('serial', '=', str(post['convertor'])) ])
        ws_db_update_dict = {
            'last_ip': request.httprequest.environ['REMOTE_ADDR'],
            'updated_at': fields.Datetime.now(),
        }
        try:
            def log_cmd_error(description, command, error, status_code):
                command.write({
                    'status': 'Failure',
                    'error': error,
                    'ex_timestamp': fields.datetime.now(),
                    'response': json.dumps(post),
                })

                report_sys_ev(description, command.controller_id)
                return check_for_unsent_cmd(status_code)

            def check_for_unsent_cmd(status_code, event=None):
                commands_env = request.env['hr.rfid.command'].sudo()

                if 0 != len(commands_env.search([ ('webstack_id', '=', webstack.id),
                                                  ('status', '=', 'Process'), ])):
                    return { 'status': status_code }

                command = commands_env.search([
                    ('webstack_id', '=', webstack.id),
                    ('status', '=', 'Wait'),
                ], limit=1)

                if len(command) == 0:
                    return { 'status': status_code }

                if event is not None:
                    event.command_id = command
                return send_command(command, status_code)

            def send_command(command, status_code):
                command.status = 'Process'

                json_cmd = {
                    'status': status_code,
                    'cmd': {
                        'id': command.controller_id.ctrl_id,
                        'c': command.cmd,
                        'd': command.cmd_data,
                    }
                }

                if command.cmd == 'D1':
                    card_num = ''.join(list('0' + ch for ch in command.card_number))
                    pin_code = ''.join(list('0' + ch for ch in command.pin_code))
                    ts_code = str(command.ts_code)
                    rights_data = '{:02X}'.format(command.rights_data)
                    rights_mask = '{:02X}'.format(command.rights_mask)

                    json_cmd['cmd']['d'] = card_num + pin_code + ts_code + rights_data + rights_mask

                if command.cmd == 'D7':
                    dt = datetime.datetime.now()

                    json_cmd['cmd']['d'] = '{:02}{:02}{:02}{:02}{:02}{:02}{:02}'.format(
                        dt.second, dt.minute, dt.hour, dt.weekday() + 1, dt.day, dt.month, dt.year % 100
                    )

                command.request = json.dumps(json_cmd)

                return json_cmd

            def parse_heartbeat():
                ws_db_update_dict['version'] = str(post['FW'])
                return check_for_unsent_cmd(200)

            def get_card_owner(event_dict: dict, card):
                if len(card.employee_id) == 0:
                    event_dict['contact_id'] = card.contact_id.id
                else:
                    event_dict['employee_id'] = card.employee_id.id

            def parse_event():
                controller = webstack.controllers.filtered(lambda r: r.ctrl_id == post['event']['id'])

                if len(controller) == 0:
                    ctrl_env = request.env['hr.rfid.ctrl'].sudo()

                    cmd_env = request.env['hr.rfid.command'].sudo()
                    controller = ctrl_env.create({
                        'name': 'Controller',
                        'ctrl_id': post['event']['id'],
                        'webstack_id': webstack.id,
                    })

                    command = cmd_env.create({
                        'webstack_id': webstack.id,
                        'controller_id': controller.id,
                        'cmd': 'F0',
                        'cr_timestamp': fields.datetime.now(),
                    })

                    return send_command(command, 400)

                card_env = request.env['hr.rfid.card'].sudo()
                workcodes_env = request.env['hr.rfid.workcode'].sudo()
                card = card_env.search([ ('number', '=', post['event']['card']) ])
                reader = None

                reader_num = post['event']['reader']
                if reader_num == 0:
                    reader_num = ((post['event']['event_n'] - 3) % 4) + 1
                for it in controller.reader_ids:
                    if it.number == reader_num:
                        reader = it
                        break

                if reader is None:
                    report_sys_ev('Could not find a reader with that id', controller)
                    return check_for_unsent_cmd(200)

                ev_env = request.env['hr.rfid.event.user'].sudo()

                event_action = post['event']['event_n']

                if len(card) == 0:
                    if event_action == 64:
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
                                        'c': cmd.cmd,
                                        'd': cmd.cmd_data,
                                           }
                        }
                        cmd.request = json.dumps(cmd_js)
                        report_sys_ev('Could not find a card with that number.', controller)
                        return cmd_js

                    report_sys_ev('Could not find a card with that number.', controller)
                    return check_for_unsent_cmd(200)

                # External db event, controller requests for permission to open or close door
                if event_action == 64:
                    ret = request.env['hr.rfid.access.group.door.rel'].sudo().search([
                        ('access_group_id', '=', card.get_owner().hr_rfid_access_group_id.id),
                        ('door_id', '=', reader.door_id.id)
                    ])
                    # if len(ret) > 0: open door, else close
                    return respond_to_ev_64(len(ret) > 0 and card.card_active is True, controller, reader, card)

                event_action = ((event_action - 3) % 4) + 1
                event_dict = {
                    'ctrl_addr': controller.ctrl_id,
                    'door_id': reader.door_id.id,
                    'reader_id': reader.id,
                    'card_id': card.id,
                    'event_time': post['event']['date'] + ' ' + post['event']['time'],
                    'event_action': str(event_action),
                }

                if reader.mode == '03':  # Card and workcode
                    wc = workcodes_env.search([
                        ('workcode', '=', post['event']['dt'])
                    ])
                    if len(wc) == 0:
                        event_dict['workcode'] = post['event']['dt']
                    else:
                        event_dict['workcode_id'] = wc.id

                get_card_owner(event_dict, card)
                event = ev_env.create(event_dict)

                return check_for_unsent_cmd(200, event)

            def parse_response():
                command_env = request.env['hr.rfid.command'].sudo()
                response = post['response']
                controller = None

                for ctrl in webstack.controllers:
                    if ctrl.ctrl_id == response['id']:
                        controller = ctrl
                        break

                if controller is None:
                    report_sys_ev('Module sent us a response from a controller that does not exist')
                    return check_for_unsent_cmd(200)

                command = command_env.search([ ('webstack_id', '=', webstack.id),
                                               ('controller_id', '=', controller.id),
                                               ('status', '=', 'Process'),
                                               ('cmd', '=', response['c']), ], limit=1)

                if len(command) == 0:
                    report_sys_ev('Controller sent us a response to a command we never sent')
                    return check_for_unsent_cmd(200)

                if response['e'] != 0:
                    command.write({
                        'status': 'Failure',
                        'error': str(response['e']),
                        'ex_timestamp': fields.datetime.now(),
                        'response': json.dumps(post),
                    })
                    return check_for_unsent_cmd(200)

                if response['c'] == 'F0':
                    data = response['d']
                    ctrl_mode = int(data[42:44], 16)
                    external_db = ctrl_mode & 0x20 > 0
                    ctrl_mode = ctrl_mode & 0x0F

                    if ctrl_mode < 1 or ctrl_mode > 4:
                        return log_cmd_error('F0 command failure, controller sent '
                                             'us a wrong mode', command, '31', 200)

                    readers_count = int(data[30:32], 16)

                    mode_reader_relation = { 1: [2], 2: [2, 4], 3: [4], 4: [4] }

                    if readers_count not in mode_reader_relation[ctrl_mode]:
                        return log_cmd_error('F0 sent us a wrong reader-controller '
                                             'mode combination', command, '31', 200)

                    reader_env = request.env['hr.rfid.reader'].sudo()
                    door_env = request.env['hr.rfid.door'].sudo()
                    ctrl_env = request.env['hr.rfid.ctrl'].sudo()

                    def bytes_to_num(start, digits):
                        digits = digits-1
                        res = 0
                        for j in range(digits+1):
                            multiplier = 10 ** (digits-j)
                            res = res + int(data[start:start+2], 16) * multiplier
                            start = start + 2
                        return res

                    serial_num = str(bytes_to_num(4, 4))

                    old_ctrl = ctrl_env.search([
                        ('serial_number', '=', serial_num)
                    ], limit=1)

                    if len(old_ctrl) > 0:
                        old_ctrl.webstack_id = controller.webstack_id
                        controller.unlick()

                    if len(controller.reader_ids):
                        controller.reader_ids.unlink()

                    if len(controller.door_ids):
                        controller.door_ids.unlink()

                    last_door = None

                    def create_door(name, number, ctrl_id):
                        return door_env.create({
                            'name': name,
                            'number': number,
                            'controller_id': ctrl_id,
                        })

                    def create_reader(name, number, reader_type, ctrl_id):
                        reader_env.create({
                            'name': name,
                            'number': number,
                            'reader_type': reader_type,
                            'controller_id': ctrl_id,
                            'door_id': last_door.id,
                        })

                    def gen_d_name(door_num, controller_id):
                        return 'Door ' + str(door_num) + ' of ctrl ' + str(controller_id)

                    if ctrl_mode == 1 or ctrl_mode == 3:
                        last_door = create_door(gen_d_name(1, controller.id), 1, controller.id)
                        create_reader('R1', 1, '0', controller.id)
                        create_reader('R2', 2, '1', controller.id)
                    elif ctrl_mode == 2 and readers_count == 4:
                        last_door = create_door(gen_d_name(1, controller.id), 1, controller.id)
                        create_reader('R1', 1, '0', controller.id)
                        create_reader('R2', 2, '1', controller.id)
                        last_door = create_door(gen_d_name(2, controller.id), 2, controller.id)
                        create_reader('R3', 3, '0', controller.id)
                        create_reader('R4', 4, '1', controller.id)
                    else:  # (ctrl_mode == 2 and readers_count == 2) or ctrl_mode == 4
                        last_door = create_door(gen_d_name(1, controller.id), 1, controller.id)
                        create_reader('R1', 1, '0', controller.id)
                        last_door = create_door(gen_d_name(2, controller.id), 2, controller.id)
                        create_reader('R2', 2, '0', controller.id)

                    if ctrl_mode == 3:
                        last_door = create_door(gen_d_name(2, controller.id), 2, controller.id)
                        create_reader('R3', 3, '0', controller.id)
                        last_door = create_door(gen_d_name(3, controller.id), 3, controller.id)
                        create_reader('R4', 4, '0', controller.id)
                    elif ctrl_mode == 4:
                        last_door = create_door(gen_d_name(3, controller.id), 3, controller.id)
                        create_reader('R3', 3, '0', controller.id)
                        last_door = create_door(gen_d_name(4, controller.id), 4, controller.id)
                        create_reader('R4', 4, '0', controller.id)

                    hw_ver = str(bytes_to_num(0, 2))
                    sw_ver = str(bytes_to_num(12, 3))
                    inputs = bytes_to_num(18, 3)
                    outputs = bytes_to_num(24, 3)
                    time_schedules = bytes_to_num(32, 2)
                    io_table_lines = bytes_to_num(36, 2)
                    alarm_lines = bytes_to_num(40, 1)
                    max_cards_count = bytes_to_num(44, 5)
                    max_events_count = bytes_to_num(54, 5)

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
                        'max_cards_count': max_cards_count,
                        'max_events_count': max_events_count,
                    })

                    cmd_env = request.env['hr.rfid.command'].sudo()
                    cmd_env.create({
                        'webstack_id': webstack.id,
                        'controller_id': controller.id,
                        'cmd': 'D7',
                        'cr_timestamp': fields.datetime.now(),
                    })

                    cmd_env.create({
                        'webstack_id': webstack.id,
                        'controller_id': controller.id,
                        'cmd': 'DC',
                        'cmd_data': '0303',
                        'cr_timestamp': fields.datetime.now(),
                    })

                    cmd_env.create({
                        'webstack_id': webstack.id,
                        'controller_id': controller.id,
                        'cmd': 'DC',
                        'cmd_data': '0404',
                    })

                    cmd_env.create({
                        'webstack_id': webstack.id,
                        'controller_id': controller.id,
                        'cmd': 'F6',
                    })

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

                command.write({
                    'status': 'Success',
                    'ex_timestamp': fields.datetime.now(),
                    'response': json.dumps(post),
                })

                return check_for_unsent_cmd(200)

            def report_sys_ev(description, controller=None):
                sys_ev_env = request.env['hr.rfid.event.system'].sudo()

                sys_ev = {
                    'webstack_id': webstack.id,
                    'error_description': description + '\n' + json.dumps(post),
                    'timestamp': fields.datetime.now(),
                }
                if controller is not None:
                    sys_ev['controller_id'] = controller.id

                sys_ev_env.create(sys_ev)

            def respond_to_ev_64(open_door, controller, reader, card):
                cmd_env = request.env['hr.rfid.command'].sudo()
                ev_env = request.env['hr.rfid.event.user'].sudo()
                open_door = 3 if open_door is True else 4
                cmd = {
                    'webstack_id': controller.webstack_id.id,
                    'controller_id': controller.id,
                    'cmd': 'DB',
                    'status': 'Process',
                    'ex_timestamp': fields.Datetime.now(),
                    'cmd_data': '40%02X00' % (open_door + 4*(reader.number - 1)),
                }
                event = {
                    'ctrl_addr': controller.ctrl_id,
                    'door_id': reader.door_id.id,
                    'reader_id': reader.id,
                    'card_id': card.id,
                    'event_time': post['event']['date'] + ' ' + post['event']['time'],
                    'event_action': '64',
                }
                get_card_owner(event, card)
                cmd = cmd_env.create(cmd)
                cmd_js = {
                    'status': 200,
                    'cmd': {
                        'id': cmd.controller_id.ctrl_id,
                        'c': cmd.cmd,
                        'd': cmd.cmd_data,
                    }
                }
                cmd.request = json.dumps(cmd_js)
                event['command_id'] = cmd.id
                ev_env.create(event)
                return cmd_js

            if len(webstack) == 0:
                new_webstack = {
                    'name': 'Module ' + str(post['convertor']),
                    'serial': str(post['convertor']),
                    'key': post['key'],
                    'last_ip': request.httprequest.environ['REMOTE_ADDR'],
                    'updated_at': fields.Datetime.now()
                }
                webstacks_env.create(new_webstack)
                return { 'status': 400 }

            if webstack.key != post['key']:
                report_sys_ev('Webstack key and key in json did not match')
                return { 'status': 400 }

            if not webstack.ws_active:
                webstack.write(ws_db_update_dict)
                report_sys_ev('Webstack is not active')
                return { 'status': 400 }

            result = {
                'status': 400
            }

            if 'heartbeat' in post:
                result = parse_heartbeat()
            elif 'event' in post:
                result = parse_event()
            elif 'response' in post:
                result = parse_response()

            webstack.write(ws_db_update_dict)
            return result
        except (KeyError, exceptions.UserError, exceptions.AccessError, exceptions.AccessDenied,
                exceptions.MissingError, exceptions.ValidationError, exceptions.DeferredException) as __:
            request.env['hr.rfid.event.system'].sudo().create({
                'webstack_id': webstack.id,
                'timestamp': fields.Datetime.now(),
                'error_description': traceback.format_exc(),
            })

