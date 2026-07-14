# -*- coding: utf-8 -*-
"""Hardware event-parsing core of ``hr.rfid.webstack``.

Moved (behaviour-preserving) out of ``controllers/main.py`` so that BOTH
ingress paths share ONE implementation:

- the HTTP route ``/hr/rfid/event`` (``WebRfidController`` stays a thin
  decode/auth/encode wrapper and delegates here), and
- the websocket layer (``ir.websocket`` device messages - see
  ``docs/odoo-bus/ODOO_BUS_ODOO_PLAN.md`` in the esp32 repo, package A).

The method bodies are a mechanical transplant of the controller code:
``request.env`` -> ``self.env``, the ``webstack`` argument -> ``self``.
No semantic change is intended; the full hr_rfid test suite is the
regression gate.
"""
import json
import logging

from odoo import models, fields, _, SUPERUSER_ID
from odoo.addons.hr_rfid.controllers import polimex

_logger = logging.getLogger(__name__)


class HrRfidWebstackHwEvents(models.Model):
    _inherit = 'hr.rfid.webstack'

    def _hw_vending_request_for_balance(self):
        """Hook for the vending ev64 balance flow.

        Mirrors the controller-level ``vending_request_for_balance`` stub:
        the base module has no vending logic; ``hr_rfid_vending`` handles
        vending controllers in its own route override before this core is
        ever reached, so this stays a guard for misconfigured setups.
        """
        raise NotImplementedError('Not implemented')

    def _hw_parse_event(self, post_data: dict):
        self.ensure_one()
        # Helpers
        ctrl_env = self.env['hr.rfid.ctrl'].sudo().with_user(SUPERUSER_ID)
        card_env = self.env['hr.rfid.card'].sudo().with_user(SUPERUSER_ID)
        workcodes_env = self.env['hr.rfid.workcode'].sudo().with_user(SUPERUSER_ID)
        ev_env = self.env['hr.rfid.event.user'].sudo().with_user(SUPERUSER_ID)

        # Find Controller — (ctrl_id, webstack_id) is logically unique,
        # so limit=1 lets PostgreSQL stop after the first match.
        controller_id = ctrl_env.search([
            ('ctrl_id', '=', post_data['event']['id']),
            ('webstack_id', '=', self.id),
        ], limit=1).with_context(no_output=True)
        # Create new controller if needed
        if len(controller_id) == 0 and post_data['event']['id']:
            controller_id = controller_id.create({
                'name': 'Controller',
                'ctrl_id': post_data['event']['id'],
                'webstack_id': self.id,
            })
            command = controller_id.read_controller_information_cmd()
            # EXIT New controller and we need setup information first
            return command.send_command(400)

        # Find the Card
        card_num = post_data['event']['card']
        is_card_event = card_num != '0000000000'
        if is_card_event:
            card_id = card_env.with_context(active_test=False).search([
                ('internal_number', '=', post_data['event']['card']),
                ('company_id', '=', self.company_id.id)
            ])
            if len(card_id) > 1:
                _logger.error(f'More than one card with the same number {card_num}')
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
            return self.check_for_unsent_cmd(200)

        # Find PIN code or additional data for event
        dt = post_data['event']['dt'] or None
        temp_data = None
        if controller_id.is_temperature_ctrl:
            temp_data = polimex.get_temperature(
                int(post_data['event']['dt'][0:2]),
                int(post_data['event']['dt'][2:4])
            )

        # Find Door ID
        door = None
        if reader_id and reader_id.door_id:  # regular door
            door = reader_id.door_id
        elif controller_id.is_relay_ctrl():  # relay door
            door_number = None
            door = None
            if controller_id.mode == 3:
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
            sys_event_dict = {
                'door_id': door and door.id or False,
                'timestamp': self.get_ws_time_str(post_data=post_data['event']),
                'event_action': str(event_action),
                'input_js': card_num,
            }

            event = controller_id.report_sys_ev(
                description=_('Duress mode'),
                post_data=post_data,
                sys_ev_dict=sys_event_dict
            )
            # _logger.error('Not Implemented event 1 or 2 (Duress mode)')
            return self.check_for_unsent_cmd(200)
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
                    'event_time': self.get_ws_time_str(post_data=post_data['event']),
                    'event_action': str(ue_event_action),
                    'more_json': json.dumps(post_data),
                }

                if reader_id.mode == '03' and not controller_id.is_vending_ctrl():  # Card and workcode
                    wc = workcodes_env.search([
                        ('workcode', '=', dt),
                        ('company_id', '=', self.company_id.id)
                    ])
                    if len(wc) == 0:
                        event_dict['workcode'] = dt
                    else:
                        event_dict['workcode_id'] = wc.id

                card_id.get_owner(event_dict)
                event = ev_env.create(event_dict)
                if event.event_action == '1' and event.contact_id:
                    ag_rel = event.contact_id.hr_rfid_access_group_ids.filter_by_door(event.door_id, True)
                    # lambda agr: event.door_id in agr.access_group_id.door_ids.mapped('door_id') and state)
                    # if ag_rel and ag_rel.visits_counting:
                    if ag_rel and reader_id and reader_id.reader_type == '0':
                        # Handle multiple access group relations for the same door
                        if len(ag_rel) > 1:
                            _logger.warning('Multiple active access group relations (%s) found for contact %s and door %s. Incrementing visits for all relations.',
                                          ag_rel.ids, event.contact_id.name, event.door_id.name)
                        for rel in ag_rel:
                            rel.visits_counter += 1
            elif is_card_event and not card_id:  # Card event with unknown card
                sys_event_dict = {
                    'door_id': door and door.id or False,
                    'timestamp': self.get_ws_time_str(post_data=post_data['event']),
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
                sys_event_dict = {
                    'door_id': door and door.id or False,
                    'timestamp': self.get_ws_time_str(post_data=post_data['event']),
                    'event_action': str(event_action),
                    'card_number': card_num or None,
                    'input_js': card_num,
                }

                event = controller_id.report_sys_ev(
                    description=_('Card event without card number'),
                    post_data=post_data,
                    sys_ev_dict=sys_event_dict
                )
            return self.check_for_unsent_cmd(200)
        # Emergency open
        elif event_action in [19]:
            software = reader_b6
            state = reader_num > 0
            msg = _("Emergency from %s %s",
                    software and _("Software") or _("Hardware"),
                    state and _("Activated") or _("Deactivated"))

            sys_event_dict = {
                'timestamp': self.get_ws_time_str(post_data=post_data['event']),
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

            return self.check_for_unsent_cmd(200)
        # Exit button Open Door(1234) from IN(1234
        elif event_action in [21, 22, 23, 24]:
            sys_event_dict = {
                # TODO Reader number in relay controller hold the door 1 or 2!!!!!
                'door_id': door and door.id or False,
                'timestamp': self.get_ws_time_str(post_data=post_data['event']),
                'event_action': '21',
            }
            event = controller_id.report_sys_ev(
                description=_('Exit button %d pressed ', event_action-20),
                post_data=post_data,
                sys_ev_dict=sys_event_dict
            )
            return self.check_for_unsent_cmd(200)
        # Door N Overtime
        elif event_action in [25]:
            sys_event_dict = {
                'door_id': door and door.id or False,
                'timestamp': self.get_ws_time_str(post_data=post_data['event']),
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
                'timestamp': self.get_ws_time_str(post_data=post_data['event']),
                'event_action': str(event_action),
            }
            event = controller_id.report_sys_ev(
                description=_('The door is opened by force/key'),
                post_data=post_data,
                sys_ev_dict=sys_event_dict
            )
            return self.check_for_unsent_cmd(200)
        # DELAY ZONE ON (if out) Z4,Z3,Z2,Z1
        elif event_action in [27]:
            raise Exception('Not Implemented (DELAY ZONE ON (if out) Z4,Z3,Z2,Z1)')
        # DELAY ZONE OFF (if out) Z4,Z3,Z2,Z1
        elif event_action in [28]:
            raise Exception('Not Implemented (DELAY ZONE OFF (if out) Z4,Z3,Z2,Z1)')
        # External control
        elif event_action in [29]:
            controller_id.report_sys_ev('External control', post_data=post_data)
            return self.check_for_unsent_cmd(200)
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
                'timestamp': self.get_ws_time_str(post_data=post_data['event']),
                'event_action': str(event_action),
            }
            event = controller_id.report_sys_ev(
                description=_('Output control from Software'),
                post_data=post_data,
                sys_ev_dict=sys_event_dict
            )

            return controller_id.read_status().send_command(200)
        # SOT Denied (firmware v7.13+): arm/disarm attempt refused by controller.
        # Same semantics as event 33 (Zone Arm/Disarm Denied) — card event with
        # direction derived from current zone state (line_id.armed).
        # Falls back to a system event when no cardholder is known.
        elif event_action in [32]:
            if is_card_event and card_id:
                line_id = controller_id.alarm_line_ids.filtered(
                    lambda l: l.line_number == reader_num)
                event_dict = {
                    'ctrl_addr': controller_id.ctrl_id,
                    'door_id': door and door.id or False,
                    'reader_id': reader_id.id,
                    'alarm_line_id': line_id.id,
                    'card_id': card_id and card_id.id or None,
                    'event_time': self.get_ws_time_str(post_data=post_data['event']),
                    'event_action': line_id.armed == 'arm' and '15' or '5',
                    'more_json': json.dumps(post_data),
                }

                if reader_id.mode == '03' and not controller_id.is_vending_ctrl():  # Card and workcode
                    wc = workcodes_env.search([
                        ('workcode', '=', dt),
                        ('company_id', '=', self.company_id.id)
                    ])
                    if len(wc) == 0:
                        event_dict['workcode'] = dt
                    else:
                        event_dict['workcode_id'] = wc.id

                ev_env.create(event_dict)
                return self.check_for_unsent_cmd(200)
            # No cardholder identified — record as system event so the
            # controller still gets a 200 and stops retrying.
            try:
                reader_byte = int(post_data['event'].get('reader', 0))
            except (TypeError, ValueError):
                reader_byte = 0
            msg = _('Arm denied') if reader_byte & 0x10 else _('Disarm denied')
            sys_event_dict = {
                'door_id': door and door.id or False,
                'timestamp': self.get_ws_time_str(post_data=post_data['event']),
                'event_action': str(event_action),
                'error_description': msg,
            }
            controller_id.report_sys_ev(
                description=msg,
                post_data=post_data,
                sys_ev_dict=sys_event_dict,
            )
            return self.check_for_unsent_cmd(200)
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
                    'event_time': self.get_ws_time_str(post_data=post_data['event']),
                    'event_action': line_id.armed == 'arm' and '15' or '5',
                    'more_json': json.dumps(post_data),
                }

                if reader_id.mode == '03' and not controller_id.is_vending_ctrl():  # Card and workcode
                    wc = workcodes_env.search([
                        ('workcode', '=', dt),
                        ('company_id', '=', self.company_id.id)
                    ])
                    if len(wc) == 0:
                        event_dict['workcode'] = dt
                    else:
                        event_dict['workcode_id'] = wc.id

                # card_id.get_owner(event_dict)
                event = ev_env.create(event_dict)
                return self.check_for_unsent_cmd(200)
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
                'door_id': line_id and line_id.door_id and line_id.enableAC and line_id.door_id.id or None,
                'alarm_line_id': line_id and line_id.id or None,
            }
            if is_card_event:  # User event only for event 35
                event_dict.update({
                    'ctrl_addr': controller_id.ctrl_id,
                    'card_id': card_id and card_id.id or None,
                    'reader_id': reader_id and reader_id.id or None,
                    'event_time': self.get_ws_time_str(post_data['event']),
                    'event_action': line_id.armed == 'arm' and '10' or '11'
                })
                card_id.get_owner(event_dict)
                event = ev_env.create(event_dict)
            else:  # System Event for event 20 and 34
                event_dict.update({
                    'controller_id': controller_id.id,
                    'timestamp': self.get_ws_time_str(post_data['event']),
                    'event_action': str(event_action),
                    'siren': siren,
                    'error_description': line_id and f"{line_id.state} / {line_id.armed}" or ''
                })
                event = controller_id.report_sys_ev(_('Hardware Event'), post_data=post_data, sys_ev_dict=event_dict)
                controller_id.siren_state = siren

            # return controller_id.read_status().send_command(200)
            return self.check_for_unsent_cmd(200)
        # Hotel reader events
        elif event_action in [36, 37, 38]:
            pin = post_data['event']['dt']
            event_dict = {
                'ctrl_addr': controller_id.ctrl_id,
                'door_id': reader_id.door_id.id,
                'reader_id': reader_id.id,
                'event_time': self.get_ws_time_str(post_data['event']),
                'event_action': str(8 - int(pin)) if event_action == 36 else '12' if event_action == 38 else '9',
            }
            if (event_dict['event_action'] in ['8', '9']) and not card_id:  # Card Denied Insert or Ejected unknown card
                sys_event_dict = {
                    'door_id': door and door.id or False,
                    'timestamp': self.get_ws_time_str(post_data=post_data['event']),
                    'event_action': event_dict['event_action'],
                    'card_number': card_num or None,
                    'input_js': card_num,
                }

                event = controller_id.report_sys_ev(
                    description=_('Could not find the card'),
                    post_data=post_data,
                    sys_ev_dict=sys_event_dict
                )
                return self.check_for_unsent_cmd(200)
            if event_action in [38]:  # button
                event_dict['more_json'] = json.dumps({"state": int(pin) == 1})
            # if event_action in [37]:  # eject
            #     event_dict['more_json'] = json.dumps({"eject": reader.id})
            # if event_action in [36] and event_dict['event_action'] == 7:  # Insert
            #     event_dict['more_json'] = json.dumps({"insert": reader.id})
            if card_id:
                card_id.get_owner(event_dict)
                event = ev_env.create(event_dict)
            else:  # Card event with unknown card
                sys_event_dict = {
                    'door_id': door and door.id or False,
                    'timestamp': self.get_ws_time_str(post_data=post_data['event']),
                    'event_action': str(event_action),
                    'card_number': card_num or None,
                    'input_js': card_num,
                }

                event = controller_id.report_sys_ev(
                    description=_('Could not find the card'),
                    post_data=post_data,
                    sys_ev_dict=sys_event_dict
                )
            door.process_event(event)
            return self.check_for_unsent_cmd(200)
        # Temperature Control
        elif event_action in [51, 52, 53, 54]:
            # ('51', _('Temperature High')),        # System Event, Temperature Event
            # ('52', _('Temperature Normal')),      # Temperature Event
            # ('53', _('Temperature Low')),         # System Event, Temperature Event
            # ('54', _('Temperature Error')),       # System Event
            if event_action in [51, 53, 54]:  # System Event
                controller_id.report_sys_ev(
                    description=_('Event from Temperature Sensor'),
                    post_data=post_data
                )

            if event_action in [51, 52, 53]:  # Temperature Event
                th_id = controller_id._find_th_sensor(internal_number=reader_num)
                if th_id:
                    th_id.write_log(
                        self.get_ws_time_str(post_data=post_data['event']),
                        {'t': temp_data}
                    )

            return self.check_for_unsent_cmd(200)
        # Cloud request 64
        elif event_action in [64]:
            if not card_id:
                sys_event_dict = {
                    'door_id': door and door.id or False,
                    'timestamp': self.get_ws_time_str(post_data=post_data['event']),
                    'event_action': str(event_action),
                    'card_number': card_num or None,
                }
                event = controller_id.report_sys_ev(
                    description=_('Could not find the card'),
                    post_data=post_data,
                    sys_ev_dict=sys_event_dict
                )
                return self.check_for_unsent_cmd(200)
            if controller_id.is_vending_ctrl():
                return self._hw_vending_request_for_balance()
            else:
                # External db event, controller requests for permission to open or close door
                ag_ids = card_id.get_owner().hr_rfid_access_group_ids
                ret = self.env['hr.rfid.access.group.door.rel'].sudo().search([
                    ('access_group_id', 'in', ag_ids.mapped('access_group_id.id')),
                    ('door_id', 'in', reader_id.door_ids.mapped('id'))
                ])
                flag = True
                if len(ret) > 0:
                    if card_id.get_owner()._name == 'hr.employee':
                        flag = 0 == len(
                            ret.access_group_id._calc_last_user_event_in_ag(employee_id=card_id.get_owner()))
                    else:
                        flag = 0 == len(ret.access_group_id._calc_last_user_event_in_ag(partner_id=card_id.get_owner()))

                return self._hw_respond_to_ev_64(len(ret) > 0 and card_id.active is True and flag,
                                              controller_id, reader_id, card_id, post_data)
        # Don't know what is this. Just report it
        else:
            try:
                controller_id.report_sys_ev(_('Unknown event. Please contact with your support!'), post_data=post_data)
            finally:
                return self.check_for_unsent_cmd(200)

    def _hw_respond_to_ev_64(self, open_door, controller, reader, card, post_data):
        """
        :param open_door: True if door should be opened, False otherwise
        :param controller: The RFID controller object
        :param reader: The RFID reader object
        :param card: The RFID card object
        :param post_data: The data received from the POST request

        :return: Response code from sending the command
        """
        cmd_env = self.env['hr.rfid.command'].sudo()
        ev_env = self.env['hr.rfid.event.user'].sudo()
        open_door = 3 if open_door is True else 4
        cmd = {
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'DB',
            'status': 'Process',
            'ex_timestamp': fields.Datetime.now(),
        }
        if controller.is_relay_ctrl():
            data = 0
            if open_door == 3:
                user_doors = card.get_owner().get_doors()
                for door in reader.door_ids.filtered(lambda d: d in user_doors):
                    data |= 1 << (door.number - 1)
            cmd['cmd_data'] = '4000' + controller.convert_int_to_cmd_data_for_output_control(data)
        else:
            cmd['cmd_data'] = '40%02X00' % (open_door + 4 * (reader.number - 1))
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
        event['command_id'] = cmd.id
        ev_env.create(event)
        return cmd.send_command(200)
