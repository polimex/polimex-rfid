# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""A vending machine behind a real-time module is served like any other.

Credit and sales used to be answered only in the route of the module's
classic connection. A machine behind a module on the real-time connection got
no credit at all, and the log told the operator to switch real time off. The
owner's decision (16.11.2026): the vending answers belong where every report
of a module is read, so that they hold whichever way the report came - and
the demo, which walks the same path, can show a machine at work.
"""

from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.models.hr_rfid_webstack_ws import WS_PROTO_VERSION
from odoo.addons.hr_rfid.tests.controller import RFIDController

from .vending_common import VendingFlowMixin, fc, take_everyone_off_auto_refill

NO_CARD = "0000000000"


@tagged("rfid_vending", "rfid_vending_real_time", "post_install", "-at_install")
class TestAVendingMachineOverRealTime(VendingFlowMixin, RFIDController, HttpCase):
    _registry_readonly_enabled = False

    def setUp(self):
        super().setUp()
        take_everyone_off_auto_refill(self.env)
        self._add_Vending()
        self._setup_products()
        self._reset_employee()
        # The tests are about what the machine is told, not about how the
        # channel proves itself: without the secret a keyed module is let in.
        self.env["ir.config_parameter"].sudo().set_param("hr_rfid.ws_fw_secret", "")
        self.module = self.c_vending.webstack_id
        self.module.action_ws_enable()

    def _over_real_time(self, *reports, batch=1):
        """Hand a batch of the machine's reports to the real-time entry point.

        :return: the acknowledgement the module is sent for the batch
        """
        message = {
            "v": WS_PROTO_VERSION,
            "s": self.module.serial,
            "k": self.module.sudo().key,
            "t": "ev",
            "bid": batch,
            "ev": list(reports),
        }
        with patch.object(type(self.env["bus.bus"]), "_sendone") as sendone:
            self.env["ir.websocket"]._serve_ir_websocket("hr_rfid", message)
        acknowledged = [
            call.args[2]
            for call in sendone.call_args_list
            if call.args[1] == "hr_rfid.ev_ack"
        ]
        self.assertEqual(len(acknowledged), 1, "one batch, one acknowledgement")
        return acknowledged[0]

    def _log_of_the_machine(self):
        return " ".join(
            self._system_events().mapped(lambda event: event.error_description or "")
        )

    def test_a_card_shown_at_the_machine_gets_its_credit_at_once(self):
        """Fifteen cents of credit, the card is shown: the machine is told three units.

        The answer rides in the acknowledgement of the report itself, because
        the person is standing at the machine now.
        """
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.15)

        told = self._over_real_time(self._machine_report(64))

        self.assertEqual(told["res"], [{"i": 0, "ok": True, "dup": False}])
        credit = told["cmd"]["cmd"]
        self.assertEqual(credit["c"], "DB")
        self.assertTrue(credit["d"].startswith("4000"))
        units = int(credit["d"][-4:-2], 16) * 0x10 + int(credit["d"][-2:], 16)
        self.assertEqual(units, 3, "0.15 in a machine that counts in fives")
        sent = self.env["hr.rfid.command"].browse(told["cmd"]["cid"])
        self.assertEqual((sent.cmd, sent.controller_id), ("DB2", self.c_vending))
        self.assertTrue(
            sent.single_attempt, "credit nobody collected is not offered again later"
        )

    def test_a_card_without_credit_gets_none(self):
        """NEGATIVE: no credit on the card - no command for the machine, and the request is on record."""
        told = self._over_real_time(self._machine_report(64))

        self.assertEqual(told["res"], [{"i": 0, "ok": True, "dup": False}])
        self.assertNotIn("cmd", told)
        self.assertEqual(self._vending_event_count(), 1)

    def test_a_sale_takes_the_price_off_the_buyers_credit(self):
        """Half a euro of credit, the item in slot two costs ten cents: forty cents are left.

        And the sale is on record with what was bought and by whom.
        """
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)

        told = self._over_real_time(
            self._machine_report(47, self._sale_dt(product_slot=2, price_units=2))
        )

        self.assertEqual(told["res"], [{"i": 0, "ok": True, "dup": False}])
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.40))
        sale = self.env["hr.rfid.vending.event"].search(
            [("controller_id", "=", self.c_vending.id), ("event_action", "=", "47")]
        )
        self.assertEqual(
            (sale.item_sold_id, sale.employee_id),
            (self.products[1], self.test_employee_id),
        )
        self.assertTrue(fc(sale.transaction_price, 0.10))

    def test_a_cash_sale_goes_into_the_machines_cash(self):
        """No card, one unit paid in coins: five cents more in the machine."""
        self.c_vending.write({"cash_contained": 0})

        self._over_real_time(
            self._machine_report(
                47, self._sale_dt(product_slot=0, price_units=1), card_number=NO_CARD
            )
        )

        self.c_vending.invalidate_recordset()
        self.assertTrue(fc(self.c_vending.cash_contained, 0.05))

    def test_the_same_report_sent_twice_is_one_sale(self):
        """NEGATIVE: the module repeats a report it got no acknowledgement for - nobody pays twice."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)
        report = self._machine_report(
            47, self._sale_dt(product_slot=2, price_units=2), bos=7
        )

        self._over_real_time(report, batch=1)
        again = self._over_real_time(report, batch=2)

        self.assertEqual(again["res"], [{"i": 0, "ok": True, "dup": True}])
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.40))

    def test_the_operator_is_no_longer_sent_to_switch_real_time_off(self):
        """NEGATIVE: a credit request over real time leaves no "use the classic connection" in the log."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.15)

        self._over_real_time(self._machine_report(64))

        said = self._log_of_the_machine()
        self.assertNotIn("real-time", said)
        self.assertNotIn("did not reach", said)

    def test_the_demo_walks_the_same_path(self):
        """A report handed straight to where every report is read books the sale too.

        That is how the demo module feeds its simulated machine, with no
        module on the line at all.
        """
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)

        told = self.module.with_context(ws_skip_piggyback=True)._hw_parse_event(
            {
                "convertor": self.module.serial,
                "event": self._machine_report(
                    47, self._sale_dt(product_slot=2, price_units=2)
                ),
            }
        )

        self.assertEqual(told, {"status": 200})
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.40))
