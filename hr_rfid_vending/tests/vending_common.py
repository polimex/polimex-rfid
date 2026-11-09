# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""What a vending machine sends and how a test reads the answer.

Mixed into an `RFIDController` + `HttpCase` test with `self.c_vending` set.
"""

from odoo.tools import float_compare


def fc(a, b):
    """Shorthand float_compare with 2 decimal precision."""
    return float_compare(a, b, precision_digits=2) == 0


def units_hex(units):
    """An amount in machine units the way the machine writes it: two hex
    digits, one per byte ('0A' -> '000A')."""
    digits = f"{units:02x}"
    return "0%s0%s" % (digits[0], digits[1])


def take_everyone_off_auto_refill(env):
    """A database with the module's demo has employees on auto refill. The
    refill job tops them up too, so every count a refill test makes would
    include them; a refill test starts with nobody on auto refill."""
    env["hr.employee"].sudo().with_context(active_test=False).search(
        [("hr_rfid_vending_auto_refill", "=", True)]
    ).write({"hr_rfid_vending_auto_refill": False})


class VendingFlowMixin:
    """Products in the price table, machine events and balance checks."""

    def _setup_products(self):
        """Create products and configure vending machine slots."""
        self.products = []
        for i in range(8):
            self.products.append(
                self.env["product.template"].create(
                    {
                        "name": "Vending Product #%d" % (i + 1),
                        "list_price": (i + 1) * 0.05,
                    }
                )
            )
        # Configure vending rows via settings wizard
        wiz = (
            self.env["hr.rfid.ctrl.vending.settings"]
            .with_context(
                ids=[self.c_vending.id],
            )
            .create({"controller_id": self.c_vending.id})
        )
        rows = self.c_vending.create_vending_rows()
        rows[0].write(
            {
                "row_num": 1,
                "controller_id": self.c_vending.id,
                "item1": self.products[0].id,
                "item2": self.products[1].id,
                "item3": self.products[2].id,
                "item4": self.products[3].id,
            }
        )
        rows[1].write(
            {
                "row_num": 2,
                "controller_id": self.c_vending.id,
                "item1": self.products[4].id,
                "item2": self.products[5].id,
                "item3": self.products[6].id,
                "item4": self.products[7].id,
            }
        )
        wiz.vending_row_ids = [(6, 0, rows.mapped("id"))]
        wiz.show_price_timeout = 15
        wiz.scale_factor = 5
        wiz.save_settings()
        # Process D9 IO table commands from heartbeat
        response = self._hearbeat(self.c_vending.webstack_id)
        while "cmd" in response and response["cmd"]["c"] == "D9":
            response = self._send_cmd_response(response)
        self._check_no_commands()

    # ------------------------------------------------------------------
    # What the machine sends
    # ------------------------------------------------------------------

    def _vending_event(
        self,
        event_n,
        dt="00000000000000",
        card_number=None,
        ctrl_id=None,
        bos=1,
        tos=1,
        key=None,
        system_event=False,
    ):
        """Send one machine event (FA) the way the controller posts it."""
        ctrl_id = ctrl_id or self.c_vending
        return self._send_cmd(
            {
                "convertor": ctrl_id.webstack_id.serial,
                "event": {
                    "bos": bos,
                    "tos": tos,
                    "card": card_number or self.test_card_employee.number,
                    "cmd": "FA",
                    "date": self.test_date_10_3,
                    "day": self.test_dow_10_3,
                    "dt": dt,
                    "time": self.test_time_10_3,
                    "err": 0,
                    "event_n": event_n,
                    "id": ctrl_id.ctrl_id,
                    "reader": 1,
                },
                "key": ctrl_id.webstack_id.key if key is None else key,
            },
            system_event=system_event,
        )

    def _ev64(self, card_number=None, ctrl_id=None, bos=1, tos=1, key=None):
        """Balance request."""
        return self._vending_event(
            64, card_number=card_number, ctrl_id=ctrl_id, bos=bos, tos=tos, key=key
        )

    def _ev47(
        self, product_slot, price_units, change_units=0, card_number=None, ctrl_id=None
    ):
        """Purchase complete: slot, price and change (or credit left) in units."""
        dt = "0000%02x%s%s" % (
            product_slot,
            units_hex(price_units),
            units_hex(change_units),
        )
        return self._vending_event(47, dt, card_number=card_number, ctrl_id=ctrl_id)

    def _ev49(self, card_number=None, ctrl_id=None):
        """Vend failed."""
        return self._vending_event(
            49, card_number=card_number, ctrl_id=ctrl_id, system_event=True
        )

    def _ev50(self, price_units, change_units=0, card_number=None, ctrl_id=None):
        """Cash collected onto the card (self recharge, item 99)."""
        dt = "000063%s%s" % (units_hex(price_units), units_hex(change_units))
        return self._vending_event(50, dt, card_number=card_number, ctrl_id=ctrl_id)

    # ------------------------------------------------------------------
    # How a test reads the answer
    # ------------------------------------------------------------------

    def _assert_balance_response(self, response, expected_units):
        """The machine is given exactly `expected_units` of credit (DB2)."""
        self.assertIn("cmd", response, "Should return DB2 command")
        self.assertEqual(response["cmd"]["c"], "DB")
        data = response["cmd"]["d"]
        self.assertTrue(data.startswith("4000"))
        sent = int(data[-4:-2], 16) * 0x10 + int(data[-2:], 16)
        self.assertEqual(sent, expected_units, "credit sent to the machine")
        # Complete the DB2 handshake
        self._send_cmd_response(response, "0000")

    def _assert_deny(self, response):
        """Assert that ev64 response is a deny (empty)."""
        self.assertEqual(response, {}, "Expected deny (empty response)")

    def _vending_event_count(self, ctrl_id=None):
        return (
            self.env["hr.rfid.vending.event"]
            .sudo()
            .search_count([("controller_id", "=", (ctrl_id or self.c_vending).id)])
        )

    def _system_events(self, event_action=None, ctrl_id=None):
        domain = [("controller_id", "=", (ctrl_id or self.c_vending).id)]
        if event_action:
            domain.append(("event_action", "=", event_action))
        return self.env["hr.rfid.event.system"].sudo().search(domain)

    def _history_count(self, employee=None):
        employee = employee or self.test_employee_id
        return self.env["hr.rfid.vending.balance.history"].search_count(
            [("employee_id", "=", employee.id)]
        )

    def _last_history(self, employee=None):
        employee = employee or self.test_employee_id
        return self.env["hr.rfid.vending.balance.history"].search(
            [("employee_id", "=", employee.id)], order="id desc", limit=1
        )

    def _emp(self):
        """Shortcut to reload employee."""
        self.test_employee_id.invalidate_recordset()
        return self.test_employee_id

    def _reset_employee(self, employee=None):
        """Reset employee vending state to zero for test isolation."""
        employee = employee or self.test_employee_id
        employee.write(
            {
                "hr_rfid_vending_balance": 0,
                "hr_rfid_vending_recharge_balance": 0,
                "hr_rfid_vending_negative_balance": False,
                "hr_rfid_vending_limit": 0,
                "hr_rfid_vending_daily_limit": 0,
                "hr_rfid_vending_in_attendance": False,
                "hr_rfid_vending_auto_refill": False,
                "hr_rfid_vending_refill_amount": 0,
                "hr_rfid_vending_refill_max": 0,
            }
        )
