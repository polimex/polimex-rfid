# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""A sale is charged once, however often the machine's module reports it.

A module that does not get the answer to a report sends the report again: the
answer was lost on the way, the sale itself was not. Over the real-time
connection a repeated report was already recognised. Over the classic
connection it was not, so the buyer paid twice for one item, and money put on
a card was added twice. The owner's decision (27.11.2026): the classic
connection recognises a repeated report of money too.

What tells a report from its repeat is where the event sits in the
controller's memory and the controller's own time of it. Two sales never share
both; a repeat always does.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.models.hr_rfid_webstack_ws import WS_PROTO_VERSION
from odoo.addons.hr_rfid.tests.controller import RFIDController

from .vending_common import VendingFlowMixin, fc, take_everyone_off_auto_refill

UNKNOWN_CARD = "0099999999"


@tagged("rfid_vending", "rfid_vending_once", "post_install", "-at_install")
class TestAMoneyReportIsBookedOnce(VendingFlowMixin, RFIDController, HttpCase):
    _registry_readonly_enabled = False

    def setUp(self):
        super().setUp()
        take_everyone_off_auto_refill(self.env)
        self._add_Vending()
        self._setup_products()
        self._reset_employee()
        self.env["ir.config_parameter"].sudo().set_param("hr_rfid.ws_fw_secret", "")
        self.module = self.c_vending.webstack_id

    # ------------------------------------------------------------------
    # The two ways a report travels
    # ------------------------------------------------------------------

    def _over_the_classic_connection(self, report):
        return self._send_cmd(
            {
                "convertor": self.module.serial,
                "event": report,
                "key": self.module.key,
            }
        )

    def _over_real_time(self, report, batch=1):
        message = {
            "v": WS_PROTO_VERSION,
            "s": self.module.serial,
            "k": self.module.sudo().key,
            "t": "ev",
            "bid": batch,
            "ev": [report],
        }
        with patch.object(type(self.env["bus.bus"]), "_sendone") as sendone:
            self.env["ir.websocket"]._serve_ir_websocket("hr_rfid", message)
        return [
            call.args[2]
            for call in sendone.call_args_list
            if call.args[1] == "hr_rfid.ev_ack"
        ][0]

    def _a_sale(self, place=7):
        """The item in slot two, ten cents, reported from this place in the memory."""
        return self._machine_report(
            47, self._sale_dt(product_slot=2, price_units=2), bos=place, tos=place
        )

    def _sales_on_record(self):
        return self.env["hr.rfid.vending.event"].search_count(
            [("controller_id", "=", self.c_vending.id), ("event_action", "=", "47")]
        )

    def _ten_seconds_later(self, report):
        clock = datetime.strptime(report["time"], "%H:%M:%S") + timedelta(seconds=10)
        return dict(report, time=clock.strftime("%H:%M:%S"))

    # ------------------------------------------------------------------
    # A repeat
    # ------------------------------------------------------------------

    def test_a_sale_reported_twice_is_charged_once(self):
        """Half a euro of credit, one item of ten cents, reported twice: forty cents are left."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)
        report = self._a_sale()

        self._over_the_classic_connection(report)
        self._over_the_classic_connection(report)

        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.40))
        self.assertEqual(self._sales_on_record(), 1)

    def test_a_cash_sale_reported_twice_is_in_the_machines_cash_once(self):
        """No card, one unit in coins, reported twice: five cents more in the machine."""
        self.c_vending.write({"cash_contained": 0})
        report = self._machine_report(
            47,
            self._sale_dt(product_slot=0, price_units=1),
            card_number="0000000000",
            bos=9,
            tos=9,
        )

        self._over_the_classic_connection(report)
        self._over_the_classic_connection(report)

        self.c_vending.invalidate_recordset()
        self.assertTrue(fc(self.c_vending.cash_contained, 0.05))

    def test_money_put_on_a_card_reported_twice_is_added_once(self):
        """One unit of five cents put on the card at the machine, reported twice."""
        report = self._machine_report(50, "000063" + "0000" + "0001", bos=5, tos=5)

        self._over_the_classic_connection(report)
        self._over_the_classic_connection(report)

        self.assertTrue(fc(self._emp().hr_rfid_vending_recharge_balance, 0.05))

    def test_a_sale_repeated_over_the_other_connection_is_one_sale(self):
        """The module lost its real-time connection after the sale went out
        and reports it again the classic way - and the other way round."""
        self.module.action_ws_enable()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)
        first, second = self._a_sale(place=7), self._a_sale(place=8)
        charges = self._history_count()

        self._over_real_time(first, batch=1)
        self._over_the_classic_connection(first)
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.40))

        self._over_the_classic_connection(second)
        told = self._over_real_time(second, batch=2)
        self.assertEqual(told["res"], [{"i": 0, "ok": True, "dup": True}])
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.30))
        self.assertEqual(self._history_count(), charges + 2)

    # ------------------------------------------------------------------
    # NEGATIVE: what is not a repeat
    # ------------------------------------------------------------------

    def test_two_sales_in_one_second_are_two_sales(self):
        """Two items bought within a second sit in two places of the memory."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)

        charges = self._history_count()

        self._over_the_classic_connection(self._a_sale(place=7))
        self._over_the_classic_connection(self._a_sale(place=8))

        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.30))
        self.assertEqual(self._history_count(), charges + 2)

    def test_the_same_place_at_another_time_is_another_sale(self):
        """The memory is a ring: a place is used again, at another time."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)
        report = self._a_sale()

        self._over_the_classic_connection(report)
        self._over_the_classic_connection(self._ten_seconds_later(report))

        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.30))
        self.assertEqual(self._sales_on_record(), 2)

    def test_a_sale_that_was_not_booked_is_booked_when_it_is_reported_again(self):
        """A card nobody knows yet: the sale is not booked. Once the card is
        given to somebody, the same report is booked - it was never held as
        already reported."""
        report = dict(self._a_sale(place=11), card=UNKNOWN_CARD)
        self._over_the_classic_connection(report)
        self.assertEqual(self._sales_on_record(), 0)
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)
        self.test_card_employee.with_context(no_hardware_commands=True).number = (
            UNKNOWN_CARD
        )

        self._over_the_classic_connection(report)

        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.40))
        self.assertEqual(self._sales_on_record(), 1)

    def test_a_report_that_failed_here_is_booked_when_it_comes_again(self):
        """The first report of a sale ends in an error on our side, so the
        module keeps it and sends it again: the buyer is charged exactly once,
        not zero times because the first try left its mark behind."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)
        report = self._a_sale(place=12)
        Module = type(self.module)
        booking = Module._hw_vending_sale
        tries = []

        def failing_once(module, controller, post_data):
            tries.append(1)
            if len(tries) == 1:
                raise RuntimeError("the first try fails")
            return booking(module, controller, post_data)

        with patch.object(Module, "_hw_vending_sale", failing_once):
            with self.assertLogs("odoo.addons.hr_rfid.controllers.main", "ERROR"):
                self.url_open(
                    self.app_url,
                    data=json.dumps(
                        {
                            "convertor": self.module.serial,
                            "event": report,
                            "key": self.module.key,
                        }
                    ),
                    headers={"Content-Type": "application/json"},
                )
            self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.50))
            self._over_the_classic_connection(report)

        self.assertEqual(len(tries), 2, "the repeat was turned away as already recorded")
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.40))
        self.assertEqual(self._sales_on_record(), 1)

    def test_two_reports_of_one_sale_arriving_together_are_one_sale(self):
        """Both pass the look-up before either has left its mark; the mark
        itself is what only one of them can leave."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)
        report = self._a_sale(place=13)
        self._over_the_classic_connection(report)

        with patch.object(
            type(self.env["hr.rfid.ws.dedup"]), "_seen", return_value=False
        ):
            self._over_the_classic_connection(report)

        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.40))

    def test_a_repeat_is_accepted_so_the_module_stops_sending_it(self):
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)
        post = {"convertor": self.module.serial, "event": self._a_sale(place=14)}

        first = self.module._hw_parse_event(post)
        again = self.module._hw_parse_event(post)

        self.assertEqual(first.get("status"), 200)
        self.assertEqual(again, {"status": 200})
