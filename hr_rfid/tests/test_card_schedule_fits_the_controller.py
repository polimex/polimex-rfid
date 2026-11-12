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
"""

from odoo import exceptions
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.tests.common import RFIDAppCase


@tagged("standard", "at_install", "rfid", "rfid_access_group", "rfid_card_schedule")
class TestCardScheduleFitsTheController(RFIDAppCase):
    def _door_on(self, hw_version, ctrl_id, readers=(1,)):
        ctrl = self.env["hr.rfid.ctrl"].create(
            {
                "name": "Ctrl %s" % hw_version,
                "ctrl_id": ctrl_id,
                "webstack_id": self.test_webstack_10_3_id.id,
                "hw_version": hw_version,
                "serial_number": str(900 + ctrl_id),
                "sw_version": "030",
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

    def _schedule(self, number):
        return self.env["hr.rfid.time.schedule"].search(
            [("number", "=", number), ("company_id", "=", self.test_company_id)],
            limit=1,
        )

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
        """A day holds intervals 0-3, and hours run 0-24; anything else is refused."""
        Line = self.env["hr.rfid.ctrl.ts.line"]
        with self.assertRaises(exceptions.ValidationError):
            Line.create({"number": 4, "begin": 8.0, "end": 12.0})
        with self.assertRaises(exceptions.ValidationError):
            Line.create({"number": 0, "begin": 8.0, "end": 25.0})
        line = Line.create({"number": 3, "begin": 8.0, "end": 12.0})
        self.assertEqual(line.number, 3, "NEGATIVE: a valid interval is kept")

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
