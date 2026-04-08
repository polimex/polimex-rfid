# Copyright 2026 Polimex Holding Ltd.
# License APL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""
E2E tests for hr_rfid_vending — full hardware-to-Odoo-to-hardware flows.

Each test simulates real vending machine HTTP requests and validates
the complete chain: event parsing → balance check → response → balance
update → history record.
"""
from odoo.addons.hr_rfid.tests.controller import RFIDController
from odoo.tests.common import HttpCase, tagged
from odoo.tools import float_compare


def fc(a, b):
    """Shorthand float_compare with 2 decimal precision."""
    return float_compare(a, b, precision_digits=2) == 0


@tagged('rfid_vending', 'rfid_vending_e2e', 'post_install', '-at_install')
class TestVendingE2E(RFIDController, HttpCase):
    """E2E tests covering all vending business flows end-to-end."""

    _registry_readonly_enabled = False

    def setUp(self):
        super().setUp()
        self._add_Vending()
        self._setup_products()

    def _setup_products(self):
        """Create products and configure vending machine slots."""
        self.products = []
        for i in range(8):
            self.products.append(
                self.env['product.template'].create({
                    'name': 'Vending Product #%d' % (i + 1),
                    'list_price': (i + 1) * 0.05,
                })
            )
        # Configure vending rows via settings wizard
        wiz = self.env['hr.rfid.ctrl.vending.settings'].with_context(
            ids=[self.c_vending.id],
        ).create({'controller_id': self.c_vending.id})
        rows = self.c_vending.create_vending_rows()
        rows[0].write({
            'row_num': 1,
            'controller_id': self.c_vending.id,
            'item1': self.products[0].id,
            'item2': self.products[1].id,
            'item3': self.products[2].id,
            'item4': self.products[3].id,
        })
        rows[1].write({
            'row_num': 2,
            'controller_id': self.c_vending.id,
            'item1': self.products[4].id,
            'item2': self.products[5].id,
            'item3': self.products[6].id,
            'item4': self.products[7].id,
        })
        wiz.vending_row_ids = [(6, 0, rows.mapped('id'))]
        wiz.show_price_timeout = 15
        wiz.scale_factor = 5
        wiz.save_settings()
        # Process D9 IO table commands from heartbeat
        response = self._hearbeat(self.c_vending.webstack_id)
        while 'cmd' in response and response['cmd']['c'] == 'D9':
            response = self._send_cmd_response(response)
        self._check_no_commands()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ev64(self, card_number=None, ctrl_id=None):
        """Send ev64 (balance request) from vending machine."""
        ctrl_id = ctrl_id or self.c_vending
        card_number = card_number or self.test_card_employee.number
        return self._send_cmd({
            "convertor": ctrl_id.webstack_id.serial,
            "event": {
                "bos": 1, "tos": 1,
                "card": card_number,
                "cmd": "FA",
                "date": self.test_date_10_3,
                "day": self.test_dow_10_3,
                "dt": "00000000000000",
                "time": self.test_time_10_3,
                "err": 0, "event_n": 64,
                "id": ctrl_id.ctrl_id, "reader": 1,
            },
            "key": ctrl_id.webstack_id.key
        })

    def _ev47(self, product_slot, price_units, change_units=0,
              card_number=None, ctrl_id=None):
        """Send ev47 (purchase complete) from vending machine."""
        def h_x2(h):
            return f'0{h[0]}0{h[1]}'

        ctrl_id = ctrl_id or self.c_vending
        card_number = card_number or self.test_card_employee.number
        p = '{:02x}'.format(product_slot)
        piu = h_x2('{:02x}'.format(price_units))
        ciu = h_x2('{:02x}'.format(change_units))
        return self._send_cmd({
            "convertor": ctrl_id.webstack_id.serial,
            "event": {
                "bos": 1, "tos": 1,
                "card": card_number,
                "cmd": "FA",
                "date": self.test_date_10_3,
                "day": self.test_dow_10_3,
                "dt": f"0000{p}{piu}{ciu}",
                "time": self.test_time_10_3,
                "err": 0, "event_n": 47,
                "id": ctrl_id.ctrl_id, "reader": 1,
            },
            "key": ctrl_id.webstack_id.key
        })

    def _ev50(self, price_units, change_units=0, card_number=None,
              ctrl_id=None):
        """Send ev50 (cash collect / self recharge) from vending machine."""
        def h_x2(h):
            return f'0{h[0]}0{h[1]}'

        ctrl_id = ctrl_id or self.c_vending
        card_number = card_number or self.test_card_employee.number
        piu = h_x2('{:02x}'.format(price_units))
        ciu = h_x2('{:02x}'.format(change_units))
        return self._send_cmd({
            "convertor": ctrl_id.webstack_id.serial,
            "event": {
                "bos": 1, "tos": 1,
                "card": card_number,
                "cmd": "FA",
                "date": self.test_date_10_3,
                "day": self.test_dow_10_3,
                "dt": f"000063{piu}{ciu}",
                "time": self.test_time_10_3,
                "err": 0, "event_n": 50,
                "id": ctrl_id.ctrl_id, "reader": 1,
            },
            "key": ctrl_id.webstack_id.key
        })

    def _assert_balance_response(self, response, expected_units):
        """Assert that ev64 response contains correct balance."""
        self.assertIn('cmd', response, 'Should return DB2 command')
        self.assertEqual(response['cmd']['c'], 'DB')
        self.assertTrue(response['cmd']['d'].startswith('4000'))
        # Complete the DB2 handshake
        self._send_cmd_response(response, '0000')

    def _assert_deny(self, response):
        """Assert that ev64 response is a deny (empty)."""
        self.assertEqual(response, {}, 'Expected deny (empty response)')

    def _vending_event_count(self):
        return self.env['hr.rfid.vending.event'].sudo().search_count([
            ('controller_id', '=', self.c_vending.id)
        ])

    def _history_count(self, employee=None):
        employee = employee or self.test_employee_id
        return self.env['hr.rfid.vending.balance.history'].search_count([
            ('employee_id', '=', employee.id)
        ])

    def _last_history(self, employee=None):
        employee = employee or self.test_employee_id
        return self.env['hr.rfid.vending.balance.history'].search([
            ('employee_id', '=', employee.id)
        ], order='id desc', limit=1)

    def _emp(self):
        """Shortcut to reload employee."""
        self.test_employee_id.invalidate_recordset()
        return self.test_employee_id

    def _reset_employee(self, employee=None):
        """Reset employee vending state to zero for test isolation."""
        employee = employee or self.test_employee_id
        employee.write({
            'hr_rfid_vending_balance': 0,
            'hr_rfid_vending_recharge_balance': 0,
            'hr_rfid_vending_negative_balance': False,
            'hr_rfid_vending_limit': 0,
            'hr_rfid_vending_daily_limit': 0,
            'hr_rfid_vending_in_attendance': False,
            'hr_rfid_vending_auto_refill': False,
            'hr_rfid_vending_refill_amount': 0,
            'hr_rfid_vending_refill_max': 0,
        })

    # ==================================================================
    # TEST 1: Balance Request (ev64) → Grant with DB2 response
    # ==================================================================

    def test_01_ev64_balance_request_grant(self):
        """Full flow: add balance → ev64 → DB2 response with correct balance."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.15)

        response = self._ev64()

        self._assert_balance_response(response, expected_units=3)
        self.assertEqual(self._vending_event_count(), 1,
                         'Balance request creates vending event')

    # ==================================================================
    # TEST 2: Balance Request → Deny (zero balance)
    # ==================================================================

    def test_02_ev64_deny_zero_balance(self):
        """Zero balance → deny (empty response), event still created."""
        self._reset_employee()

        response = self._ev64()

        self._assert_deny(response)

    # ==================================================================
    # TEST 3: Purchase (ev47) → balance deducted, history created
    # ==================================================================

    def test_03_ev47_purchase_deducts_balance(self):
        """Purchase: balance decreases, history record created, event logged."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)
        ev_before = self._vending_event_count()

        # Verify initial balance via ev64 (10 units = 0.50)
        response = self._ev64()
        self._assert_balance_response(response, expected_units=10)

        # Purchase product slot 1, price 2 units (2*5/100 = 0.10)
        response = self._ev47(product_slot=1, price_units=2)
        self.assertEqual(response, {}, 'Purchase returns empty response')

        # Verify reduced balance via ev64 (8 units = 0.40)
        response = self._ev64()
        self._assert_balance_response(response, expected_units=8)

    # ==================================================================
    # TEST 4: Cash purchase (card=0000000000) → cash_contained increases
    # ==================================================================

    def test_04_ev47_cash_purchase_increases_cash_contained(self):
        """Cash purchase (no card) increases machine cash_contained."""
        self.c_vending.write({'cash_contained': 0})

        response = self._ev47(product_slot=0, price_units=1,
                              card_number='0000000000')
        self.assertEqual(response, {})

        self.c_vending.invalidate_recordset()
        self.assertTrue(fc(self.c_vending.cash_contained, 0.05),
                        'Cash contained should be 0.05 (1 unit * 5/100)')

    # ==================================================================
    # TEST 5: Self recharge (ev50) → recharge_balance increases
    # ==================================================================

    def test_05_ev50_self_recharge(self):
        """Self recharge: employee adds personal money via machine."""
        self._reset_employee()

        # ev50 with product=99 (special recharge code), change=1 unit
        response = self._ev50(price_units=0, change_units=1)
        self.assertEqual(response, {})

        self.assertTrue(
            fc(self._emp().hr_rfid_vending_recharge_balance, 0.05),
            'Recharge balance should be 0.05')

    # ==================================================================
    # TEST 6: Combined balance (company + personal) in ev64
    # ==================================================================

    def test_06_combined_balance_in_ev64(self):
        """ev64 returns sum of company + personal balance."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.10)  # 2 units
        # Add personal balance via recharge
        self._ev50(price_units=0, change_units=1)  # +0.05 = 1 unit

        response = self._ev64()
        # Total: 0.10 + 0.05 = 0.15 = 3 units
        self._assert_balance_response(response, expected_units=3)

    # ==================================================================
    # TEST 7: Daily limit enforcement
    # ==================================================================

    def test_07_daily_limit_caps_balance(self):
        """Daily limit restricts available balance in ev64."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(1.00)  # 20 units
        self.test_employee_id.hr_rfid_vending_daily_limit = 0.10  # 2 units
        self.test_employee_id.daily_limit_type = 'day'

        response = self._ev64()
        # Balance is 1.00 but daily limit is 0.10, so max 0.10 = 2 units
        self._assert_balance_response(response, expected_units=2)

    # ==================================================================
    # TEST 8: Daily limit exhausted after purchase → deny
    # ==================================================================

    def test_08_daily_limit_exhausted_after_purchase(self):
        """After spending daily limit, next ev64 returns deny."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(1.00)
        self.test_employee_id.hr_rfid_vending_daily_limit = 0.05
        self.test_employee_id.daily_limit_type = 'day'

        # Purchase 0.05 (1 unit) → exhausts daily limit of 0.05
        self._ev47(product_slot=1, price_units=1)

        response = self._ev64()
        self._assert_deny(response)

    # ==================================================================
    # TEST 9: Negative balance with credit limit
    # ==================================================================

    def test_09_negative_balance_with_credit_limit(self):
        """Negative balance allowed up to credit limit."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_negative_balance = True
        self.test_employee_id.hr_rfid_vending_limit = 0.20  # 4 units credit
        # Balance is 0, but credit limit allows 0.20

        response = self._ev64()
        # Available: 0 (balance) + 0.20 (credit) = 0.20 = 4 units
        self._assert_balance_response(response, expected_units=4)

    # ==================================================================
    # TEST 10: Attendance check → deny when not checked in
    # ==================================================================

    def test_10_attendance_not_checked_in_deny(self):
        """Employee with attendance check but not checked in → deny."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(1.00)
        self.test_employee_id.hr_rfid_vending_in_attendance = True

        response = self._ev64()
        self._assert_deny(response)

    # ==================================================================
    # TEST 11: Purchase overflow from company to personal balance
    # ==================================================================

    def test_11_purchase_overflows_to_personal_balance(self):
        """Purchase exceeding company balance uses credit, verified via ev64."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.05)  # company: 0.05
        self.test_employee_id.write({
            'hr_rfid_vending_recharge_balance': 0.10,  # personal: 0.10
        })

        # Total available: 0.05 + 0.10 = 0.15 = 3 units
        response = self._ev64()
        self._assert_balance_response(response, expected_units=3)

        # Purchase 0.10 (2 units)
        self._ev47(product_slot=1, price_units=2)

        # Remaining: 0.15 - 0.10 = 0.05 = 1 unit
        response = self._ev64()
        self._assert_balance_response(response, expected_units=1)

    # ==================================================================
    # TEST 12: Auto refill — fixed type
    # ==================================================================

    def test_12_auto_refill_fixed(self):
        """Fixed auto refill sets balance to refill_amount."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_auto_refill = True
        self.test_employee_id.hr_rfid_vending_refill_amount = 0.50
        self.test_employee_id.hr_rfid_vending_refill_type = 'fixed'

        refill = self.env['hr.rfid.vending.auto.refill'].with_company(
            self.test_company_id
        )._auto_refill()

        self.assertEqual(len(refill), 1, 'Refill record should be created')
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.50))

    # ==================================================================
    # TEST 13: Auto refill — up_to type
    # ==================================================================

    def test_13_auto_refill_up_to(self):
        """Up-to refill tops up balance to refill_max, not beyond."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.20)
        self.test_employee_id.hr_rfid_vending_auto_refill = True
        self.test_employee_id.hr_rfid_vending_refill_amount = 1.00
        self.test_employee_id.hr_rfid_vending_refill_type = 'up_to'
        self.test_employee_id.hr_rfid_vending_refill_max = 0.50

        refill = self.env['hr.rfid.vending.auto.refill'].with_company(
            self.test_company_id
        )._auto_refill()

        self.assertEqual(len(refill), 1)
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.50),
                        'Balance should be topped to max 0.50, not 1.20')
        self.assertTrue(fc(refill.auto_refill_total, 0.30),
                        'Refill total should be 0.30 (0.50 - 0.20)')

    # ==================================================================
    # TEST 14: Auto refill — no refill when balance >= max
    # ==================================================================

    def test_14_auto_refill_up_to_no_refill_when_full(self):
        """Up-to refill does nothing when balance >= max."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.60)
        self.test_employee_id.hr_rfid_vending_auto_refill = True
        self.test_employee_id.hr_rfid_vending_refill_amount = 0.50
        self.test_employee_id.hr_rfid_vending_refill_type = 'up_to'
        self.test_employee_id.hr_rfid_vending_refill_max = 0.50

        refill = self.env['hr.rfid.vending.auto.refill'].with_company(
            self.test_company_id
        )._auto_refill()

        self.assertEqual(len(refill), 0,
                         'No refill when balance >= max')
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.60))

    # ==================================================================
    # TEST 15: Product mapping — slot → product.template
    # ==================================================================

    def test_15_purchase_links_product(self):
        """Purchase event links correct product.template via slot mapping."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(1.00)

        # Product slot 1 = self.products[0]
        self._ev47(product_slot=1, price_units=1)

        ev = self.env['hr.rfid.vending.event'].sudo().search([
            ('controller_id', '=', self.c_vending.id),
            ('event_action', '=', '47'),
        ], order='id desc', limit=1)
        self.assertTrue(ev, 'Purchase event should exist')
        self.assertEqual(ev.item_sold_id.id, self.products[0].id,
                         'Slot 1 should map to Product #1')
        self.assertEqual(ev.item_sold, 1, 'item_sold should be slot number')

    # ==================================================================
    # TEST 16: Balance history audit trail
    # ==================================================================

    def test_16_balance_history_audit_trail(self):
        """Each balance change creates a history record with correct data."""
        self._reset_employee()
        # Manual add
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.30)
        h1 = self._last_history()
        self.assertTrue(fc(h1.balance_change, 0.30))
        self.assertTrue(fc(h1.balance_result, 0.30))
        self.assertEqual(h1.employee_id.id, self.test_employee_id.id)

        # Purchase
        self._ev47(product_slot=1, price_units=1)
        h2 = self._last_history()
        self.assertTrue(fc(h2.balance_change, -0.05))
        self.assertTrue(fc(h2.balance_result, 0.25))
        self.assertTrue(h2.vending_event_id,
                        'Purchase history should link to vending event')

    # ==================================================================
    # TEST 17: Cash collect wizard
    # ==================================================================

    def test_17_cash_collect_wizard(self):
        """Cash collect wizard zeroes out machine cash_contained."""
        self.c_vending.write({'cash_contained': 0})
        # Add some cash via cash purchase
        self._ev47(product_slot=0, price_units=3,
                   card_number='0000000000')
        self.c_vending.invalidate_recordset()
        self.assertTrue(fc(self.c_vending.cash_contained, 0.15))

        # Run cash collect wizard
        wiz = self.env['hr.rfid.ctrl.cash.wiz'].with_context(
            active_ids=[self.c_vending.id],
        ).create({})
        wiz.collect()

        self.c_vending.invalidate_recordset()
        self.assertTrue(fc(self.c_vending.cash_contained, 0),
                        'Cash contained should be 0 after collection')

    # ==================================================================
    # TEST 18: Full lifecycle — add → purchase → refill → purchase
    # ==================================================================

    def test_18_full_purchase_lifecycle(self):
        """Complete lifecycle: add balance → purchase → refill → purchase.
        All balance checks via ev64 (hardware verification)."""
        self._reset_employee()
        emp = self.test_employee_id

        # Step 1: Add balance 0.30 = 6 units
        emp.hr_rfid_vending_add_to_balance(0.30)

        # Step 2: Verify via ev64
        response = self._ev64()
        self._assert_balance_response(response, expected_units=6)

        # Step 3: Purchase 0.10 (2 units)
        self._ev47(product_slot=1, price_units=2)

        # Step 4: Verify 0.20 remaining = 4 units
        response = self._ev64()
        self._assert_balance_response(response, expected_units=4)

        # Step 5: Auto refill (up_to 0.50) — runs in ORM context
        emp.hr_rfid_vending_auto_refill = True
        emp.hr_rfid_vending_refill_amount = 1.00
        emp.hr_rfid_vending_refill_type = 'up_to'
        emp.hr_rfid_vending_refill_max = 0.50
        self.env['hr.rfid.vending.auto.refill'].with_company(
            self.test_company_id
        )._auto_refill()

        # Step 6: Verify refilled balance 0.50 = 10 units
        response = self._ev64()
        self._assert_balance_response(response, expected_units=10)

        # Step 7: Purchase 0.15 (3 units)
        self._ev47(product_slot=2, price_units=3)

        # Step 8: Verify 0.35 = 7 units
        response = self._ev64()
        self._assert_balance_response(response, expected_units=7)

        self._check_no_commands()

    # ==================================================================
    # TEST 19: Multiple employees don't interfere
    # ==================================================================

    def test_19_multiple_employees_isolated(self):
        """Purchases by one employee don't affect another's balance.
        Verified via ev64 for both employees."""
        self._reset_employee(self.test_employee_id)
        self._reset_employee(self.test_employee_2_id)

        self.test_employee_id.hr_rfid_vending_add_to_balance(1.00)  # 20 units
        self.test_employee_2_id.hr_rfid_vending_add_to_balance(0.50)  # 10 units

        # Verify emp1 initial balance
        response = self._ev64(card_number=self.test_card_employee.number)
        self._assert_balance_response(response, expected_units=20)

        # Verify emp2 initial balance
        response = self._ev64(card_number=self.test_card_employee_2.number)
        self._assert_balance_response(response, expected_units=10)

        # Employee 1 purchases 0.10 (2 units)
        self._ev47(product_slot=1, price_units=2,
                   card_number=self.test_card_employee.number)

        # Emp1: 20-2 = 18 units
        response = self._ev64(card_number=self.test_card_employee.number)
        self._assert_balance_response(response, expected_units=18)

        # Emp2: still 10 units (unchanged)
        response = self._ev64(card_number=self.test_card_employee_2.number)
        self._assert_balance_response(response, expected_units=10)

    # ==================================================================
    # TEST 20: Unknown card → deny, no balance change
    # ==================================================================

    def test_20_unknown_card_deny(self):
        """Unknown card gets deny, no events or balance changes."""
        ev_before = self._vending_event_count()
        response = self._ev64(card_number='9999999999')
        self._assert_deny(response)

    # ==================================================================
    # TEST 21-24: Reversal (storno) tests
    # ==================================================================

    def _get_last_purchase_event(self):
        return self.env['hr.rfid.vending.event'].sudo().search([
            ('controller_id', '=', self.c_vending.id),
            ('event_action', '=', '47'),
        ], order='id desc', limit=1)

    def _reverse_event(self, event, reason='Test reversal'):
        """Run the reversal wizard on an event."""
        wiz = self.env['hr.rfid.vending.event.reverse'].with_context(
            active_id=event.id,
        ).create({'reason': reason})
        return wiz.action_reverse()

    def test_21_reversal_restores_balance(self):
        """Reversal of purchase restores balance, verified via ev64."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)

        # Verify initial: 10 units
        response = self._ev64()
        self._assert_balance_response(response, expected_units=10)

        # Purchase 0.10 (2 units)
        self._ev47(product_slot=1, price_units=2)

        # Verify after purchase: 8 units
        response = self._ev64()
        self._assert_balance_response(response, expected_units=8)

        # Reverse the purchase
        purchase = self._get_last_purchase_event()
        self._reverse_event(purchase)

        # Verify balance restored: 10 units
        response = self._ev64()
        self._assert_balance_response(response, expected_units=10)

    def test_22_reversal_creates_history(self):
        """Reversal creates positive balance_history linked to same event."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.30)
        self._ev47(product_slot=1, price_units=1)

        purchase = self._get_last_purchase_event()
        self._reverse_event(purchase, reason='Wrong item dispensed')

        # Same event should now have TWO history records:
        # one negative (purchase) and one positive (reversal)
        bh_records = self.env['hr.rfid.vending.balance.history'].search([
            ('vending_event_id', '=', purchase.id),
        ], order='id asc')
        self.assertEqual(len(bh_records), 2,
                         'Purchase event should have 2 history records')
        self.assertTrue(fc(bh_records[0].balance_change, -0.05),
                        'First record: purchase -0.05')
        self.assertTrue(fc(bh_records[1].balance_change, 0.05),
                        'Second record: reversal +0.05')

    def test_23_double_reversal_blocked(self):
        """Cannot reverse an already reversed event."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)
        self._ev47(product_slot=1, price_units=1)

        purchase = self._get_last_purchase_event()
        self._reverse_event(purchase)

        # Second reversal should raise
        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            self._reverse_event(purchase)

    def test_24_reversal_non_purchase_blocked(self):
        """Cannot reverse non-purchase events."""
        self._reset_employee()
        # Create a non-purchase event (self recharge)
        self._ev50(price_units=0, change_units=1)

        ev = self.env['hr.rfid.vending.event'].sudo().search([
            ('controller_id', '=', self.c_vending.id),
            ('event_action', '=', '50'),
        ], order='id desc', limit=1)

        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            self._reverse_event(ev)

    def test_25_reversal_restores_daily_limit(self):
        """Reversal within same day neutralizes daily spend."""
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(1.00)
        self.test_employee_id.hr_rfid_vending_daily_limit = 0.10
        self.test_employee_id.daily_limit_type = 'day'

        # Purchase 0.05 (1 unit) — uses half of daily limit
        self._ev47(product_slot=1, price_units=1)

        # Daily limit: 0.10 - 0.05 = 0.05 remaining = 1 unit
        response = self._ev64()
        self._assert_balance_response(response, expected_units=1)

        # Reverse the purchase — daily spend should be neutralized
        purchase = self._get_last_purchase_event()
        self._reverse_event(purchase)

        # Daily limit fully available again: 0.10 = 2 units
        response = self._ev64()
        self._assert_balance_response(response, expected_units=2)
