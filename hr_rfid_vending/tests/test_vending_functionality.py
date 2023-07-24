# Copyright 2022 Polimex Holding Ltd..
# License APL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.hr_rfid.tests.controller import RFIDController
from odoo.tests.common import HttpCase, tagged

from odoo.tools import float_compare


# {'convertor': 242865, 'key': '0000', 'event': {'id': 38, 'cmd': 'FA', 'err': 0, 'tos': 1, 'bos': 1, 'event_n': 4, 'time': '17:45:15', 'day': 4, 'date': '13.10.22', 'card': '1598240645', 'reader': 1, 'dt': '00000000000000'}}
# TODO Add this event if happend
@tagged('rfid_vending')
class VendingController(RFIDController, HttpCase):
    def test_vending_functionality(self):
        self._add_Vending()

        self._add_products()

        self._balance_test()

        self._sale_test()

    def _add_products(self, ctrl_id=None):
        ctrl_id = ctrl_id or self.c_vending
        products = []
        wiz = self.env['hr.rfid.ctrl.vending.settings'].with_context(
            ids=[ctrl_id.id],
        ).create({'controller_id': ctrl_id.id})
        for i in range(0, 8):
            products.append(
                self.env['product.template'].create({
                    'name': 'Vending Product #%d' % (i + 1),
                    'list_price': (i + 1) * 0.05,
                })
            )
        rows = ctrl_id.create_vending_rows()
        rows[0].write({'row_num': 1,
                       'controller_id': ctrl_id.id,
                       'item1': products[0].id,
                       'item2': products[1].id,
                       'item3': products[2].id,
                       'item4': products[3].id})
        rows[1].write({'row_num': 2,
                       'controller_id': ctrl_id.id,
                       'item1': products[4].id,
                       'item2': products[5].id,
                       'item3': products[6].id,
                       'item4': products[7].id})
        wiz.vending_row_ids = [(6, 0, rows.mapped('id'))]
        wiz.show_price_timeout = 15
        wiz.scale_factor = 5

        wiz.save_settings()
        response = self._hearbeat(ctrl_id.webstack_id)
        io_count = 0
        while 'cmd' in response.keys() and response['cmd']['c'] == 'D9':
            response = self._send_cmd_response(response)
            io_count += 1
        self.assertEqual(io_count, 20)
        self.assertEqual(self.c_vending.io_table,
                         '000400030002000100080007000600050F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F0F000000000000000F0000000000000005')
        self._check_no_commands()

    def _check_history_records_count(self, count):
        self.assertEqual(
            count,
            self.env['hr.rfid.vending.balance.history'].search_count([
                ('employee_id', '=', self.test_employee_id.id)
            ]),
            "Check history balance count")

    def _check_balance(self, expected, ctrl_id=None):
        ctrl_id = ctrl_id or self.c_vending
        response = self._send_cmd({
            "convertor": ctrl_id.webstack_id.serial,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      "dt": "00000000000000",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 64, "id": ctrl_id.ctrl_id, "reader": 1},
            "key": ctrl_id.webstack_id.key
        })
        if expected != 0:
            es = '{:02}'.format(expected)
            self.assertEqual(response, {
                'cmd': {'id': ctrl_id.ctrl_id, 'c': 'DB', 'd': f'4000010203040501020304050{es[0]}0{es[1]}'}})
            response = self._send_cmd_response(response, '0000')
        self.assertEqual(response, {})

    def _balance_test(self, ctrl_id=None):
        ctrl_id = ctrl_id or self.c_vending
        # add balance
        self.assertEqual(self.test_employee_id.hr_rfid_vending_balance, 0)
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.15)
        self.assertEqual(self.test_employee_id.hr_rfid_vending_balance, 0.15)
        self._check_history_records_count(1)
        # request balance
        self._check_balance(expected=3)  # Expected 3 units balance
        # self recharge
        self._sale_event(product=99, price_in_units=0, change_in_units=1, card_number=self.test_card_employee.number)
        self.assertEqual(self.test_employee_id.hr_rfid_vending_recharge_balance, 0.05)

        # Check balance for sum of self recharge + main balance. Expecting 4
        # request balance
        self._check_balance(expected=4)

        # remove balance

        # auto refill
        refill_id = self.env['hr.rfid.vending.auto.refill'].with_company(self.test_company_id)._auto_refill()
        self.assertEqual(0, len(refill_id), "Do not expect refill record")
        self.test_employee_id.hr_rfid_vending_auto_refill = True

        self.test_employee_id.hr_rfid_vending_refill_amount = 0.20

        self.test_employee_id.hr_rfid_vending_refill_type = 'fixed'
        refill_id = self.env['hr.rfid.vending.auto.refill'].with_company(self.test_company_id)._auto_refill()
        self.assertEqual(1, len(refill_id), "Expecting record")
        self.assertEqual(float_compare(refill_id.auto_refill_total, 0.05, precision_digits=2), 0)
        self.assertEqual(float_compare(self.test_employee_id.hr_rfid_vending_balance, 0.20, precision_digits=2), 0)

        self.test_employee_id.hr_rfid_vending_refill_type = 'up_to'
        self.test_employee_id.hr_rfid_vending_refill_max = 0.30
        refill_id = self.env['hr.rfid.vending.auto.refill'].with_company(self.test_company_id)._auto_refill()
        self.assertEqual(1, len(refill_id), "Expecting record")
        self.assertEqual(float_compare(refill_id.auto_refill_total, 0.10, precision_digits=2), 0)
        self.assertEqual(float_compare(self.test_employee_id.hr_rfid_vending_balance, 0.30, precision_digits=2), 0)
        self._check_no_commands()
        # Finishing with 0.3 balance and self balance 5. Let's spend it

    def _sale_event(self, product, price_in_units, change_in_units=0, card_number=None, ctrl_id=None):
        def h_x2(h):
            return f'0{h[0]}0{h[1]}'

        ctrl_id = ctrl_id or self.c_vending
        p = '{:02x}'.format(product)
        piu = h_x2('{:02x}'.format(price_in_units))
        ciu = h_x2('{:02x}'.format(change_in_units))
        response = self._send_cmd({
            "convertor": ctrl_id.webstack_id.serial,
            "event": {"bos": 1,
                      "tos": 1,
                      "card": card_number or self.test_card_employee.number,
                      "cmd": "FA",
                      "date": self.test_date_10_3,
                      "day": self.test_dow_10_3,
                      # "dt": "00 00 01 00 01 00 01",
                      # pass,pass, 72 hex product, price hex H, price hex L, result_credit hex H, result_credit hex L
                      "dt": f"0000{p}{piu}{ciu}",
                      "time": self.test_time_10_3,
                      "err": 0, "event_n": 47 if product != 99 else 50, "id": ctrl_id.ctrl_id, "reader": 1},
            "key": ctrl_id.webstack_id.key
        })
        self.assertEqual(response, {})

    def _sale_test(self, ctrl_id=None):
        ctrl_id = ctrl_id or self.c_vending
        # sale with card and product
        self._sale_event(product=1, price_in_units=1, change_in_units=0, card_number=self.test_card_employee.number)
        self._check_balance(6)

        # sale with card without product over balance
        self._sale_event(product=0, price_in_units=7, change_in_units=0, card_number=self.test_card_employee.number)
        self.assertEqual(
            float_compare(self.test_employee_id.hr_rfid_vending_recharge_balance, -0.05, precision_digits=2), 0)
        self.assertEqual(float_compare(self.test_employee_id.hr_rfid_vending_balance, 0, precision_digits=2), 0)
        self._check_balance(0)

        # Refill with get fill negative self balance. Add 4 units - 1 unit from negative self balance
        refill_id = self.env['hr.rfid.vending.auto.refill'].with_company(self.test_company_id)._auto_refill()
        self.assertEqual(1, len(refill_id), "Expecting record")
        self.assertEqual(float_compare(refill_id.auto_refill_total, 0.20, precision_digits=2), 0)
        self.assertEqual(float_compare(self.test_employee_id.hr_rfid_vending_balance, 0.15, precision_digits=2), 0)
        self.assertEqual(float_compare(self.test_employee_id.hr_rfid_vending_recharge_balance, 0, precision_digits=2),
                         0)
        self._check_balance(3)

        # sale with card without product over balance
        self._sale_event(product=2, price_in_units=2, change_in_units=0, card_number=self.test_card_employee.number)
        self.assertEqual(float_compare(self.test_employee_id.hr_rfid_vending_balance, 0.05, precision_digits=2), 0)

        # Refill with get fill negative self balance. Add 4 units - 1 unit from negative self balance
        refill_id = self.env['hr.rfid.vending.auto.refill'].with_company(self.test_company_id)._auto_refill()
        self.assertEqual(1, len(refill_id), "Expecting record")
        self.assertEqual(float_compare(refill_id.auto_refill_total, 0.20, precision_digits=2), 0)
        self.assertEqual(float_compare(self.test_employee_id.hr_rfid_vending_balance, 0.25, precision_digits=2), 0)
        self.assertEqual(
            float_compare(self.test_employee_id.hr_rfid_vending_recharge_balance, 0, precision_digits=2),
            0
        )
        self._check_balance(5)

        # sale without card and without product
        self._sale_event(product=0, price_in_units=1, change_in_units=0, card_number='0000000000')
        self.assertEqual(ctrl_id.cash_contained, 0.05)

        self._check_no_commands()

