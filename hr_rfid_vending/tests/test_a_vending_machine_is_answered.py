# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""What a vending machine is told, where its conversation differs from a door's.

The vending add-on answers the machine in its own route, in front of the one
every other controller goes through. So what that route promises - the reply
in the shape the module reads, an answer of the moment never given later, a
failed report kept - has to hold here too.
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

    def test_a_request_past_the_add_on_is_not_blamed_on_a_missing_add_on(self):
        """NEGATIVE: a credit request that did not come through the add-on's route is not logged as "not installed".

        The real-time connection hands its events straight to the core. The
        log then has to say that vending is served the classic way only.
        """
        module = self.c_vending.webstack_id

        told = module.with_context(
            ws_skip_piggyback=True
        )._hw_vending_request_for_balance(self.c_vending, {"convertor": module.serial})

        self.assertEqual(told, {"status": 200})
        said = (
            self.env["hr.rfid.event.system"]
            .search(
                [("controller_id", "=", self.c_vending.id)], order="id desc", limit=1
            )
            .error_description
        )
        self.assertIn("did not reach the vending add-on", said)
        self.assertNotIn("not installed", said)
