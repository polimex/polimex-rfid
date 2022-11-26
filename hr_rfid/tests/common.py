from dateutil.relativedelta import relativedelta

from odoo.api import Environment
from odoo import models, fields
from odoo.tests import common
import json
from odoo.addons.hr_rfid.controllers.polimex import get_default_io_table

_controllers_created = 0


class RFIDAppCase(common.TransactionCase):
    def setUp(self):
        super(RFIDAppCase, self).setUp()
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

        self.test_employee_id = self.env['hr.employee'].create({
            'name': 'Pesho Employee',
            'company_id': self.test_company_id,
            'department_id': self.test_department_id.id,
        })

        self.test_card_employee = self.env['hr.rfid.card'].create({
            'number': '1234512345',
            'card_reference': 'Badge 77',
            'employee_id': self.test_employee_id.id,
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
            'access_group_id':  self.test_ag_partner_1.id,
            'contact_id':  self.test_partner.id,
        })

        self.test_card_partner = self.env['hr.rfid.card'].create({
            'number': '0012312345',
            'card_reference': 'Badge 33',
            'contact_id': self.test_partner.id,
            'company_id': self.test_company_id,
        })

        self.c_50 = None
        self.c_110 = None
        self.c_115 = None
        self.c_130 = None
        self.c_180 = None
        self.c_turnstile = None
        self.c_vending = None
        self.c_temperature = None

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
            self.assertTrue(isinstance(response.json(), dict), 'Response is not JSON')
        # if 'error' in response.json().keys():
        #     self.assertTrue(False, 'Response contain error' + response.json()['error']['data']['message'])
        return response

    def _hearbeat(self, webstack_id):
        response = self.url_open(self.app_url,
                                 data=json.dumps({'convertor': webstack_id.serial, 'FW': '1.3400', 'key': webstack_id.key, 'heartbeat': 22}),
                                 timeout=20,
                                 headers={'Content-Type': 'application/json'})
        return self._assertResponse(response).json()

    def _count_system_events(self, company_id):
        return self.env['hr.rfid.event.system'].with_company(company_id or self.test_company_id).search_count([
            ('webstack_id', '=', self.test_webstack_10_3_id.id)
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

    def _make_F0(self, hw_ver=12, serial_num=5, sw_ver=740, mode=1, inputs=1,  outputs=3,
                 time_schedules=4,  io_table_lines=28, alarm_lines=0, max_cards_count=3000, max_events_count=3000):
        #0102000000010703090000010000030100000208000100010502060003000506 iCON50
        #0102000000010703090000010000030004000002080100030500000001050000
        #12 0001 739 001 003 1 0028 0 1 01526 03056 iCON50
        f0 = '%02d%04d%03d%03d%03d%02d%02d%d%d%05d%05d' % (
            hw_ver, serial_num, sw_ver, inputs, outputs, time_schedules, alarm_lines, io_table_lines,
            mode, max_cards_count, max_events_count
        )
        f0 = ''.join(['%02d' % int(i) for i in f0])
        pass
        # F0Parse.hw_ver: str(bytes_to_num(data, 0, 2)),
        # F0Parse.serial_num: str(bytes_to_num(data, 4, 4)),
        # F0Parse.sw_ver: str(bytes_to_num(data, 12, 3)),
        # F0Parse.inputs: bytes_to_num(data, 18, 3),
        # F0Parse.outputs: bytes_to_num(data, 24, 3),
        # F0Parse.time_schedules: bytes_to_num(data, 32, 2),
        # F0Parse.io_table_lines: bytes_to_num(data, 36, 2),
        # F0Parse.alarm_lines: bytes_to_num(data, 40, 1),
        # F0Parse.mode: int(data[42:44], 16),
        # F0Parse.max_cards_count: bytes_to_num(data, 44, 5),
        # F0Parse.max_events_count: bytes_to_num(data, 54, 5),
        #
        # hw_ver = 0
        # serial_num = 1
        # sw_ver = 2
        # inputs = 3
        # outputs = 4
        # time_schedules = 5
        # io_table_lines = 6
        # alarm_lines = 7
        # mode = 8
        # max_cards_count = 9
        # max_events_count = 10

    def _send_cmd(self, cmd, system_event=False, company_id=None):
        sys_events_count = self._count_system_events(company_id or self.test_company_id)
        response = self.url_open(self.app_url,
                                 data=json.dumps(cmd),
                                 timeout=200,
                                 headers={'Content-Type': 'application/json'})
        if not response.ok:
            pass
        self.assertTrue(response.ok)
        sys_events_count -= self._count_system_events(company_id or self.test_company_id)
        if sys_events_count != 0 and not system_event:
            pass
        self.assertTrue(sys_events_count != 0 or not system_event, 'System event generated')
        if response.text != '':
            return self._assertResponse(response).json()
        else:
            return {}

    def _send_cmd_response(self, request_cmd, data='', module=234567, key='0000'):
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

    def _process_io_table(self, response, ctrl, module=234567, key='0000'):
        ctrl.read()
        self.assertTrue(response['cmd']['c'] == 'F9' and response['cmd']['d'] == '01')
        self.assertNotEqual(ctrl.default_io_table, '')
        io_count = 0
        while response['cmd']['c'] == 'F9':
            line = int(response['cmd']['d'], 16)
            self.assertNotEqual(ctrl.default_io_table[(line - 1) * 16:(line - 1) * 16 + 16], '')
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
        self.assertEqual(io_count, ctrl.io_table_lines)
        self.assertEqual(len(ctrl.io_table), len(ctrl.default_io_table))
        self.assertEqual(ctrl.io_table, ctrl.default_io_table)
        return response

    def _check_added_controller(self, ctrl):
        ctrl.read()
        self.assertTrue(ctrl.hw_version != '')
        self.assertTrue(ctrl.serial_number != '')
        self.assertTrue(ctrl.sw_version != '')
        self.assertTrue(ctrl.inputs > 0)
        self.assertTrue(ctrl.outputs > 0)
        self.assertTrue(ctrl.io_table_lines > 0)
        self.assertTrue(ctrl.mode > 0)
        self.assertTrue(ctrl.max_cards_count > 0)
        self.assertTrue(ctrl.max_events_count > 0)

    def _make_event(self, ctrl,
                    card=None,
                    pin=None,
                    reader=None,
                    date=None,
                    day=None,
                    time=None,
                    event_code=None,
                    system_event=False):
        ctrl.read()
        return self._send_cmd({
            "convertor": ctrl.webstack_id.serial,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": card or self.test_card_employee.number,
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

    def _test_R_event(self, ctrl, reader=1):
        response = self._make_event(ctrl, reader=reader, event_code=3)
        self.assertEqual(response, {})
        response = self._make_event(ctrl, reader=reader, event_code=4)
        self.assertEqual(response, {})
        response = self._make_event(ctrl, reader=reader, event_code=5)
        self.assertEqual(response, {})
        response = self._make_event(ctrl, reader=reader, event_code=6)
        self.assertEqual(response, {})
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

    def _change_mode(self, ctrl, mode):
        if mode < 3:
            ctrl.mode_selection = str(mode)
        else:
            ctrl.mode_selection_4 = str(mode)
        response = self._hearbeat(ctrl.webstack_id)

    def _ev64(self, ctrl):
        if not ctrl.external_db:
            ctrl.external_db = True
            response = self._hearbeat(ctrl.webstack_id)
            self.assertEqual(response, {'cmd': {'id': ctrl.ctrl_id, 'c': 'D5', 'd': '22'}}, )
            response = self._send_cmd_response(response)
            self.assertEqual(response, {'cmd': {'id': ctrl.ctrl_id, 'c': 'F0', 'd': ''}}, )
            response = self._send_cmd_response(response,'0006000400000704000000030000030201050208002200010502060003000506')
            self.assertEqual(response, {})
            self.test_ag_employee_1.add_doors(ctrl.door_ids)
            # response = self._hearbeat(ctrl.webstack_id)
            # self.assertEqual(response, {})
            response = self._make_event(ctrl, card=self.test_card_employee.number, reader=1, event_code=64)
            self.assertEqual(response, {'cmd': {'id': ctrl.ctrl_id, 'c': 'DB', 'd': '400300'}}, )
            response = self._send_cmd_response(response, '400300')
            self.test_ag_employee_1.delay_between_events = 60
            response = self._make_event(ctrl, card=self.test_card_employee.number, reader=1, event_code=64)
            self.assertEqual(response, {'cmd': {'id': ctrl.ctrl_id, 'c': 'DB', 'd': '400400'}}, )
            response = self._send_cmd_response(response, '400400')
            # response = self._make_event(ctrl, card=self.test_card_employee.number, reader=1, time=self._time_10_3(30), event_code=3)
            # response = self._make_event(ctrl, card=self.test_card_employee.number, reader=1, event_code=64)
            # self.assertEqual(response, {'cmd': {'id': ctrl.ctrl_id, 'c': 'DB', 'd': '400400'}}, )
            pass
