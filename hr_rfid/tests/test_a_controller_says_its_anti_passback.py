# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
"""A controller that checks anti-passback shows it on its doors.

A new controller is asked which of its pairs of readers it checks (entry then
exit, never twice the same way). Its answer is one byte: the first bit is the
pair of door 1, the second the pair of door 2. The answer used to be compared
with text and never reached the doors, so a controller that refused a second
entry was shown as one that does not.
"""

from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.tests.controller import RFIDController

PAIR_OF_DOOR_1 = "01"
PAIR_OF_DOOR_2 = "02"
BOTH_PAIRS = "03"
NO_PAIR = "00"


@tagged("standard", "at_install", "rfid", "rfid_apb")
class TestAControllerSaysItsAntiPassback(RFIDController, HttpCase):
    _registry_readonly_enabled = False

    def _two_doors_of_two_readers(self):
        self._add_iCon130()
        self._change_mode(self.c_130, 2)
        doors = self.c_130.door_ids.sorted("number")
        self.assertEqual(doors.mapped("number"), [1, 2])
        for door in doors:
            self.assertEqual(len(door.reader_ids), 2)
        return doors

    def _controller_answers(self, controller, flags):
        controller.read_anti_pass_back_mode_cmd()
        asked = self._hearbeat(controller.webstack_id)
        self.assertEqual(asked["cmd"]["c"], "FC")
        self._send_cmd_response(asked, flags)

    def _written_back(self, controller):
        return self.env["hr.rfid.command"].search_count(
            [("controller_id", "=", controller.id), ("cmd", "=", "DE")]
        )

    def test_the_pair_of_the_first_door_shows_on_that_door_only(self):
        first, second = self._two_doors_of_two_readers()

        self._controller_answers(self.c_130, PAIR_OF_DOOR_1)

        self.assertTrue(first.apb_mode)
        self.assertFalse(second.apb_mode)

    def test_the_pair_of_the_second_door_shows_on_that_door_only(self):
        first, second = self._two_doors_of_two_readers()

        self._controller_answers(self.c_130, PAIR_OF_DOOR_2)

        self.assertFalse(first.apb_mode)
        self.assertTrue(second.apb_mode)

    def test_both_pairs_show_on_both_doors_and_nothing_is_written_back(self):
        doors = self._two_doors_of_two_readers()

        self._controller_answers(self.c_130, BOTH_PAIRS)

        self.assertEqual(doors.mapped("apb_mode"), [True, True])
        self.assertEqual(
            self._written_back(self.c_130),
            0,
            "reading what the controller does is not a change of it",
        )

    def test_a_controller_that_checks_nothing_clears_the_doors(self):
        doors = self._two_doors_of_two_readers()
        doors.with_context(no_hardware_commands=True).write({"apb_mode": True})

        self._controller_answers(self.c_130, NO_PAIR)

        self.assertEqual(doors.mapped("apb_mode"), [False, False])

    def test_a_door_with_one_reader_is_never_shown_as_checked(self):
        """One door with entry and exit readers, two doors with a reader each:
        a single reader has no pair to check, whatever the controller says."""
        self._add_iCon130()
        self._change_mode(self.c_130, 3)
        doors = self.c_130.door_ids.sorted("number")
        self.assertEqual([len(door.reader_ids) for door in doors[:2]], [2, 1])

        self._controller_answers(self.c_130, BOTH_PAIRS)

        self.assertTrue(doors[0].apb_mode)
        self.assertFalse(doors[1].apb_mode)

    def test_a_turnstile_that_checks_its_readers_shows_it(self):
        self._add_Turnstile()
        door = self.c_turnstile.door_ids
        self.assertFalse(door.apb_mode)

        self._controller_answers(self.c_turnstile, PAIR_OF_DOOR_1)

        self.assertTrue(door.apb_mode)
