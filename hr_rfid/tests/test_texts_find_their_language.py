# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
"""A text written with nobody at a screen still finds its language quietly.

A door is named when its controller describes itself over the real-time
connection, and a number plate is refused while cards are brought in from a
file or the API: both happen where no user's language travels with the call.
Asked there for a translation, the plain translation function logs a warning
with a whole stack - once for every door of every controller.
"""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.models.hr_rfid_webstack_ws import WS_PROTO_VERSION
from odoo.addons.hr_rfid.tests.common import RFIDAppCase

TRANSLATION_LOG = "odoo.tools.translate"
# What an iCON110 says about itself (two readers), as in tests/common.py.
ICON110_DESCRIBES_ITSELF = (
    "0006000400000704000000030000030201050208000200010502060003000506"
)
CONTROLLER_NUMBER = 5


@tagged("standard", "at_install", "rfid", "rfid_texts")
class TestTextsFindTheirLanguage(RFIDAppCase):
    def _module_says(self, module, kind, **payload):
        message = {
            "v": WS_PROTO_VERSION,
            "s": module.serial,
            "k": module.sudo().key,
            "t": kind,
            **payload,
        }
        with patch.object(type(self.env["bus.bus"]), "_sendone"):
            self.env["ir.websocket"]._serve_ir_websocket("hr_rfid", message)

    def test_a_controller_names_its_doors_without_a_warning(self):
        # The signature of the first message is not what this test is about.
        self.env["ir.config_parameter"].sudo().set_param("hr_rfid.ws_fw_secret", "")
        module = self.test_webstack_10_3_id
        module.action_ws_enable()
        self._module_says(module, "hello", fw="2.01", ctrl=[CONTROLLER_NUMBER])
        controller = module.controllers.filtered(
            lambda c: c.ctrl_id == CONTROLLER_NUMBER
        )
        asked = (
            self.env["hr.rfid.command"]
            .sudo()
            .search(
                [("controller_id", "=", controller.id), ("cmd", "=", "F0")], limit=1
            )
        )
        asked.status = "Process"

        with self.assertNoLogs(TRANSLATION_LOG, level="WARNING"):
            self._module_says(
                module,
                "rsp",
                cid=asked.id,
                r={
                    "id": CONTROLLER_NUMBER,
                    "c": "F0",
                    "e": 0,
                    "d": ICON110_DESCRIBES_ITSELF,
                },
            )

        doors = controller.door_ids
        self.assertTrue(doors, "the controller described itself and has its doors")
        self.assertTrue(all(doors.mapped("name")), "every door got its name")

    def test_a_refused_plate_is_told_without_a_warning(self):
        plates = self.env.ref("hr_rfid.hr_rfid_card_type_8")

        with (
            self.assertNoLogs(TRANSLATION_LOG, level="WARNING"),
            self.assertRaises(UserError) as refused,
        ):
            plates.check_and_fix_card_numer("CB5803@M")

        self.assertIn('"@"', str(refused.exception))

    def test_an_output_on_a_schedule_reads_as_its_output_and_schedule(self):
        schedule = self._schedule(1)
        controller = self.env["hr.rfid.ctrl"].create(
            {
                "name": "Controller with outputs",
                "ctrl_id": self._get_id_num(),
                "webstack_id": self.test_webstack_10_3_id.id,
                "outputs": 4,
                "time_schedules": 4,
            }
        )
        row = self.env["hr.rfid.ctrl.output.ts"].create(
            {
                "controller_id": controller.id,
                "output_number": 2,
                "time_schedule_id": schedule.id,
            }
        )

        self.assertEqual(
            row.with_context(lang="en_US").display_name,
            "Output 2 working with TS %s" % schedule.name,
        )
