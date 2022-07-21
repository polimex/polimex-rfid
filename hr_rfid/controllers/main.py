# -*- coding: utf-8 -*-
import json
import traceback
import time
import psycopg2

from ..models.hr_rfid_webstack import BadTimeException
from odoo import http, fields, exceptions, _, SUPERUSER_ID
from odoo.http import request


import logging

_logger = logging.getLogger(__name__)


class WebRfidController(http.Controller):

    def _ws_db_update_dict(self):
        return {
            'last_ip': request.httprequest.environ['REMOTE_ADDR'],
            'updated_at': fields.Datetime.now(),
        }

    def _parse_event(self, post_data: dict, webstack):
        # Helpers
        ctrl_env = request.env['hr.rfid.ctrl'].sudo()
        card_env = request.env['hr.rfid.card'].sudo()
        workcodes_env = request.env['hr.rfid.workcode'].sudo()
        ev_env = request.env['hr.rfid.event.user'].sudo()

        # Find Controller
        controller_id = ctrl_env.search([
            ('ctrl_id', '=', post_data['event']['id']),
            ('webstack_id', '=', webstack.id),
        ]).with_context(no_output=True)
        # Create new controller if needed
        if len(controller_id) == 0 and post_data['event']['id']:
            controller_id = controller_id.create({
                'name': 'Controller',
                'ctrl_id': post_data['event']['id'],
                'webstack_id': webstack.id,
            })
            command = controller_id.read_controller_information_cmd()
            # EXIT New controller and we need setup information first
            return command.send_command(400)

        # Find the Card
        card_num = post_data['event']['card']
        is_card_event = card_num != '0000000000'
        if is_card_event:
            card_id = card_env.with_context(active_test=False).search([
                ('number', '=', post_data['event']['card']),
                ('company_id', '=', webstack.company_id.id)
            ])
        else:
            card_id = None

        # Get Event ID
        event_action = post_data['event']['event_n']

        # Find Reader
        reader_num = post_data['event']['reader']
        reader_b6 = False
        if reader_num == 0:
            if int(post_data['event']['event_n']) in range(3, 18):
                reader_num = ((post_data['event']['event_n'] - 3) // 4) + 1
        else:
            reader_b6 = reader_num & 64 == 64
            reader_num = reader_num & 0x07
        reader_id = controller_id.reader_ids.filtered(lambda r: r.number == reader_num)

        if not reader_id and is_card_event:
            controller_id.report_sys_ev('Could not find a reader with that id', post_data=post_data)
            return webstack.check_for_unsent_cmd(200)

        # Find PIN code or additional data for event
        dt = post_data['event']['dt'] or None

        # Find Door ID
        door = None
        if reader_id and reader_id.door_id:  # regular door
            door = reader_id.door_id
        elif controller_id.is_relay_ctrl():  # relay door
            try:
                door_number = controller_id.decode_door_number_for_relay(dt)
                door = controller_id.door_ids.filtered(lambda d: d.number == door_number)
            except:
                door_number = None
            if not door and card_id:  # relay door
                door = reader_id.door_ids.filtered(lambda d: d.id in card_id.door_ids.mapped('id'))
                # door = set(card_id.door_ids) & set(reader_id.door_ids)
                if len(door) > 1:
                    card_door_ids = card_id and card_id.door_ids or []
                    door = set(door) & set(card_door_ids)
                    if len(door) == 1:
                        door = reader_id.door_ids and reader_id.door_ids[0] or None
                    else:
                        door = None
                    # TODO Debug and test relay controller with this event
                    # Received={"convertor": 446111, "event": {"bos": 3, "card": "0023023153", "cmd": "FA", "date": "01.08.22", "day": 6, "dt": "00000000000000000000010100000205060000000002", "err": 0, "event_n": 3, "id": 40, "reader": 0, "time": "14:59:35", "tos": 23}, "key": "44FC"}
                    if isinstance(door, set) and len(door) > 0:
                        door = door.pop()
                    else:
                        door = None
                    # -----------------MUST rework!!!!!!!!!!!!!

        # ==============EVENTS Parser======================================================
        # Durres OK, Durres Error
        if event_action in [1, 2]:
            raise Exception('Not Implemented')
        # Card Events
        elif event_action in range(3, 19):
            ue_event_action = ((event_action - 3) % 4) + 1
            # Turnstile controller. If the 7th bit is not up, then there was no actual entry
            if controller_id.is_turnstile_ctrl() and (
                    post_data['event']['reader'] & 64) == 0 and ue_event_action == '1':
                ue_event_action = '6'
            if is_card_event and card_id:  # Card event with valid card
                event_dict = {
                    'ctrl_addr': controller_id.ctrl_id,
                    'door_id': door and door.id or False,
                    'reader_id': reader_id.id,
                    'card_id': card_id and card_id.id or None,
                    'event_time': webstack.get_ws_time_str(post_data=post_data['event']),
                    'event_action': str(ue_event_action),
                    'more_json': json.dumps(post_data),
                }

                if reader_id.mode == '03' and not controller_id.is_vending_ctrl():  # Card and workcode
                    wc = workcodes_env.search([
                        ('workcode', '=', dt),
                        ('company_id', '=', webstack.company_id.id)
                    ])
                    if len(wc) == 0:
                        event_dict['workcode'] = dt
                    else:
                        event_dict['workcode_id'] = wc.id

                card_id.get_owner(event_dict)
                event = ev_env.create(event_dict)
            elif is_card_event and not card_id:  # Card event with unknown card
                sys_event_dict = {
                    'door_id': door and door.id or False,
                    'timestamp': webstack.get_ws_time_str(post_data=post_data['event']),
                    'event_action': str(event_action),
                    'card_number': card_num or None,
                    'input_js': card_num,
                }

                event = controller_id.report_sys_ev(
                    description=_('Could not find the card'),
                    post_data=post_data,
                    sys_ev_dict=sys_event_dict
                )
            else:
                _logger.error(f'IGNORING EVENT: No card number in card event. {str(post_data)}')
            return webstack.check_for_unsent_cmd(200)
        # Emergency open
        elif event_action in [19]:
            software = reader_b6
            state = reader_num > 0
            msg = _("Emergency from %s %s",
                    software and _("Software") or _("Hardware"),
                    state and _("Activated") or _("Deactivated"))

            sys_event_dict = {
                'timestamp': webstack.get_ws_time_str(post_data=post_data['event']),
                'event_action': str(event_action),
                'error_description': msg
                # 'input_js': card_num,
            }
            event = controller_id.report_sys_ev(
                description=msg,
                post_data=post_data,
                sys_ev_dict=sys_event_dict
            )
            if not software:
                controller_id._update_input_state(controller_id.inputs, int(state))
            # else:
            #     controller_id._update_input_state(14, int(state))


            if controller_id.emergency_group_id and not software:
                if state:
                    controller_id.emergency_group_id.emergency_on()
                else:
                    controller_id.emergency_group_id.emergency_off()

            return webstack.check_for_unsent_cmd(200)
        # Exit button Open Door(1234) from IN(1234
        elif event_action in [21, 22, 23, 24]:
            sys_event_dict = {
                # TODO Reader number in relay controller hold the door 1 or 2!!!!!
                'door_id': door and door.id or False,
                'timestamp': webstack.get_ws_time_str(post_data=post_data['event']),
                'event_action': '21',
                # 'input_js': card_num,
            }
            event = controller_id.report_sys_ev(
                description=_('Exit button pressed'),
                post_data=post_data,
                sys_ev_dict=sys_event_dict
            )
            return webstack.check_for_unsent_cmd(200)
        # Door N Overtime
        elif event_action in [25]:
            sys_event_dict = {
                'door_id': door and door.id or False,
                'timestamp': webstack.get_ws_time_str(post_data=post_data['event']),
                'event_action': str(event_action),
            }
            event = controller_id.report_sys_ev(
                description=_('The door is still opened'),
                post_data=post_data,
                sys_ev_dict=sys_event_dict
            )

            return controller_id.read_status().send_command(200)
        # Forced Open Door N
        elif event_action in [26]:
            sys_event_dict = {
                'door_id': door and door.id or False,
                'timestamp': webstack.get_ws_time_str(post_data=post_data['event']),
                'event_action': str(event_action),
            }
            event = controller_id.report_sys_ev(
                description=_('The door is opened by force/key'),
                post_data=post_data,
                sys_ev_dict=sys_event_dict
            )
            return webstack.check_for_unsent_cmd(200)
        # DELAY ZONE ON (if out) Z4,Z3,Z2,Z1
        elif event_action in [27]:
            raise Exception('Not Implemented (DELAY ZONE ON (if out) Z4,Z3,Z2,Z1)')
        # DELAY ZONE OFF (if out) Z4,Z3,Z2,Z1
        elif event_action in [28]:
            raise Exception('Not Implemented (DELAY ZONE OFF (if out) Z4,Z3,Z2,Z1)')
        # Reserved
        elif event_action in [29]:
            raise Exception('Not Implemented (Reserved 29)')
        # Power On controller
        elif event_action in [30]:
            controller_id.report_sys_ev('Controller restarted or Power Fail', post_data=post_data)
            return controller_id.synchronize_clock_cmd().send_command(200)
        # Open/Close Door From PC
        elif event_action in [31]:
            # iCON115 Siren Output = 4
            # iCON115 Z1 Output = 5 Arm/Disarm
            # iCON180 Siren Output = 10
            # iCON180 Z1 Out 11 ..14 Arm/Disarm
            # iCON115Relay 00 00 00  00 00 00  00 00 00  00 00 01
            sys_event_dict = {
                'door_id': door and door.id or False,
                'timestamp': webstack.get_ws_time_str(post_data=post_data['event']),
                'event_action': str(event_action),
            }
            event = controller_id.report_sys_ev(
                description=_('Output control from Software'),
                post_data=post_data,
                sys_ev_dict=sys_event_dict
            )

            return controller_id.read_status().send_command(200)
        # Reserved
        elif event_action in [32]:
            raise Exception('Not Implemented(Reserved 32)')
        # Zone Arm/Disarm Denied
        elif event_action in [33]:
            if is_card_event and card_id:
                line_id = controller_id.alarm_line_ids.filtered(lambda l: l.line_number == reader_num)
                event_dict = {
                    'ctrl_addr': controller_id.ctrl_id,
                    'door_id': door and door.id or False,
                    'reader_id': reader_id.id,
                    'alarm_line_id': line_id.id,
                    'card_id': card_id and card_id.id or None,
                    'event_time': webstack.get_ws_time_str(post_data=post_data['event']),
                    'event_action': line_id.armed == 'arm' and '15' or '5',
                    'more_json': json.dumps(post_data),
                }

                if reader_id.mode == '03' and not controller_id.is_vending_ctrl():  # Card and workcode
                    wc = workcodes_env.search([
                        ('workcode', '=', dt),
                        ('company_id', '=', webstack.company_id.id)
                    ])
                    if len(wc) == 0:
                        event_dict['workcode'] = dt
                    else:
                        event_dict['workcode_id'] = wc.id

                # card_id.get_owner(event_dict)
                event = ev_env.create(event_dict)
                return webstack.check_for_unsent_cmd(200)
            else:
                raise Exception('Wrong event. Non card event for Arm/Disarm denied!')
        # Siren On/Off, Zone Alarm, Zone Arm/Disarm
        elif event_action in [20, 34, 35]:
            # reader_num = line_number
            # PIN last 2 digits = line_statu
            line_id = controller_id.alarm_line_ids.filtered(lambda l: l.line_number == reader_num)
            line_status = dt and dt[2:] or None
            # siren = bool(event_action == 20 and line_id)
            siren = bool(event_action == 20 and reader_b6)
            # siren = bool(event_action == 20 and reader_num != 0)
            if line_id:
                new_states = []
                for i in range(4):
                    if i + 1 == line_id.line_number:
                        new_states.append(line_status)
                    else:
                        new_states.append(controller_id.alarm_line_states[i * 2:i * 2 + 2])
                controller_id.alarm_line_states = ''.join(new_states)

            event_dict = {
                'door_id': line_id and line_id.door_id and line_id.door_id.id or None,
                'alarm_line_id': line_id and line_id.id or None,
            }
            if is_card_event:  # User event only for event 35
                event_dict.update({
                    'ctrl_addr': controller_id.ctrl_id,
                    'card_id': card_id and card_id.id or None,
                    'reader_id': reader_id and reader_id.id or None,
                    'event_time': webstack.get_ws_time_str(post_data['event']),
                    'event_action': line_id.armed == 'arm' and '10' or '11'
                })
                card_id.get_owner(event_dict)
                event = ev_env.create(event_dict)
            else:  # System Event for event 20 and 34
                event_dict.update({
                    'controller_id': controller_id.id,
                    'timestamp': webstack.get_ws_time_str(post_data['event']),
                    'event_action': str(event_action),
                    'siren': siren,
                    'error_description': line_id and f"{line_id.name} - {line_id.state} / {line_id.armed}" or ''
                })
                event = controller_id.report_sys_ev(_('Hardware Event'), post_data=post_data, sys_ev_dict=event_dict)
                controller_id.siren_state = siren

            # return controller_id.read_status().send_command(200)
            return webstack.check_for_unsent_cmd(200)
        # Hotel reader events
        elif event_action in [36, 37, 38]:
            pin = post_data['event']['dt']
            event_dict = {
                'ctrl_addr': controller_id.ctrl_id,
                'door_id': reader_id.door_id.id,
                'reader_id': reader_id.id,
                'event_time': webstack.get_ws_time_str(post_data['event']),
                'event_action': str(8 - int(pin)) if event_action == 36 else '12' if event_action == 38 else '9',
            }
            if (event_dict['event_action'] in ['8', '9']) and not card_id: # Card Denied Insert or Ejected unknown card
                sys_event_dict = {
                    'door_id': door and door.id or False,
                    'timestamp': webstack.get_ws_time_str(post_data=post_data['event']),
                    'event_action': event_dict['event_action'],
                    'card_number': card_num or None,
                    'input_js': card_num,
                }

                event = controller_id.report_sys_ev(
                    description=_('Could not find the card'),
                    post_data=post_data,
                    sys_ev_dict=sys_event_dict
                )
                return webstack.check_for_unsent_cmd(200)
            if event_action in [38]:  # button
                event_dict['more_json'] = json.dumps({"state": int(pin) == 1})
            # if event_action in [37]:  # eject
            #     event_dict['more_json'] = json.dumps({"eject": reader.id})
            # if event_action in [36] and event_dict['event_action'] == 7:  # Insert
            #     event_dict['more_json'] = json.dumps({"insert": reader.id})
            card_id.get_owner(event_dict)
            event = ev_env.create(event_dict)
            door.proccess_event(event)
            return webstack.check_for_unsent_cmd(200)
        # Cloud request 64
        elif event_action in [64]:
            if not card_id:
                sys_event_dict = {
                    'door_id': door and door.id or False,
                    'timestamp': webstack.get_ws_time_str(post_data=post_data['event']),
                    'event_action': str(event_action),
                    'card_number': card_num or None,
                    # 'input_js': ,
                }

                event = controller_id.report_sys_ev(
                    description=_('Could not find the card'),
                    post_data=post_data,
                    sys_ev_dict=sys_event_dict
                )

                # controller_id.report_sys_ev(_('Could not find the card'), post_data=post_data)
                return webstack.check_for_unsent_cmd(200)
            if controller_id.is_vending_ctrl():
                return self.vending_request_for_balance()
            else:
                # External db event, controller requests for permission to open or close door
                ret = request.env['hr.rfid.access.group.door.rel'].sudo().search([
                    (
                        'access_group_id', 'in',
                        card_id.get_owner().hr_rfid_access_group_ids.mapped('access_group_id.id')),
                    ('door_id', '=', reader_id.door_id.id)
                ])
                return self._respond_to_ev_64(len(ret) > 0 and card_id.active is True,
                                              controller_id, reader_id, card_id, post_data)
                # cmd_env = request.env['hr.rfid.command'].sudo()
                # cmd = {
                #     'webstack_id': controller.webstack_id.id,
                #     'controller_id': controller.id,
                #     'cmd': 'DB',
                #     'status': 'Process',
                #     'ex_timestamp': fields.Datetime.now(),
                #     'cmd_data': '40%02X00' % (4 + 4 * (reader.number - 1)),
                # }
                # cmd = cmd_env.create(cmd)
                # cmd_js = {
                #     'status': 200,
                #     'cmd': {
                #         'id': cmd.controller_id.ctrl_id,
                #         'c': cmd.cmd[:2],
                #         'd': cmd.cmd_data,
                #     }
                # }
                # cmd.request = json.dumps(cmd_js)
                # if post_data['event']['card'] == '0000000000':
                #     controller_id._report_sys_ev('', post_data=post_data)
                # else:
                #     controller_id._report_sys_ev(_('Could not find the card'), post_data=post_data)
                # return cmd_js
        # Don't know what is this. Just report it
        else:
            controller_id.report_sys_ev(_('Unknown event. Please contact with your support!'), post_data=post_data)
            return webstack.check_for_unsent_cmd(200)

    def _respond_to_ev_64(self, open_door, controller, reader, card, post_data):
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
            cmd['cmd_data'] = '40%02X00' % (open_door + 4 * (reader.number - 1))
        else:
            data = 0
            user_doors = card.get_owner().get_doors()
            for door in reader.door_ids:
                if door in user_doors:
                    data |= 1 << (door.number - 1)
            cmd['cmd_data'] = '4000' + controller.convert_int_to_cmd_data_for_output_control(data)
        event = {
            'ctrl_addr': controller.ctrl_id,
            'door_id': reader.door_id.id,
            'reader_id': reader.id,
            'card_id': card.id,
            'event_time': controller.webstack_id.get_ws_time_str(post_data=post_data['event']),
            'event_action': '64',
        }
        card.get_owner(event)
        cmd = cmd_env.create(cmd)
        # cmd_js = {
        #     'status': 200,
        #     'cmd': {
        #         'id': cmd.controller_id.ctrl_id,
        #         'c': cmd.cmd[:2],
        #         'd': cmd.cmd_data,
        #     }
        # }
        # cmd.request = json.dumps(cmd_js)
        event['command_id'] = cmd.id
        ev_env.create(event)
        return cmd.semd_command(200)
        # return cmd_js

    @http.route(['/hr/rfid/barcode'], type='json', auth='none', methods=['POST'], cors='*', csrf=False,
                save_session=False)
    def post_barcode(self, **post):
        # request.session.should_save = False
        return
        t0 = time.time()
        _logger.info(request.jsonrequest)
        return [{
            "id": 1,
            "method": "POST",
            "body": {"cmd": {"reader": 1, "type": 0}}
        }]

    @http.route(['/hr/rfid/event'], type='json', auth='none', methods=['POST'], cors='*', csrf=False,
                save_session=False)
    def post_event(self, **post):
        """
        Process events from equipment

        """
        t0 = time.time()
        if not post:
            # Controllers with no odoo functionality use the dd/mm/yyyy format
            post_data = request.jsonrequest
        else:
            post_data = post
        _logger.info('Received=' + str(post_data))

        if 'convertor' not in post_data:
            return self._parse_raw_data(post_data)

        webstack_id = request.env['hr.rfid.webstack'].with_user(SUPERUSER_ID).search([
            '|', ('active', '=', True), ('active', '=', False),
            ('serial', '=', str(post_data['convertor']))
        ])
        try:
            if not webstack_id:
                if request.env['ir.config_parameter'].sudo().get_param('hr_rfid.save_new_webstacks') in ['true', 'True',
                                                                                                         '1']:
                    new_webstack_dict = {
                        'name': f"Module {post_data['convertor']}",
                        'serial': str(post_data['convertor']),
                        'key': post_data['key'],
                        'last_ip': request.httprequest.environ['REMOTE_ADDR'],
                        'updated_at': fields.Datetime.now(),
                        'available': 'a',
                        'company_id': request.env['res.company'].search([])[0].id,
                    }
                    webstack_id = request.env['hr.rfid.webstack'].sudo().with_context(
                        tz=request.env['res.users'].sudo().browse(2).tz).create(new_webstack_dict)
                else:
                    return {'status': 400}

            if not webstack_id.key:
                webstack_id.key = post_data['key']
                webstack_id.available = 'a'
                webstack_id.message_post(
                    body=_("The Module contacted us and activated.")
                )

            elif webstack_id.key != post_data['key']:
                webstack_id.report_sys_ev('Webstack key and key in json did not match', post_data=post_data)
                return {'status': 400}

            if not webstack_id.active:
                webstack_id.write(self._ws_db_update_dict())
                webstack_id.report_sys_ev('Webstack is not active', post_data=post_data)
                return {'status': 400}

            result = {
                'status': 400
            }

            if 'heartbeat' in post_data:
                _logger.info('Heartbeat from {}'.format(webstack_id.name))
                result = webstack_id.parse_heartbeat(post_data=post_data)
            elif 'event' in post_data:
                _logger.info('Event from {}'.format(webstack_id.name))
                result = self._parse_event(post_data=post_data, webstack=webstack_id)
            elif 'response' in post_data:
                _logger.info('Command response from {}'.format(webstack_id.name))
                result = webstack_id.parse_response(post_data=post_data)
            if not post and 'cmd' in result:
                result = {'cmd': result['cmd']}
            webstack_id.write(self._ws_db_update_dict())
            t1 = time.time()
            _logger.debug('Took %2.03f time to form response=%s' % ((t1 - t0), str(result)))
            return result
        except (KeyError, exceptions.UserError, exceptions.AccessError, exceptions.AccessDenied,
                exceptions.MissingError, exceptions.ValidationError,
                psycopg2.DataError, ValueError) as e:
            # commented DeferredException ^
            _logger.error('Caught an exception, returning status=500 and creating a system event (%s)' % str(e))
            request.env['hr.rfid.event.system'].sudo().create({
                'webstack_id': webstack_id and webstack_id.id,
                'timestamp': fields.Datetime.now(),
                'error_description': traceback.format_exc() or str(e),
                'input_js': json.dumps(post_data),
            })
            # print('Caught an exception, returning status=500 and creating a system event')
            return {'status': 500}
        except BadTimeException:
            t = post_data['event']['date'] + ' ' + post_data['event']['time']
            ev_num = str(post_data['event']['event_n'])
            controller_id = webstack_id.controllers.filtered(lambda r: r.ctrl_id == post_data['event']['id'])
            sys_ev_dict = {
                'webstack_id': webstack_id.id,
                'controller_id': controller_id.id,
                'timestamp': fields.Datetime.now(),
                'event_action': ev_num,
                'error_description': 'Controller sent us an invalid date or time: ' + t,
                'input_js': json.dumps(post_data),
            }
            request.env['hr.rfid.event.system'].sudo().create(sys_ev_dict)
            _logger.error('Caught a time error, returning status=200 and creating a system event')
            # print('Caught a time error, returning status=200 and creating a system event')
            if not post:
                #return werkzeug.exceptions.NotFound(description)
                pass
            return {'status': 200}
        except Exception as e:
            # commented DeferredException ^
            request.env['hr.rfid.event.system'].sudo().create([{
                'webstack_id': webstack_id and webstack_id.id,
                'timestamp': fields.Datetime.now(),
                'error_description': str(e),
                'input_js': json.dumps(post_data),
            }])
            _logger.error('Caught an unexpected exception, returning status=500 and creating a system event - '+str(e))
            return {'status': 500}

    def _parse_raw_data(self, post_data: dict):
        if 'serial' in post_data and 'security' in post_data and 'events' in post_data:
            return self._parse_barcode_device(post_data)

        return {'status': 200}

    def _parse_barcode_device(self, post_data: dict):
        ret = request.env['hr.rfid.raw.data'].create([{
            'do_not_save': True,
            'identification': post_data['serial'],
            'security': post_data['security'],
            'data': json.dumps(post_data),
        }])

        ret_data = ret.return_data

        if ret.do_not_save is True:
            ret.unlink()

        return json.loads(ret_data)

    def vending_request_for_balance(self):
        raise NotImplementedError('Not implemented')



