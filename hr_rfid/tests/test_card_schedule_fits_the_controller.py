# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""A card goes to a controller with a schedule the controller can hold.

The business rule, from the protocol team's reading of each firmware (protocol
change D47, 12.11.2026): iCON130 and iCON180 keep time schedules 0-3 for a card
and refuse the WHOLE card write above that - the person's card simply never
reaches the door. iCON110, iCON115 and the turnstile take 0-15. Whoever sets up
an access group must be stopped with words at the moment they choose the
schedule, not find out from a door that does not open.

And a door with an entry and an exit reader keeps the schedule on both: a card
written with the schedule on one reader only opens the other at any hour.

A second rule, from the protocol team's reading of the delivered firmware files
(23.11.2026): iCON115 builds 7.44 and 7.46 take any schedule and then read it
wrongly - schedule 4, 8 or 12 lets the card in at any hour, 5 is checked as 1,
and the second reader is checked against the schedule of the first. Until a
build that reads it right is out, a door of such a controller takes schedules
0-3 and the same one as the controller's other door. Other builds of the
iCON115 are left alone (the owner's decision, 27.11.2026).
"""

from odoo import exceptions
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.models.hr_rfid_command import F0Parse
from odoo.addons.hr_rfid.tests.common import RFIDAppCase


@tagged("standard", "at_install", "rfid", "rfid_access_group", "rfid_card_schedule")
class TestCardScheduleFitsTheController(RFIDAppCase):
    def _door_on(self, hw_version, ctrl_id, readers=(1,), sw_version="030"):
        ctrl = self.env["hr.rfid.ctrl"].create(
            {
                "name": "Ctrl %s" % hw_version,
                "ctrl_id": ctrl_id,
                "webstack_id": self.test_webstack_10_3_id.id,
                "hw_version": hw_version,
                "serial_number": str(900 + ctrl_id),
                "sw_version": sw_version,
                "mode": 1,
                "inputs": 1,
                "outputs": 1,
                "readers": len(readers),
            }
        )
        door = self.env["hr.rfid.door"].create(
            {
                "name": "Door on %s" % hw_version,
                "number": 1,
                "controller_id": ctrl.id,
                "company_id": self.test_company_id,
            }
        )
        for number in readers:
            self.env["hr.rfid.reader"].create(
                {
                    "name": "R%d" % number,
                    "number": number,
                    "reader_type": "0" if number == 1 else "1",
                    "mode": "01",
                    "controller_id": ctrl.id,
                    "door_id": door.id,
                }
            )
        return door

    def _second_door_of(self, door):
        """The controller's other door, on its reader 2."""
        ctrl = door.controller_id
        second = self.env["hr.rfid.door"].create(
            {
                "name": "Second door of %s" % ctrl.name,
                "number": 2,
                "controller_id": ctrl.id,
                "company_id": self.test_company_id,
            }
        )
        self.env["hr.rfid.reader"].create(
            {
                "name": "R2",
                "number": 2,
                "reader_type": "0",
                "mode": "01",
                "controller_id": ctrl.id,
                "door_id": second.id,
            }
        )
        return second

    def _group_on(self, door, schedule):
        group = self.env["hr.rfid.access.group"].create(
            {
                "name": "Group for %s" % door.name,
                "company_id": self.test_company_id,
            }
        )
        return self.env["hr.rfid.access.group.door.rel"].create(
            {
                "access_group_id": group.id,
                "door_id": door.id,
                "time_schedule_id": schedule.id,
            }
        )

    def test_an_icon130_door_refuses_a_schedule_above_3_in_words(self):
        """Schedule 4 on an iCON130 door is stopped, naming the door and 0 to 3."""
        door = self._door_on("17", 91)
        with self.assertRaises(exceptions.ValidationError) as refused:
            self._group_on(door, self._schedule(4))
        message = str(refused.exception)
        self.assertIn(door.name, message)
        self.assertIn("0 to 3", message)

    def test_an_icon130_door_takes_schedule_3(self):
        """NEGATIVE: the highest number the controller holds is accepted."""
        door = self._door_on("17", 92)
        rel = self._group_on(door, self._schedule(3))
        self.assertEqual(rel.time_schedule_id.number, 3)

    def test_an_icon110_door_takes_schedule_15(self):
        """NEGATIVE: the 0-3 limit is the iCON130's, not every controller's."""
        door = self._door_on("6", 93)
        rel = self._group_on(door, self._schedule(15))
        self.assertEqual(rel.time_schedule_id.number, 15)

    def test_both_readers_of_a_door_carry_the_card_schedule(self):
        """Entry and exit reader alike get schedule 2 in the card write.

        Measured on the real path - the card command the controller receives -
        not on a helper: a card with the schedule on one reader opens the other
        at any hour.
        """
        door = self._door_on("6", 94, readers=(1, 2))
        card = self.test_card_employee
        self.env["hr.rfid.command"].add_card(
            door.id, self._schedule(2).id, "", card.id, False
        )

        writes = self.env["hr.rfid.command"].search(
            [
                ("controller_id", "=", door.controller_id.id),
                ("cmd", "=", "D1"),
                ("card_number", "=", card.internal_number),
            ]
        )
        self.assertTrue(writes, "a card write was queued for the controller")
        slots = {
            reader: max(
                int(c.ts_code[(reader - 1) * 2 : reader * 2], 16) for c in writes
            )
            for reader in (1, 2)
        }
        self.assertEqual(slots, {1: 2, 2: 2})
        card_door = self.env["hr.rfid.card.door.rel"].new(
            {
                "door_id": door.id,
                "time_schedule_id": self._schedule(2).id,
            }
        )
        self.assertEqual(
            card_door.get_ts_code_string(),
            "02020000",
            "and the helper that reads the same thing back agrees",
        )

    def test_a_schedule_interval_outside_its_slots_is_refused(self):
        """A day holds periods 1-4, as the editor numbers them, and hours run
        0-24; anything else is refused."""
        Line = self.env["hr.rfid.ctrl.ts.line"]
        with self.assertRaises(exceptions.ValidationError):
            Line.create({"number": 5, "begin": 8.0, "end": 12.0})
        with self.assertRaises(exceptions.ValidationError):
            Line.create({"number": 0, "begin": 8.0, "end": 12.0})
        with self.assertRaises(exceptions.ValidationError):
            Line.create({"number": 1, "begin": 8.0, "end": 25.0})
        line = Line.create({"number": 4, "begin": 8.0, "end": 12.0})
        self.assertEqual(line.number, 4, "NEGATIVE: a valid interval is kept")

    def _refused_card_write(self, door, ts_code):
        return self.env["hr.rfid.command"].create(
            {
                "webstack_id": door.controller_id.webstack_id.id,
                "controller_id": door.controller_id.id,
                "cmd": "D1",
                "card_number": "0012345678",
                "ts_code": ts_code,
                "status": "Failure",
                "error": "4",
            }
        )

    def test_a_card_the_controller_refused_for_its_schedule_is_explained(self):
        """The controller's log says the card was not written, and why."""
        door = self._door_on("17", 95)
        Event = self.env["hr.rfid.event.system"]
        before = Event.search_count([("controller_id", "=", door.controller_id.id)])

        self._refused_card_write(door, "04000000")._explain_a_refused_card_schedule()

        events = Event.search([("controller_id", "=", door.controller_id.id)])
        self.assertEqual(len(events), before + 1)
        self.assertIn("0012345678", events[0].error_description)
        self.assertIn("0 to 3", events[0].error_description)

    def test_a_refusal_within_the_limit_is_not_blamed_on_the_schedule(self):
        """NEGATIVE: "wrong value" with schedule 2 has another cause; say nothing."""
        door = self._door_on("17", 96)
        Event = self.env["hr.rfid.event.system"]
        before = Event.search_count([("controller_id", "=", door.controller_id.id)])

        self._refused_card_write(door, "02000000")._explain_a_refused_card_schedule()

        self.assertEqual(
            Event.search_count([("controller_id", "=", door.controller_id.id)]), before
        )

    # ------------------------------------------------------------------
    # iCON115 builds 7.44 and 7.46 read the schedule wrongly
    # ------------------------------------------------------------------

    def test_an_icon115_on_7_44_refuses_a_schedule_above_3_naming_the_firmware(self):
        door = self._door_on("11", 101, sw_version="744")
        with self.assertRaises(exceptions.ValidationError) as refused:
            self._group_on(door, self._schedule(4))
        message = str(refused.exception)
        self.assertIn(door.name, message)
        self.assertIn("firmware 7.44", message)
        self.assertIn("0 to 3", message)

    def test_an_icon115_on_7_46_refuses_a_schedule_above_3(self):
        door = self._door_on("11", 102, sw_version="746")
        with self.assertRaises(exceptions.ValidationError) as refused:
            self._group_on(door, self._schedule(12))
        self.assertIn("firmware 7.46", str(refused.exception))

    def test_an_icon115_on_7_44_takes_schedule_3(self):
        """NEGATIVE: the numbers the build reads right stay open."""
        door = self._door_on("11", 103, sw_version="744")
        rel = self._group_on(door, self._schedule(3))
        self.assertEqual(rel.time_schedule_id.number, 3)

    def test_an_icon115_on_another_build_takes_schedule_15(self):
        """NEGATIVE: the limit is of builds 7.44 and 7.46, not of the model."""
        for sw_version, ctrl_id in (("738", 104), ("745", 105), ("747", 106)):
            door = self._door_on("11", ctrl_id, sw_version=sw_version)
            rel = self._group_on(door, self._schedule(15))
            self.assertEqual(rel.time_schedule_id.number, 15, sw_version)

    def test_a_hotel_icon115_takes_schedule_15(self):
        """NEGATIVE: the hotel iCON115 holds 0-15 like the iCON115."""
        door = self._door_on("13", 107)
        self.assertEqual(door.controller_id._card_schedule_max(), 15)
        rel = self._group_on(door, self._schedule(15))
        self.assertEqual(rel.time_schedule_id.number, 15)

    def test_the_two_doors_of_an_icon115_on_7_44_take_one_schedule(self):
        """The second reader is checked against the first one's schedule, so a
        group that gives the two doors different hours is refused in words."""
        door = self._door_on("11", 108, sw_version="744")
        second = self._second_door_of(door)
        rel = self._group_on(door, self._schedule(1))
        with self.assertRaises(exceptions.ValidationError) as refused:
            self.env["hr.rfid.access.group.door.rel"].create(
                {
                    "access_group_id": rel.access_group_id.id,
                    "door_id": second.id,
                    "time_schedule_id": self._schedule(2).id,
                }
            )
        message = str(refused.exception)
        self.assertIn(door.name, message)
        self.assertIn(second.name, message)
        self.assertIn("firmware 7.44", message)
        self.assertIn(rel.access_group_id.name, message)

    def test_the_two_doors_of_an_icon115_on_7_44_may_share_a_schedule(self):
        """NEGATIVE: the same schedule on both doors is what the build does."""
        door = self._door_on("11", 109, sw_version="744")
        second = self._second_door_of(door)
        rel = self._group_on(door, self._schedule(2))
        other = self.env["hr.rfid.access.group.door.rel"].create(
            {
                "access_group_id": rel.access_group_id.id,
                "door_id": second.id,
                "time_schedule_id": self._schedule(2).id,
            }
        )
        self.assertEqual(other.time_schedule_id, rel.time_schedule_id)

    def test_the_two_doors_of_an_icon115_on_another_build_keep_their_own(self):
        """NEGATIVE: a build that reads each reader's schedule is left alone."""
        door = self._door_on("11", 111, sw_version="738")
        second = self._second_door_of(door)
        rel = self._group_on(door, self._schedule(1))
        other = self.env["hr.rfid.access.group.door.rel"].create(
            {
                "access_group_id": rel.access_group_id.id,
                "door_id": second.id,
                "time_schedule_id": self._schedule(2).id,
            }
        )
        self.assertNotEqual(other.time_schedule_id, rel.time_schedule_id)

    def test_two_controllers_on_7_44_keep_their_own_schedules(self):
        """NEGATIVE: the build mixes up the two readers of ONE controller.
        Doors of two controllers have nothing to do with each other."""
        door = self._door_on("11", 114, sw_version="744")
        elsewhere = self._door_on("11", 115, sw_version="744")
        rel = self._group_on(door, self._schedule(1))
        other = self.env["hr.rfid.access.group.door.rel"].create(
            {
                "access_group_id": rel.access_group_id.id,
                "door_id": elsewhere.id,
                "time_schedule_id": self._schedule(2).id,
            }
        )
        self.assertNotEqual(other.time_schedule_id, rel.time_schedule_id)

    def test_the_version_a_controller_reports_is_the_one_the_rule_reads(self):
        """A controller describes itself with its version digit by digit
        (07 04 04). What is kept from that is what the rule looks for - on a
        mismatch the rule would never fire, and nothing would say so."""
        described = "0101" + "01020304" + "070404" + "00" * 30
        Command = self.env["hr.rfid.command"]
        version = Command._parse_f0_cmd(described)[F0Parse.sw_ver]
        self.assertEqual(version, "744")
        door = self._door_on("11", 116, sw_version=version)
        self.assertTrue(door.controller_id._misreads_card_schedule())
        self.assertEqual(door.controller_id._firmware_version_name(), "7.44")

    def test_a_door_added_to_a_group_somebody_already_holds_is_checked_too(self):
        """The order on a live site: the person has both groups, then the
        second door of the controller is added to one of them with other hours."""
        door = self._door_on("11", 117, sw_version="744")
        second = self._second_door_of(door)
        elsewhere = self._door_on("6", 118)
        first_group = self._group_on(door, self._schedule(1)).access_group_id
        second_group = self._group_on(elsewhere, self._schedule(2)).access_group_id
        department = self.test_employee_id.department_id
        department.hr_rfid_allowed_access_groups = [
            (4, first_group.id, 0),
            (4, second_group.id, 0),
        ]
        self.test_employee_id.add_acc_gr(first_group)
        self.test_employee_id.add_acc_gr(second_group)

        with self.assertRaises(exceptions.ValidationError) as refused:
            second_group.add_doors(second, self._schedule(2))
        self.assertIn("firmware 7.44", str(refused.exception))

    def test_a_person_is_given_a_group_whatever_the_firmware_does(self):
        """NEGATIVE: the rule stops the set-up of a door in a group. It never
        stops a group being given to a person - a card issued at a reception
        or an employee hired must not fail because of a firmware build."""
        door = self._door_on("11", 112, sw_version="744")
        second = self._second_door_of(door)
        first_group = self._group_on(door, self._schedule(1)).access_group_id
        second_group = self._group_on(second, self._schedule(2)).access_group_id
        department = self.test_employee_id.department_id
        department.hr_rfid_allowed_access_groups = [
            (4, first_group.id, 0),
            (4, second_group.id, 0),
        ]

        self.test_employee_id.add_acc_gr(first_group)
        self.test_employee_id.add_acc_gr(second_group)

        held = self.test_employee_id.hr_rfid_access_group_ids.access_group_id
        self.assertIn(first_group, held)
        self.assertIn(second_group, held)

    # A setting that is already there is nobody's choice of today.

    def _a_split_that_is_already_there(self, ctrl_id):
        """One person, two groups, the two doors of a 7.44 controller on
        different hours."""
        door = self._door_on("11", ctrl_id, sw_version="744")
        second = self._second_door_of(door)
        groups = (
            self._group_on(door, self._schedule(1)).access_group_id
            | self._group_on(second, self._schedule(2)).access_group_id
        )
        department = self.test_employee_id.department_id
        department.hr_rfid_allowed_access_groups = [
            (4, group.id, 0) for group in groups
        ]
        self.test_employee_id.add_acc_gr(groups)
        return groups

    def test_a_transfer_brings_a_site_as_it_is(self):
        """NEGATIVE: data brought across from another system, or read from
        the hardware, describe what the site has. They are not refused for
        what a firmware build does with them - the transfer would stop on a
        setting nobody is choosing now."""
        door = self._door_on("11", 119, sw_version="744")
        second = self._second_door_of(door)
        Rel = self.env["hr.rfid.access.group.door.rel"].with_context(
            no_hardware_commands=True
        )
        group = self._group_on(door, self._schedule(1)).access_group_id

        brought = Rel.create(
            {
                "access_group_id": group.id,
                "door_id": second.id,
                "time_schedule_id": self._schedule(12).id,
            }
        )

        self.assertEqual(brought.time_schedule_id.number, 12)

    def test_a_transfer_is_still_held_to_what_the_controller_can_hold(self):
        """An iCON130 refuses the whole card above schedule 3, whoever asks."""
        door = self._door_on("17", 120)
        group = self.env["hr.rfid.access.group"].create(
            {"name": "Brought across", "company_id": self.test_company_id}
        )
        with self.assertRaises(exceptions.ValidationError):
            self.env["hr.rfid.access.group.door.rel"].with_context(
                no_hardware_commands=True
            ).create(
                {
                    "access_group_id": group.id,
                    "door_id": door.id,
                    "time_schedule_id": self._schedule(5).id,
                }
            )

    def test_a_split_that_is_already_there_does_not_stop_the_persons_passages(self):
        """NEGATIVE, and the one that matters most: every granted passage of
        a visitor counts a visit on their membership. A site that already has
        the two doors on different hours must go on recording passages."""
        groups = self._a_split_that_is_already_there(121)
        membership = self.test_employee_id.hr_rfid_access_group_ids.filtered(
            lambda rel: rel.access_group_id in groups
        )
        self.assertEqual(len(membership), 2)

        membership[0].write({"expiration": False})
        self.test_employee_id.check_for_ts_inconsistencies()
        groups[0].check_for_ts_inconsistencies()

    def test_a_new_door_is_refused_even_where_a_split_is_already_there(self):
        """What is there stays; what is chosen today is still checked."""
        groups = self._a_split_that_is_already_there(122)
        elsewhere = self._door_on("11", 123, sw_version="744")
        other_door = self._second_door_of(elsewhere)
        groups[0].add_doors(elsewhere, self._schedule(1))

        with self.assertRaises(exceptions.ValidationError) as refused:
            groups[1].add_doors(other_door, self._schedule(2))
        self.assertIn("firmware 7.44", str(refused.exception))

    def test_a_card_refused_by_an_icon115_on_7_44_is_not_blamed_on_the_schedule(self):
        """NEGATIVE: that build TAKES a schedule above 3 (and misreads it), so
        its "wrong value" to a card write has another cause; say nothing."""
        door = self._door_on("11", 113, sw_version="744")
        self.assertEqual(door.controller_id._card_schedule_max(), 15)
        Event = self.env["hr.rfid.event.system"]
        before = Event.search_count([("controller_id", "=", door.controller_id.id)])

        self._refused_card_write(door, "05000000")._explain_a_refused_card_schedule()

        self.assertEqual(
            Event.search_count([("controller_id", "=", door.controller_id.id)]), before
        )
