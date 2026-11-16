# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""What a vending machine is told, where its conversation differs from a door's.

The vending add-on answers the machine's reports itself, before the core reads
them. So what every report of a module is promised - the reply in the shape
the module reads, an answer of the moment never given later, a failed report
kept - has to hold for a machine too.
"""

import json
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.controllers.polimex import CMD_ANSWER_TIMEOUT_S
from odoo.addons.hr_rfid.tests.controller import RFIDController
from odoo.addons.hr_rfid.tests.hardware import one_door

from .vending_common import VendingFlowMixin


@tagged("rfid_vending", "rfid_vending_conversation")
class TestAVendingMachineIsAnswered(VendingFlowMixin, RFIDController, HttpCase):
    _registry_readonly_enabled = False

    def setUp(self):
        super().setUp()
        self._add_Vending()
        # The site does not keep its communication: what survives a failure
        # survives because it failed.
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_rfid.save_webstack_communications", "false"
        )

    def _post(self, serial, key, **body):
        return self.url_open(
            self.app_url,
            data=json.dumps(dict(body, convertor=serial, key=key)),
            timeout=60,
            headers={"Content-Type": "application/json"},
        )

    def test_credit_nobody_collected_is_not_offered_again(self):
        """NEGATIVE: credit for a card shown at the machine is not handed over later, to whoever stands there then."""
        self._machine_counts_in_fives()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.15)
        response = self._ev64(self.test_card_employee.number)
        self.assertEqual(response["cmd"]["c"], "DB")
        credit = self.env["hr.rfid.command"].search(
            [("controller_id", "=", self.c_vending.id), ("status", "=", "Process")]
        )
        self.assertEqual(credit.cmd, "DB2")
        credit.sent_at = fields.Datetime.now() - timedelta(
            seconds=CMD_ANSWER_TIMEOUT_S + 5
        )

        later = self._hearbeat(self.c_vending.webstack_id)

        self.assertEqual(later, {})
        self.assertEqual((credit.status, credit.retries), ("Failure", 0))

    def test_a_vending_report_that_fails_keeps_what_was_sent(self):
        """When a machine's report fails here, what it sent is kept with the place it failed.

        The machine's module reads the empty reply as "accepted" and forgets
        the report, so the record is the only copy of it.
        """
        module = self.c_vending.webstack_id
        module.key = "AB12"
        before = self._newest_system_event()
        with patch.object(
            type(self.env["hr.rfid.vending.event"]),
            "create",
            side_effect=ValueError("the event could not be written"),
        ):
            reply = self._post(
                module.serial,
                module.key,
                event={
                    "bos": 1,
                    "tos": 1,
                    "card": self.test_card_employee.number,
                    "cmd": "FA",
                    "date": self.test_date_10_3,
                    "day": self.test_dow_10_3,
                    "dt": "00000000000000",
                    "time": self.test_time_10_3,
                    "err": 0,
                    "event_n": 64,
                    "id": self.c_vending.ctrl_id,
                    "reader": 1,
                },
            )

        self.assertEqual((reply.status_code, reply.text), (200, ""))
        self.env.invalidate_all()
        kept = self.env["hr.rfid.event.system"].search(
            [("id", ">", before), ("webstack_id", "=", module.id)]
        )
        self.assertEqual(len(kept), 1)
        self.assertIn("the event could not be written", kept.error_description)
        self.assertIn(self.test_card_employee.number, kept.input_js)
        self.assertNotIn(
            "AB12", kept.input_js, "the copy that people read does not carry the key"
        )

    def test_a_refusal_comes_in_the_shape_of_the_module_that_asked(self):
        """A module refused for its key is told so in its own language, whoever reported before it.

        The shape of the reply was remembered from one request to the next,
        so a new module with a wrong key got the empty reply of the old
        module that had reported before it - which it reads as nothing.
        """
        old = self.c_vending.webstack_id
        old.key = "AB12"
        new = one_door(self.env, "New", 7799, 44, serial="400799", key="C3D4")[
            0
        ].controller_id.webstack_id

        self._post(old.serial, old.key, FW="1.3400", heartbeat=1)
        refused = self._post(new.serial, "DEAD", FW="1.44", heartbeat=1)
        self.assertEqual(refused.json(), {"status": 400})

        self._post(new.serial, new.key, FW="1.44", heartbeat=2)
        refused = self._post(old.serial, "DEAD", FW="1.3400", heartbeat=2)
        self.assertEqual((refused.status_code, refused.text), (200, ""))

    def test_a_credit_request_handed_to_the_core_is_answered_by_the_add_on(self):
        """A credit request read where every report is read gets the machine its credit.

        That is where the real-time connection hands its reports. The add-on
        answers there, and the log is not told that vending is missing or
        that real time has to be switched off.
        """
        self._machine_counts_in_fives()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.15)
        module = self.c_vending.webstack_id

        told = module.with_context(ws_skip_piggyback=True)._hw_parse_event(
            {"convertor": module.serial, "event": self._machine_report(64)}
        )

        self.assertEqual((told["status"], told["cmd"]["c"]), (200, "DB"))
        said = " ".join(
            self.env["hr.rfid.event.system"]
            .search([("controller_id", "=", self.c_vending.id)])
            .mapped(lambda event: event.error_description or "")
        )
        self.assertNotIn("not installed", said)
        self.assertNotIn("did not reach", said)

    def _with_credit(self):
        self._machine_counts_in_fives()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.15)

    def test_a_credit_request_that_arrives_late_gets_no_credit(self):
        """NEGATIVE: a card shown ten minutes ago is not given credit now.

        The report was held up on its way. Whoever showed the card has walked
        away from the machine: the request is recorded and nothing is sent.
        """
        self._with_credit()
        shown = self.test_now - timedelta(minutes=10)
        self.test_date_10_3 = "%02d.%02d.%02d" % (
            shown.day,
            shown.month,
            shown.year - 2000,
        )
        self.test_time_10_3 = "%02d:%02d:%02d" % (
            shown.hour,
            shown.minute,
            shown.second,
        )

        response = self._ev64()

        self._assert_deny(response)
        self.assertEqual(self._vending_event_count(), 1, "and it is on record")

    def test_a_credit_request_the_machine_has_already_moved_past_gets_no_credit(self):
        """NEGATIVE: a request that is not the machine's newest event is history.

        The controller counts what it has recorded (the top) and what it has
        reported (the bottom). A request reported from below the top was made
        before other things happened at the machine, so no credit goes out
        for it.
        """
        self._with_credit()

        response = self._ev64(bos=3, tos=9)

        self._assert_deny(response)
        self.assertEqual(self._vending_event_count(), 1, "and it is on record")

    def test_a_sale_on_a_card_nobody_here_knows_is_not_booked_as_cash(self):
        """NEGATIVE: the machine reports a sale on a card this company does not have.

        It is not a coin sale: the cash in the machine does not grow, and no
        sale is recorded for nobody. The report is the core's to deal with,
        as an unknown card is at any door.
        """
        self._machine_counts_in_fives()
        self.c_vending.write({"cash_contained": 0})

        self._ev47(product_slot=0, price_units=1, card_number="0099887766")

        self.c_vending.invalidate_recordset()
        self.assertEqual(self.c_vending.cash_contained, 0)
        self.assertFalse(
            self.env["hr.rfid.vending.event"].search(
                [
                    ("controller_id", "=", self.c_vending.id),
                    ("event_action", "=", "47"),
                ]
            )
        )

    def test_the_kept_copy_of_a_report_carries_no_key(self):
        """NEGATIVE: on a site that keeps its communication, the sale's copy of the report is without the module's key.

        The copy is read by whoever looks at the vending events. The key is
        what the module proves itself with, and nobody needs it to read a sale.
        """
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_rfid.save_webstack_communications", "true"
        )
        self._with_credit()
        module = self.c_vending.webstack_id

        self._ev47(product_slot=0, price_units=1)

        kept = (
            self.env["hr.rfid.vending.event"]
            .search(
                [
                    ("controller_id", "=", self.c_vending.id),
                    ("event_action", "=", "47"),
                ]
            )
            .input_js
        )
        self.assertIn(module.serial, kept, "the report itself is kept")
        self.assertNotIn('"key"', kept)
        self.assertNotIn(module.key, json.loads(kept).values())
