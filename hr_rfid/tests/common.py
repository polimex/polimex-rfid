from dateutil.relativedelta import relativedelta

from odoo.api import Environment
from odoo import models, fields
from odoo.tests import common
import json
from odoo.addons.hr_rfid.controllers.polimex import get_default_io_table
import logging

_logger = logging.getLogger(__name__)

_controllers_created = 0
_TIMEOUT = 500


class RFIDAppCase(common.TransactionCase):
    def setUp(self):
        super(RFIDAppCase, self).setUp()
        self.env.ref('hr_rfid.hr_rfid_read_ctrl_status_cron').active = False
        self.env.ref('hr_rfid.hr_rfid_sync_ctrl_clock_cron').active = False
        self.env.ref('hr_rfid.hr_rfid_set_card_active_inactive_status').active = False
        self.env.user.tz = 'Europe/Sofia'
        # Create an mobile app
        self.app_url = "/hr/rfid/event"
        self.test_company_id = self.env['res.company'].create({'name': 'Test Company 1'}).id
        self.test_company2_id = self.env['res.company'].create({'name': 'Test Company 2'}).id
        self.env.ref('base.user_admin').company_ids = [
            (4, self.test_company2_id, 0),
            (4, self.test_company_id, 0)
        ]
        self.test_webstack_10_3_id = self.env['hr.rfid.webstack'].create({
            'name': 'Test Stack',
            'serial': '234567',
            'company_id': self.test_company_id,
            'available': 'a',
            'tz': 'Europe/Sofia',
            'active': True,
        })
        self.test_now = fields.Datetime.context_timestamp(
            self.test_webstack_10_3_id, fields.Datetime.now()
        )
        self.test_date_10_3 = '%02d.%02d.%02d' % (
            self.test_now.day,
            self.test_now.month,
            self.test_now.year - 2000,
        )
        self.test_dow_10_3 = '%d' % self.test_now.weekday()
        self.test_time_10_3 = '%02d:%02d:%02d' % (
            self.test_now.hour,
            self.test_now.minute,
            self.test_now.second,
        )

        self.test_ag_employee_1 = self.env['hr.rfid.access.group'].create({
            'name': 'Test Access Group 1',
            'company_id': self.test_company_id,
            # 'door_ids': "[(0, 0, {'door_id':ref('hr_rfid.demo_ctrl_icon110_D1')}), (0, 0, {'door_id': ref('hr_rfid.demo_ctrl_icon110_D2')})]"
        })

        self.test_department_id = self.env['hr.department'].create({
            'name': 'Test Department',
            'company_id': self.test_company_id,
            'hr_rfid_default_access_group': self.test_ag_employee_1.id,
            'hr_rfid_allowed_access_groups': [(4, self.test_ag_employee_1.id, 0)],

        })
        self.test_employee_tag1_id = self.env['hr.employee.category'].create({'name': 'Tag1'})
        self.test_employee_tag2_id = self.env['hr.employee.category'].create({'name': 'Tag2'})

        self.test_employee_id = self.env['hr.employee'].create({
            'name': 'Pesho Employee',
            'company_id': self.test_company_id,
            'department_id': self.test_department_id.id,
            'category_ids': [(4, self.test_employee_tag1_id.id)],
        })

        self.test_card_employee = self.env['hr.rfid.card'].create({
            'number': '1234512345',
            'card_input_type': 'w34',
            'card_reference': 'Badge 77',
            'employee_id': self.test_employee_id.id,
            'company_id': self.test_company_id,
        })

        self.test_employee_2_id = self.env['hr.employee'].create({
            'name': 'Ivan Employee',
            'company_id': self.test_company_id,
            'department_id': self.test_department_id.id,
            'category_ids': [(4, self.test_employee_tag2_id.id)],
        })

        self.test_card_employee_2 = self.env['hr.rfid.card'].create({
            'number': '1234612346',
            'card_input_type': 'w34',
            'card_reference': 'Badge 78',
            'employee_id': self.test_employee_2_id.id,
            'company_id': self.test_company_id,
        })

        self.test_ag_partner_1 = self.env['hr.rfid.access.group'].create({
            'name': 'Test Access Group 2',
            'company_id': self.test_company_id,
            # 'door_ids': "[(0, 0, {'door_id':ref('hr_rfid.demo_ctrl_icon110_D1')}), (0, 0, {'door_id': ref('hr_rfid.demo_ctrl_icon110_D2')})]"
        })

        self.test_partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'company_type': 'person',
            'is_company': False,
            'type': 'contact',
            'company_id': self.test_company_id,
        })
        self.test_partner_ag_rel = self.env['hr.rfid.access.group.contact.rel'].create({
            'access_group_id': self.test_ag_partner_1.id,
            'contact_id': self.test_partner.id,
        })

        self.test_card_partner = self.env['hr.rfid.card'].create({
            'number': '0012312345',
            'card_input_type': 'w34',
            'card_reference': 'Badge 33',
            'contact_id': self.test_partner.id,
            'company_id': self.test_company_id,
        })
        self.assertTrue(self.test_card_partner.internal_number == '0012312345', 'Check cad number w34')
        self.test_card2_partner = self.env['hr.rfid.card'].create({
            'number': '2760500060',
            'card_input_type': 'w34s',
            'card_reference': 'Badge 34',
            'contact_id': self.test_partner.id,
            'company_id': self.test_company_id,
        })
        self.assertTrue(self.test_card2_partner.internal_number == '4212158204', 'Check cad number w34s')
        self.test_card2_partner.unlink()


        self.heartbeat = 1
        self.id_num = 1

    def _get_id_num(self):
        self.id_num += 1
        return self.id_num - 1

    def _get_heartbeat(self):
        self.heartbeat += 1
        return self.heartbeat - 1

    def _check_no_commands(self, module_id=None):
        # Check for not processed responses
        module_id = module_id or self.test_webstack_10_3_id
        response = self._hearbeat(module_id)
        self.assertEqual(response, {}, 'Check no commands in queue')


    def _make_F0(self, hw_version=None, serial_number=None, sw_version=None, mode=None, inputs=None, outputs=None,
                 readers=None, time_schedules=None, io_table_lines=None, alarm_lines=None, max_cards_count=None,
                 max_events_count=None, ctrl=None):
        hw_version = ctrl and ctrl.hw_version or hw_version
        serial_number = ctrl and ctrl.serial_number or serial_number
        sw_version = ctrl and ctrl.sw_version or sw_version
        inputs = ctrl and ctrl.inputs or inputs
        outputs = ctrl and ctrl.outputs or outputs
        readers = ctrl and ctrl.readers or readers
        time_schedules = ctrl and ctrl.time_schedules or time_schedules or 0
        io_table_lines = ctrl and ctrl.io_table_lines or io_table_lines
        alarm_lines = ctrl and ctrl.alarm_lines or alarm_lines or 0
        mode = ctrl and (ctrl.mode + ctrl.external_db * 20) or mode
        max_cards_count = ctrl and ctrl.max_cards_count or max_cards_count
        max_events_count = ctrl and ctrl.max_events_count or max_events_count

        # f0 = '%02d%04d%03d%03d%03d%d%02d%d%d%d%05d%05d' % (
        #     int(hw_version),
        #     int(serial_number),
        #     int(sw_version),
        #     inputs,
        #     outputs,
        #     readers,
        #     time_schedules,
        #     io_table_lines,
        #     alarm_lines,
        #     mode,
        #     max_cards_count,
        #     max_events_count
        # )
        # f0 = ''.join(['%02d' % int(i) for i in f0])
        f0 = '%s%s%s%s%s%s%s%s%s%s%s%s' % (
            ''.join(['%02d' % int(i) for i in ('%02d' % int(hw_version))]),
            ''.join(['%02d' % int(i) for i in ('%04d' % int(serial_number))]),
            ''.join(['%02d' % int(i) for i in ('%03d' % int(sw_version))]),
            ''.join(['%02d' % int(i) for i in ('%03d' % inputs)]),
            ''.join(['%02d' % int(i) for i in ('%03d' % outputs)]),
            '%02d' % readers,
            ''.join(['%02d' % int(i) for i in ('%02d' % time_schedules)]),
            ''.join(['%02d' % int(i) for i in ('%02d' % io_table_lines)]),
            '%02d' % alarm_lines,
            '%02d' % mode,
            ''.join(['%02d' % int(i) for i in ('%05d' % max_cards_count)]),
            ''.join(['%02d' % int(i) for i in ('%05d' % max_events_count)]),
        )
        return f0

    def _get_F0_response(self, ctrl):
        if ctrl == self.c_50:
            return '0102000000010703090000010000030100000208000100010502060003000506'
        elif ctrl == self.c_110:
            return '0006000400000704000000030000030201050208000200010502060003000506'
        elif ctrl == self.c_115:
            return '0101000202000704000000050000040201050208010200090702070003000506'
        elif ctrl == self.c_Relay:
            return '0301070004060704010000050001000200080206000200090702070003000506'
        elif ctrl == self.c_130:
            return '0107000601000703090000090000080401050208000401050807000008010900'
        elif ctrl == self.c_180:
            return '0107000601000703090000090000080401050208000401050807000008010900'
        elif ctrl == self.c_temperature:
            return '0202000207080704040000050000040001050208000200000102070004000604'
        elif ctrl == self.c_turnstile:
            return '0009000601000703090000090000080401050208000401050807000008010900'
        elif ctrl == self.c_vending:
            return '0102000000010703090000010000030100000208000100010502060003000506'

    def _time_10_3(self, delta_in_seconds):
        now = self.test_now - relativedelta(seconds=delta_in_seconds)
        return '%02d:%02d:%02d' % (
            now.hour,
            now.minute,
            now.second,
        )

    def _assertResponse(self, response):
        self.assertEqual(response.status_code, 200)
        if response.text != '':
            self.assertTrue(isinstance(response.json(), dict), 'Response is not JSON (%s)' % response.text)
            # if 'error' in response.json().keys():
            #     self.assertTrue(False, 'Response contain error' + response.json()['error']['data']['message'])
            return response.json()
        else:
            return {}

    def _hearbeat(self, webstack_id):
        response = self.url_open(self.app_url,
                                 data=json.dumps(
                                     {'convertor': webstack_id.serial, 'FW': '1.3400', 'key': webstack_id.key,
                                      'heartbeat': self._get_heartbeat()}),
                                 timeout=_TIMEOUT,
                                 headers={'Content-Type': 'application/json'})
        return self._assertResponse(response)

    def _count_system_events(self, company_id = None):
        return self.env['hr.rfid.event.system'].with_company(company_id or self.test_company_id).search_count([
            ('webstack_id', '=', self.test_webstack_10_3_id.id)
        ])

    def _count_user_events(self, company_id = None):
        return self.env['hr.rfid.event.user'].search_count([
            ('employee_id.company_id', '=', company_id or self.test_company_id)
        ])

    def _user_events(self, company_id, count=True, last=False):
        if count:
            return self.env['hr.rfid.event.user'].with_company(company_id or self.test_company_id).search_count([
                # ('webstack_id', '=', self.test_webstack_10_3_id.id)
            ])
        if last:
            return self.env['hr.rfid.event.user'].with_company(company_id or self.test_company_id).search([
                # ('webstack_id', '=', self.test_webstack_10_3_id.id)
            ], limit=1)

    def _send_cmd(self, cmd, system_event=False, company_id=None):
        sys_events_count = self._count_system_events(company_id or self.test_company_id)
        response = self.url_open(self.app_url,
                                 data=json.dumps(cmd),
                                 timeout=_TIMEOUT,
                                 headers={'Content-Type': 'application/json'})
        if not response.ok:
            pass
        self.assertTrue(response.ok)
        sys_events_count -= self._count_system_events(company_id or self.test_company_id)
        if sys_events_count != 0 and not system_event:
            pass
        self.assertTrue(sys_events_count != 0 or not system_event, 'System event generated')
        if response.text != '':
            return self._assertResponse(response)
        else:
            return {}

    def _send_cmd_response(self, request_cmd, data='', module=234567, key='0000'):
        self.assertTrue(request_cmd != {})
        if data == '':
            if request_cmd['cmd'] == 'D5':
                data = request_cmd['cmd']['d']
            if request_cmd['cmd'] == 'D9':
                data = request_cmd['cmd']['d'][:2]
        response = self._send_cmd({
            "convertor": module,
            "response": {
                "id": request_cmd['cmd']['id'],
                "c": request_cmd['cmd']['c'],
                "e": 0,
                "d": data
            },
            "key": key
        })
        return response

    def _count_ctrl_waiting_cmd(self, ctrl):
        return self.env['hr.rfid.command'].search_count([('controller_id', '=', ctrl.id), ('status', '=', 'Wait')])

    def _check_no_cmd(self, ctrl):
        self.assertTrue(
            self.env['hr.rfid.command'].search_count([('controller_id', '=', ctrl.id), ('status', '=', 'Wait')]) == 0,
            'Command exists for execution. Not expecting command!!! (%s)' % ctrl.name)

    def _check_cmd_add_card(self, ctrl, count=None, rights=None, mask=None):
        cmd = self.env['hr.rfid.command'].search([
            ('controller_id', '=', ctrl.id),
            ('status', 'in', ['Wait', 'Process'])
        ], limit=count or 1)
        self.assertEqual(len(cmd), count or 1, 'No command. Expecting Add card command (%s)' % ctrl.name)
        if ctrl.is_relay_ctrl():
            operation = cmd.cmd == 'D1' and int(cmd.rights_data) > 0 and int(cmd.rights_mask) > 0
        else:
            operation = all([c.cmd == 'D1' for c in cmd]) and \
                        all([(int(c.rights_data) == rights) if rights is not None else (int(c.rights_data) > 0) for c in cmd]) and \
                        all([(int(c.rights_mask) == mask) if mask is not None else (int(c.rights_mask) > 0) for c in cmd])
        self.assertTrue(operation,
                        'Command exists for add card, but something is wrong with command parameters(%s)' % ctrl.name)
        return cmd

    def _check_cmd_delete_card(self, ctrl):
        cmd = self.env['hr.rfid.command'].search([('controller_id', '=', ctrl.id), ('status', '=', 'Wait')], limit=1)
        self.assertTrue(len(cmd) == 1, 'No command. Expecting Delete card command (%s)' % ctrl.name)
        if ctrl.is_relay_ctrl():
            operation = cmd.cmd == 'D1' and int(cmd.rights_data) == 0 and int(cmd.rights_mask) > 0
        else:
            operation = cmd.cmd == 'D1' and int(cmd.rights_data) == 0 and int(cmd.rights_mask) > 0
        self.assertTrue(operation,
                        'Command exists for delete card, but something is wrong with command parameters (%s)' % ctrl.name)
        return cmd

    def _check_cmd_add_card_and_remove(self, ctrl, count=None, rights=None, mask=None):
        self._check_cmd_add_card(ctrl, count, rights, mask).unlink()

    def _check_cmd_delete_card_and_remove(self, ctrl):
        self._check_cmd_delete_card(ctrl).unlink()

    def _clear_ctrl_cmd(self, ctrl):
        cmd_ids = self.env['hr.rfid.command'].search([('controller_id', '=', ctrl.id), ('status', 'in', ['Wait','Process'])])
        self.assertTrue(cmd_ids, 'No commands for delete. Expecting to delete something (%s)' % ctrl.name)
        cmd_ids.unlink()

    def _process_io_table(self, response, ctrl, module=234567, key='0000'):
        ctrl.read()
        self.assertTrue(response['cmd']['c'] == 'F9' and response['cmd']['d'] == '01', '(%s)' % ctrl.name)
        self.assertNotEqual(ctrl.default_io_table, '(%s)' % ctrl.name)
        io_count = 0
        while response['cmd']['c'] == 'F9':
            line = int(response['cmd']['d'], 16)
            self.assertNotEqual(ctrl.default_io_table[(line - 1) * 16:(line - 1) * 16 + 16], '(%s)' % ctrl.name)
            response = self._send_cmd({
                "convertor": module,
                "response": {
                    "id": ctrl.ctrl_id,
                    "c": "F9",
                    "e": 0,
                    "d": ctrl.default_io_table[(line - 1) * 16:(line - 1) * 16 + 16]
                },
                "key": key
            })
            io_count += 1
        ctrl.read()
        self.assertEqual(io_count, ctrl.io_table_lines, '(%s)' % ctrl.name)
        self.assertEqual(len(ctrl.io_table), len(ctrl.default_io_table), '(%s)' % ctrl.name)
        self.assertEqual(ctrl.io_table, ctrl.default_io_table, '(%s)' % ctrl.name)
        return response

    def _check_added_controller(self, ctrl):
        ctrl.read()
        self.assertTrue(ctrl.hw_version != '', '(%s)' % ctrl.name)
        self.assertTrue(ctrl.serial_number != '', '(%s)' % ctrl.name)
        self.assertTrue(ctrl.sw_version != '', '(%s)' % ctrl.name)
        self.assertTrue(ctrl.inputs > 0, '(%s)' % ctrl.name)
        self.assertTrue(ctrl.outputs > 0, '(%s)' % ctrl.name)
        self.assertTrue(ctrl.io_table_lines > 0, '(%s)' % ctrl.name)
        self.assertTrue(ctrl.mode > 0, '(%s)' % ctrl.name)
        self.assertTrue(ctrl.max_cards_count > 0, '(%s)' % ctrl.name)
        self.assertTrue(ctrl.max_events_count > 0, '(%s)' % ctrl.name)

    def _make_event_on_all_readers(self, ctrl,
                                   card=None,
                                   pin=None,
                                   date=None,
                                   day=None,
                                   time=None,
                                   event_code=None,
                                   system_event=False,
                                   relay_num=1):
        return [self._make_event(ctrl, card, pin, r, date, day, time, event_code, system_event, relay_num) for r in
                range(1, ctrl.readers + 1)]

    def _make_event(self, ctrl,
                    card=None,
                    pin=None,
                    reader=None,
                    date=None,
                    day=None,
                    time=None,
                    event_code=None,
                    system_event=False,
                    relay_num=1):
        # ctrl.read()
        if ctrl.is_relay_ctrl():
            if event_code != 3:
                relay_num = 0
            cmd = self._send_cmd({
                "convertor": ctrl.webstack_id.serial,
                "event": {"bos": 1,
                          "tos": 1,
                          "card": card is not None and card or self.test_card_employee.number,
                          "cmd": "FA",
                          "time": time or self.test_time_10_3,
                          "date": date or self.test_date_10_3,
                          "day": day or self.test_dow_10_3,
                          "dt": (pin or '0000') + "000000000000000000%02d" % relay_num,
                          # "dt": (pin or '0000') + "0000000000",
                          "err": 0,
                          "event_n": event_code or 4,  # Int(action_selection[X]
                          "id": ctrl.ctrl_id,
                          "reader": reader or 1},
                "key": ctrl.webstack_id.key
            }, system_event=system_event)
        else:
            cmd = self._send_cmd({
                "convertor": ctrl.webstack_id.serial,
                "event": {"bos": 1,
                          "tos": 1,
                          "card": card is not None and card or self.test_card_employee.number,
                          "cmd": "FA",
                          "time": time or self.test_time_10_3,
                          "date": date or self.test_date_10_3,
                          "day": day or self.test_dow_10_3,
                          "dt": (pin or '0000') + "0000000000",
                          "err": 0,
                          "event_n": event_code or 4,  # Int(action_selection[X]
                          "id": ctrl.ctrl_id,
                          "reader": reader or 1},
                "key": ctrl.webstack_id.key
            }, system_event=system_event)
        return cmd

    def _test_R_event(self, ctrl, reader=1):
        user_events_count = self._count_user_events()
        # Test with known card
        response = self._make_event(ctrl, reader=reader, event_code=3)
        self.assertEqual(response, {}, '(%s)' % ctrl.name)
        response = self._make_event(ctrl, reader=reader, event_code=4)
        self.assertEqual(response, {}, '(%s)' % ctrl.name)
        response = self._make_event(ctrl, reader=reader, event_code=5)
        self.assertEqual(response, {}, '(%s)' % ctrl.name)
        response = self._make_event(ctrl, reader=reader, event_code=6)
        self.assertEqual(response, {}, '(%s)' % ctrl.name)

        self.assertEqual(user_events_count + 4, self._count_user_events(), '(%s)' % ctrl.name)

        # Test with unknown card
        system_events_count = self._count_system_events()
        response = self._make_event(ctrl, card='1122334455', reader=reader, event_code=4+(reader-1)*4)
        self.assertEqual(response, {}, '(%s)' % ctrl.name)
        self.assertEqual(system_events_count + 1, self._count_system_events(), '(%s)' % ctrl.name)

        # response = self._make_event(self.ctrl, reader=reader+1, event_code=3, system_event=True)
        # self.assertEqual(response, {})
        pass

    def _test_R1R2(self, ctrl):
        self._test_R_event(ctrl, 1)
        self._test_R_event(ctrl, 2)
        pass

    def _test_R1R2R3R4(self, ctrl):
        self._test_R_event(ctrl, 1)
        self._test_R_event(ctrl, 2)
        self._test_R_event(ctrl, 3)
        self._test_R_event(ctrl, 4)
        pass

    def _test_Duress(self, ctrl):
        res = [self._make_event(ctrl, reader=r, event_code=1) for r in range(1, ctrl.readers + 1)]
        res.append([self._make_event(ctrl, reader=r, event_code=2) for r in range(1, ctrl.readers + 1)])
        return res

    def _test_inputs(self, ctrl):
        res = [
            self._test_Emergency(ctrl), self._test_Exit_buttons(ctrl), self._test_Door_Overtime(ctrl),
            self._test_Force_Door_Open(ctrl), self._test_Power_On(ctrl),
            self._test_External_control(ctrl)
        ]
        return res

    def _test_Emergency(self, ctrl):
        res = [self._make_event(ctrl, card=0, reader=1, event_code=19),
               self._make_event(ctrl, card=0, reader=1 + 64, event_code=19),
               self._make_event(ctrl, card=0, reader=0, event_code=19)]  # hardware On
        return res

    def _test_Exit_buttons(self, ctrl):
        return [self._make_event(ctrl, reader=d.reader_ids[0].number, event_code=21) for d in ctrl.door_ids]
    def _test_External_control(self, ctrl):
        return [self._make_event(ctrl, reader=0, event_code=29)]

    def _test_Door_Overtime(self, ctrl):
        res = [self._make_event(ctrl, reader=d.reader_ids[0].number, event_code=25) for d in ctrl.door_ids]
        self._clear_ctrl_cmd(ctrl)
        return res

    def _test_Force_Door_Open(self, ctrl):
        return [self._make_event(ctrl, reader=d.reader_ids[0].number, event_code=26) for d in ctrl.door_ids]

    def _test_Power_On(self, ctrl):
        res = self._make_event(ctrl, event_code=30)
        self._clear_ctrl_cmd(ctrl)  # Ignore new time sync
        return res

    # ('20', True, 'Siren ON/OFF'),
    # ('27', False, 'DELAY ZONE ON (if out) Z4,Z3,Z2,Z1'),
    # ('28', False, 'DELAY ZONE OFF (if in) Z4,Z3,Z2,Z1'),
    # ('30', False, 'Power On event'),
    # ('31', False, 'Open/Close Door From PC'),
    # ('33', False, 'Zone Arm/Disarm Denied'),  # User Event
    # ('34', False, 'Zone Status'),
    # ('35', False, 'Zone Arm/Disarm'),  # User Event
    # ('36', False, 'Inserted Card'),  # User Event
    # ('37', False, 'Ejected Card'),  # User Event
    # ('38', False, 'Hotel Button Pressed'),  # User Event
    # ('45', False, '1-W ERROR (wiring problems)'),
    # ('47', False, 'Vending Purchase Complete'),
    # ('48', False, 'Vending Error1'),
    # ('49', False, 'Vending Error2'),
    # ('51', False, 'Temperature High'),
    # ('52', False, 'Temperature Normal'),
    # ('53', False, 'Temperature Low'),
    # ('54', False, 'Temperature Error'),
    # ('64', False, 'Cloud Card Request'),  # User Event
    # ('99', False, 'System Event')

    def _change_mode(self, ctrl, mode):
        if mode < 3:
            ctrl.mode_selection = str(mode)
        else:
            ctrl.mode_selection_4 = str(mode)
        response = self._hearbeat(ctrl.webstack_id)
        self.assertNotEqual(response, {})
        mode = response['cmd']['d']
        response = self._send_cmd_response(response)  # To D5 change mode
        # F0 Mode 2: 0006000400000704000000030000030201050208002200010502060003000506
        # F0 Mode 1: 0006000400000704000000030000030201050208002100010502060003000506
        #             '0006000400000704000000030000030201050208000200010502060003000506'
        #             '0006000400000704000000030000030201050208002100010502060003000506'
        #'0107000601000703090000090000080401050208000401050807000008010900'
        #'0107000601000703090000090000080401050208000201050807000008010900'
        original_F0 = self.default_F0[int(ctrl.hw_version)]
        new_F0 = original_F0[:42] + mode + original_F0[44:]

        response = self._send_cmd_response(response, new_F0)
        while response != {} and response['cmd']['c'] == 'D9':
            response = self._send_cmd_response(response)  # To F0 to confirm the mode

        response = self._send_cmd_response(response, '00')  # To FC read APB
        pass

    def _ev64(self, ctrl):
        if not ctrl.external_db:
            # Prepare controller for External DB
            ctrl.external_db = True
            response = self._hearbeat(ctrl.webstack_id)
            self.assertEqual(response, {'cmd': {'id': ctrl.ctrl_id, 'c': 'D5', 'd': '2%d' % ctrl.mode}},
                             '(%s)' % ctrl.name)
            response = self._send_cmd_response(response)
            self.assertEqual(response, {'cmd': {'id': ctrl.ctrl_id, 'c': 'F0', 'd': ''}}, '(%s)' % ctrl.name)
            response = self._send_cmd_response(response, self._make_F0(mode=2 + ctrl.mode, ctrl=ctrl))
            self.assertEqual(response, {}, '(%s)' % ctrl.name)
            # Try before grand access (expected Denied)
            response = self._make_event(ctrl, card=self.test_card_employee.number, reader=1, event_code=64)
            if ctrl.is_relay_ctrl():
                self.assertEqual(response,
                                 {'cmd': {'id': ctrl.ctrl_id, 'c': 'DB', 'd': '4000000000000000000000000000'}},
                                 '(%s)' % ctrl.name)
            else:
                self.assertEqual(response, {'cmd': {'id': ctrl.ctrl_id, 'c': 'DB', 'd': '400400'}}, '(%s)' % ctrl.name)
            response = self._send_cmd_response(response, '400400')
            self.assertEqual(response, {})
            # Grand access to doors in controller
            cmd_count = self._count_ctrl_waiting_cmd(ctrl)
            self.test_ag_employee_1.add_doors(ctrl.door_ids)
            # Not expecting command for add card
            new_cmd_count = self._count_ctrl_waiting_cmd(ctrl)
            self.assertEqual(new_cmd_count, cmd_count)

            # Try access with card (Expected Granted)
            response = self._make_event(ctrl, card=self.test_card_employee.number, reader=1, event_code=64)
            if ctrl.is_relay_ctrl():
                self.assertEqual(response,
                                 {'cmd': {'id': ctrl.ctrl_id, 'c': 'DB', 'd': '4000000000000000000003020505'}},
                                 '(%s)' % ctrl.name)
            else:
                self.assertEqual(response, {'cmd': {'id': ctrl.ctrl_id, 'c': 'DB', 'd': '400300'}}, '(%s)' % ctrl.name)
            response = self._send_cmd_response(response, '400300')
            self.assertEqual(response, {})
            # Set delay on access group
            self.test_ag_employee_1.delay_between_events = 60
            # Try access in delay previous (expected Denied)
            last_event_id = self.test_ag_employee_1._calc_last_user_event_in_ag(employee_id=self.test_employee_id)
            _logger.info(
                '%s > last event: %s %s' % (fields.Datetime.now(), last_event_id.name, last_event_id.event_time))
            response = self._make_event(ctrl, card=self.test_card_employee.number, reader=1, event_code=64)
            if ctrl.is_relay_ctrl():
                self.assertEqual(response,
                                 {'cmd': {'id': ctrl.ctrl_id, 'c': 'DB', 'd': '4000000000000000000000000000'}},
                                 '(%s)' % ctrl.name)
            else:
                self.assertEqual(response, {'cmd': {'id': ctrl.ctrl_id, 'c': 'DB', 'd': '400400'}}, '(%s)' % ctrl.name)
            response = self._send_cmd_response(response, '400400')
            self.assertEqual(response, {})

            # Clean up
            self.test_ag_employee_1.del_doors(ctrl.door_ids)
            self.test_ag_employee_1.delay_between_events = 0
            ctrl.external_db = False
            response = self._hearbeat(ctrl.webstack_id)
            self.assertEqual(response, {'cmd': {'id': ctrl.ctrl_id, 'c': 'D5', 'd': '%02d' % ctrl.mode}},
                             '(%s)' % ctrl.name)
            response = self._send_cmd_response(response)
            self.assertEqual(response, {'cmd': {'id': ctrl.ctrl_id, 'c': 'F0', 'd': ''}}, '(%s)' % ctrl.name)
            response = self._send_cmd_response(response, self._make_F0(ctrl=ctrl))
            self.assertEqual(response, {})
            pass
