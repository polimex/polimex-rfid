from odoo.api import Environment
from odoo import models, fields
from odoo.tests import common
import json
from odoo.addons.hr_rfid.controllers.polimex import get_default_io_table

_controllers_created = 0


class RFIDAppCase(common.TransactionCase):
    def setUp(self):
        super(RFIDAppCase, self).setUp()
        # Create an mobile app
        self.app_url = "/hr/rfid/event"
        self.test_company_id = 1
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
        self.test_date_10_3 = '%d.%d.%d' %(
            self.test_now.day,
            self.test_now.month,
            self.test_now.year-2000,
        )
        self.test_dow_10_3 = '%d' % self.test_now.weekday()
        self.test_time_10_3 = '%d:%d:%d' %(
            self.test_now.hour+1,
            self.test_now.minute,
            self.test_now.second,
        )

        self.test_department_id = self.env['hr.department'].create({
            'name': 'Test Department',
            'company_id': self.test_company_id,
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
        })

        self.test_partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'company_type': 'person',
            'is_company': False,
            'type': 'contact',
            'company_id': self.test_company_id,
        })

        self.test_card_partner = self.env['hr.rfid.card'].create({
            'number': '0012312345',
            'card_reference': 'Badge 33',
            'contact_id': self.test_partner.id,

        })
        self.c_50 = None
        self.c_110 = None
        self.c_115 = None
        self.c_130 = None
        self.c_180 = None
        self.c_turnstile = None
        self.c_vending = None

    def _assertResponse(self, response):
        self.assertEqual(response.status_code, 200)
        if response.text != '':
            self.assertTrue(isinstance(response.json(), dict), 'Response is not JSON')
        # if 'error' in response.json().keys():
        #     self.assertTrue(False, 'Response contain error' + response.json()['error']['data']['message'])
        return response

    def _hearbeat(self, serial=234567, key='0000'):
        response = self.url_open(self.app_url,
                                 data=json.dumps({'convertor': serial, 'FW': '1.3400', 'key': key, 'heartbeat': 22}),
                                 timeout=20,
                                 headers={'Content-Type': 'application/json'})
        return self._assertResponse(response).json()

    def _send_cmd(self, cmd):
        sys_events_count = self.env['hr.rfid.event.system'].search_count([
            ('webstack_id', '=', self.test_webstack_10_3_id.id)
        ])
        response = self.url_open(self.app_url,
                                 data=json.dumps(cmd),
                                 timeout=20,
                                 headers={'Content-Type': 'application/json'})
        if not response.ok:
            pass
        self.assertTrue(response.ok)
        sys_events_count -= self.env['hr.rfid.event.system'].search_count([
            ('webstack_id', '=', self.test_webstack_10_3_id.id)
        ])
        if sys_events_count != 0:
            pass
        self.assertEqual(sys_events_count, 0, 'System event generated')
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
        self.assertTrue(response['cmd']['c'] == 'F9' and response['cmd']['d'] == '01')
        self.assertNotEqual(ctrl.default_io_table, None)
        io_count = 0
        while response['cmd']['c'] == 'F9':
            line = int(response['cmd']['d'], 16)
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
        self.assertEqual(io_count, ctrl.io_table_lines)
        self.assertEqual(len(ctrl.io_table), len(ctrl.default_io_table))
        self.assertEqual(ctrl.io_table, ctrl.default_io_table)
        return response
