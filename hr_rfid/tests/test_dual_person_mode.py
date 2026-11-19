# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Dual person mode reaches only the controller that carries it out.

The protocol team, from the firmware sources (19.11.2026): only iCON130
(hardware 17) opens a door for two persons in a row. The turnstile calls itself
"icon130 turniket" and never does it; on iCON50 the same bit stops
anti-passback; the older iCON180 and iCON115 refuse the whole mode write. An
administrator who switches it on must get it where it works, and must never
switch anything else off or have a controller refuse its settings.
"""

from lxml import etree

from odoo.tests.common import HttpCase, tagged
from odoo.tools.safe_eval import safe_eval

from odoo.addons.hr_rfid.tests.common import f0_with_mode_byte
from odoo.addons.hr_rfid.tests.controller import RFIDController

DUAL_PERSON_BIT = 0x08


@tagged("standard", "at_install", "rfid", "rfid_dual_person")
class TestDualPersonMode(RFIDController, HttpCase):
    _registry_readonly_enabled = False

    def _queued_mode_writes(self, ctrl):
        return self.env["hr.rfid.command"].search(
            [
                ("controller_id", "=", ctrl.id),
                ("cmd", "=", "D5"),
                ("status", "=", "Wait"),
            ]
        )

    def test_switched_on_for_an_iCON130_it_reaches_the_controller(self):
        """The administrator switches dual person mode on for an iCON130: the
        controller is told, and its other settings go with it unchanged."""
        self._add_iCon130()
        ctrl = self.c_130
        ctrl.dual_person_mode = True
        writes = self._queued_mode_writes(ctrl)
        self.assertEqual(len(writes), 1, "one mode write for the controller")
        byte = int(writes.cmd_data, 16)
        self.assertTrue(
            byte & DUAL_PERSON_BIT, "the iCON130 is told to wait for two persons"
        )
        self.assertEqual(byte & 0x07, ctrl.mode, "the mode itself is unchanged")

    def _assert_never_told(self, ctrl):
        """Saved for the controller, never sent to it."""
        ctrl.dual_person_mode = True
        self.assertFalse(
            self._queued_mode_writes(ctrl),
            "%s is not sent a mode write for a setting it does not have" % ctrl.name,
        )
        # A mode write for another reason carries the controller's settings,
        # and still not this bit.
        ctrl.relay_time_factor = "1"
        writes = self._queued_mode_writes(ctrl)
        self.assertTrue(writes, "the other setting is sent")
        self.assertFalse(
            int(writes.sorted("id")[-1].cmd_data, 16) & DUAL_PERSON_BIT,
            "%s never receives the dual person bit" % ctrl.name,
        )
        self.assertTrue(ctrl.dual_person_mode, "what was saved stays saved")

    def test_an_iCON50_keeps_its_anti_passback(self):
        self._add_iCon50()
        self._assert_never_told(self.c_50)

    def test_a_turnstile_is_not_an_iCON130_for_it(self):
        self._add_Turnstile()
        self._assert_never_told(self.c_turnstile)

    def test_an_iCON115_does_not_refuse_its_settings(self):
        self._add_iCon115()
        self._assert_never_told(self.c_115)

    def test_an_iCON180_does_not_refuse_its_settings(self):
        # The test hardware has no iCON180 of its own (_add_iCon180 answers
        # as an iCON130), so the controller reports the iCON180 code itself.
        self._add_iCon115()
        self.c_115.with_context(from_controller=True).write({"hw_version": "10"})
        self._assert_never_told(self.c_115)

    def _read_with_mode_byte(self, ctrl, mode_byte):
        f0 = self.default_F0[int(ctrl.hw_version)]
        ctrl.read_controller_information_cmd()
        response = self._hearbeat(ctrl.webstack_id)
        self.assertEqual(response["cmd"]["c"], "F0", "(%s)" % ctrl.name)
        response = self._send_cmd_response(response, f0_with_mode_byte(f0, mode_byte))
        while response != {} and response["cmd"]["c"] == "D9":
            response = self._send_cmd_response(response)

    def test_an_iCON50_with_anti_passback_is_not_shown_in_dual_person_mode(self):
        """Read back from an iCON50 whose bit 3 is set (its anti-passback),
        the controller is not shown as waiting for two persons."""
        self._add_iCon50()
        ctrl = self.c_50
        f0 = self.default_F0[int(ctrl.hw_version)]
        self._read_with_mode_byte(ctrl, int(f0[42:44], 16) | DUAL_PERSON_BIT)
        self.assertFalse(ctrl.dual_person_mode)

    def test_an_iCON130_read_back_shows_what_it_does(self):
        """Read back from an iCON130, the screen shows what the controller does."""
        self._add_iCon130()
        ctrl = self.c_130
        f0 = self.default_F0[int(ctrl.hw_version)]
        self._read_with_mode_byte(ctrl, int(f0[42:44], 16) | DUAL_PERSON_BIT)
        self.assertTrue(ctrl.dual_person_mode, "switched on at the controller")
        self._read_with_mode_byte(ctrl, int(f0[42:44], 16) & ~DUAL_PERSON_BIT)
        self.assertFalse(ctrl.dual_person_mode, "switched off at the controller")

    def test_the_switch_is_on_the_iCON130_form_only(self):
        """The switch is on the form of an iCON130 and on no other form."""
        view = self.env.ref("hr_rfid.hr_rfid_controller_view_form")
        arch = self.env["hr.rfid.ctrl"].get_view(view.id, "form")["arch"]
        node = etree.fromstring(arch).xpath("//field[@name='dual_person_mode']")
        self.assertEqual(len(node), 1, "the switch is on the controller form")
        invisible = node[0].get("invisible")
        self.assertTrue(invisible, "the switch is not shown everywhere")
        for hw_version, name in (
            ("17", "iCON130"),
            ("9", "turnstile"),
            ("12", "iCON50"),
            ("11", "iCON115"),
            ("10", "iCON180"),
            ("6", "iCON110"),
        ):
            hidden = safe_eval(invisible, {"hw_version": hw_version})
            self.assertEqual(
                hidden, hw_version != "17", "the switch on the %s form" % name
            )
