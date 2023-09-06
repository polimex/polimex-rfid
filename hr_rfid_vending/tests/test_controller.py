# Copyright 2022 Polimex Holding Ltd..
# License APL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.hr_rfid.tests.common import RFIDAppCase
from odoo.addons.hr_rfid.controllers.polimex import get_default_io_table
from odoo.tests.common import HttpCase, tagged
import json

# {'convertor': 242865, 'key': '0000', 'event': {'id': 38, 'cmd': 'FA', 'err': 0, 'tos': 1, 'bos': 1, 'event_n': 4, 'time': '17:45:15', 'day': 4, 'date': '13.10.22', 'card': '1598240645', 'reader': 1, 'dt': '00000000000000'}}
# TODO Add this event if happend
@tagged('rfid_vending')
class VendingController(RFIDAppCase, HttpCase):
    def test_app(self):
        self._add_Vending()
        self._add_products()
        self._balance_test()
        self._sale_test()
        self._event_test()

    def _add_Vending(self, module=234567, key='0000', id=7):
        self.c_vending = self.env['hr.rfid.ctrl'].create({
            'name': 'Turnstile Vending',
            'ctrl_id': id,
            'webstack_id': self.test_webstack_10_3_id.id
        })
        self.c_vending.read_controller_information_cmd()

        response = self._hearbeat(self.c_vending.webstack_id)
        self.assertEqual(response, {'cmd': {'id': id, 'c': 'F0', 'd': ''}}, )
        response = self._send_cmd_response(response, '0106000003090704020000010000010201050200002200090702070003000506')
        self.assertTrue(
            response['cmd']['c'] == 'D5' and response['cmd']['d'] == '22')  # {'cmd': {'id': 7, 'c': 'D5', 'd': '22'}}
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F0')
        response = self._send_cmd_response(response, '0106000003090704020000010000010201050200002200090702070003000506')
        self.assertTrue(response['cmd']['c'] == 'D7')  #
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'DC')
        response = self._send_cmd_response(response)
        self.assertTrue(response['cmd']['c'] == 'F6')
        response = self._send_cmd_response(response, '010100010100010100010100')
        self.assertTrue(response['cmd']['c'] == 'F9' and response['cmd']['d'] == '01')
        response = self._process_io_table(response, self.c_vending)
        self.assertTrue(response['cmd']['c'] == 'B3')
        response = self._send_cmd_response(response, '00006E010752079200000000000000000000000000000000')
        self.assertTrue(response == {})

    def _add_products(self, module=234567, key='0000', id=7):
        products = []
        wiz = self.env['hr.rfid.ctrl.vending.settings'].with_context(
            ids=[self.c_vending.id],
        ).create({'controller_id': self.c_vending.id})
        for i in range(0, 8):
            products.append(
                self.env['product.template'].create({
                    'name': 'Vending Product #%d' % (i + 1),
                    'list_price': (i+1)*0.05,
                })
            )
        rows = self.c_vending.create_vending_rows()
        rows[0].write({'row_num': 1,
                       'controller_id': self.c_vending.id,
                       'item1': products[0].id,
                       'item2': products[1].id,
                       'item3': products[2].id,
                       'item4': products[3].id})
        rows[1].write({'row_num': 2,
                       'controller_id': self.c_vending.id,
                       'item1': products[4].id,
                       'item2': products[5].id,
                       'item3': products[6].id,
                       'item4': products[7].id})
        wiz.vending_row_ids = [(6, 0, rows.mapped('id'))]
        wiz.show_price_timeout = 15
        wiz.scale_factor = 5

        wiz.save_settings()
        response = self._hearbeat(self.c_vending.webstack_id)
        io_count = 0
        while 'cmd' in response.keys() and response['cmd']['c'] == 'D9':
            response = self._send_cmd_response(response)
            io_count += 1
        self.assertEqual(io_count, 20)
        self.assertEqual(self.c_vending.io_table,
                         '000400030002000100080007000600050F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F000000000000000F0000000000000005')

    def _balance_test(self, module=234567, key='0000', id=7):
        # add balance
        self.assertEqual(self.test_employee_id.hr_rfid_vending_balance, 0)
        self.test_employee_id.hr_rfid_vending_add_to_balance(2)
        self.assertEqual(self.test_employee_id.hr_rfid_vending_balance, 2)
        self.assertEqual(
            1,
            self.env['hr.rfid.vending.balance.history'].search_count([
                ('employee_id', '=', self.test_employee_id.id)
            ])
        )
        # request balance
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000000000000",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 64, "id": id, "reader": 1},
            "key": key
        })
        self.assertEqual(response, {'cmd': {'id': 7, 'c': 'DB', 'd': '4000010203040501020304050208'}})
        response = self._send_cmd_response(response, '0000')
        self.assertEqual(response, {})
        # self recharge
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00006300000001",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 50, "id": id, "reader": 1},
            "key": key
        })
        self.test_employee_id.read(['hr_rfid_vending_recharge_balance'])
        self.assertEqual(self.test_employee_id.hr_rfid_vending_recharge_balance, 0.05)
        self.assertEqual(response, {})
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000000000000",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 64, "id": id, "reader": 1},
            "key": key
        })
        self.assertEqual(response, {'cmd': {'id': 7, 'c': 'DB', 'd': '4000010203040501020304050209'}})
        response = self._send_cmd_response(response, '0000')
        self.assertEqual(response, {})

    def _sale_test(self, module=234567, key='0000', id=7):
        # sale with card and product
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000100010208",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 47, "id": id, "reader": 1},
            "key": key
        })
        self.assertEqual(response, {})
        # request balance for check
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000000000000",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 64, "id": id, "reader": 1},
            "key": key
        })
        self.assertEqual(response, {'cmd': {'id': 7, 'c': 'DB', 'd': '4000010203040501020304050208'}})
        response = self._send_cmd_response(response, '0000')
        self.assertEqual(response, {})

        # sale with card without product
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000000010207",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 47, "id": id, "reader": 1},
            "key": key
        })
        self.assertEqual(response, {})
        # request balance for check
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000000000000",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 64, "id": id, "reader": 1},
            "key": key
        })
        self.assertEqual(response, {'cmd': {'id': 7, 'c': 'DB', 'd': '4000010203040501020304050207'}})
        response = self._send_cmd_response(response, '0000')
        self.assertEqual(response, {})

        # sale without card and without product
        # {"convertor": 425757,
        #  "event": {"bos": 1, "card": "0000000000", "cmd": "FA", "date": "10.12.22", "day": 3, "dt": "00000d000c0f06",
        #            "err": 0, "event_n": 47, "id": 1, "reader": 1, "time": "17:06:54", "tos": 1}, "key": "66F6"}
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": '0000000000',
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000000010f0e",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 47, "id": id, "reader": 1},
            "key": key
        })
        self.assertEqual(response, {})
        self.c_vending.read(['cash_contained'])
        self.assertEqual(self.c_vending.cash_contained, 0.05)
        pass
    def _event_test(self, module=234567, key='0000', id=7):
        #{"convertor":242865,"key":"0000","event":{"id":38,"cmd":"FA","err":99,"tos":9,"bos":1,"event_n":50,"time":"11:01:51","day":1,"date":"31.10.22","card":"0016226318","reader":1,"dt":"00006300000000"}
        # sale with card and product
        a = {"convertor": 242865,
             "key": "0000",
             "event": {
                 "id": 38,
                 "cmd": "FA",
                 "err": 99,
                 "tos": 9,
                 "bos": 1,
                 "event_n": 50,
                 "time": "11:01:51",
                 "day": 1,
                 "date": "31.10.22",
                 "card": "0016226318",
                 "reader": 1,
                 "dt": "00006300000000"}
             }
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000100010208",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 47, "id": id, "reader": 1},
            "key": key
        })
        self.assertEqual(response, {})
        # request balance for check
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000000000000",
                      "time": self.test_time_10_3,
                      "err": 15, "event_n": 64, "id": id, "reader": 1},
            "key": key
        })
        self.assertEqual(response, {'cmd': {'id': 7, 'c': 'DB', 'd': '4000010203040501020304050208'}})
        response = self._send_cmd_response(response, '0000')
        self.assertEqual(response, {})

        # sale with card without product
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000000010207",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 47, "id": id, "reader": 1},
            "key": key
        })
        self.assertEqual(response, {})
        # request balance for check
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000000000000",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 64, "id": id, "reader": 1},
            "key": key
        })
        self.assertEqual(response, {'cmd': {'id': 7, 'c': 'DB', 'd': '4000010203040501020304050207'}})
        response = self._send_cmd_response(response, '0000')
        self.assertEqual(response, {})

        # sale without card and without product
        # {"convertor": 425757,
        #  "event": {"bos": 1, "card": "0000000000", "cmd": "FA", "date": "10.12.22", "day": 3, "dt": "00000d000c0f06",
        #            "err": 0, "event_n": 47, "id": 1, "reader": 1, "time": "17:06:54", "tos": 1}, "key": "66F6"}
        response = self._send_cmd({
            "convertor": module,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": '0000000000',
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000000010f0e",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 47, "id": id, "reader": 1},
            "key": key
        })
        self.assertEqual(response, {})
        self.assertEqual(self.c_vending.cash_contained, 0.05)
        pass
