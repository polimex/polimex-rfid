# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_pms")
class TestRfidPmsRoom(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.access_group = cls.env["hr.rfid.access.group"].create({
            "name": "PMS-AG-Test",
            "company_id": cls.company.id,
        })
        cls.webstack = cls.env["hr.rfid.webstack"].create({
            "name": "PMS Test Stack",
            "serial": "PMS001",
            "company_id": cls.company.id,
            "available": "a",
            "tz": "Europe/Sofia",
            "active": True,
        })
        cls.controller = cls.env["hr.rfid.ctrl"].create({
            "name": "PMS Ctrl",
            "ctrl_id": 1,
            "webstack_id": cls.webstack.id,
        })
        cls._door_counter = 0

    @classmethod
    def _next_door(cls, label):
        cls._door_counter += 1
        return cls.env["hr.rfid.door"].create({
            "name": f"Door for {label}",
            "number": cls._door_counter,
            "controller_id": cls.controller.id,
            "company_id": cls.company.id,
        })

    def _make_room(self, name, number, group="Ungrouped"):
        door = self._next_door(name)
        return self.env["rfid_pms_base.room"].create({
            "name": name,
            "number": number,
            "group": group,
            "company_id": self.company.id,
            "access_group_id": self.access_group.id,
            "door_id": door.id,
        })

    def test_create_room(self):
        room = self._make_room("Suite 101", 101)
        self.assertEqual(room.name, "Suite 101")
        self.assertEqual(room.number, 101)
        self.assertEqual(room.access_group_id, self.access_group)

    def test_room_default_group_value(self):
        door = self._next_door("Standalone")
        room = self.env["rfid_pms_base.room"].create({
            "name": "Standalone",
            "number": 200,
            "company_id": self.company.id,
            "access_group_id": self.access_group.id,
            "door_id": door.id,
        })
        self.assertEqual(room.group, "Ungrouped")

    def test_room_number_must_be_globally_unique(self):
        from odoo.tools import mute_logger
        self._make_room("Room A", 300, group="Floor 3")
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Exception):
                self._make_room("Room B", 300, group="Floor 4")

    def test_room_number_must_be_within_range(self):
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self._make_room("Out of range", 70000)

    def test_reservation_is_empty_when_no_contacts(self):
        room = self._make_room("Empty", 500)
        self.assertFalse(room.reservation,
                         "A room with no AG contacts must report no reservation")

    def test_room_move_wiz_lists_only_free_rooms(self):
        # `reservation` is a non-stored compute, so the helper must
        # materialise the free-room set instead of putting it in the domain.
        room_from = self._make_room("Source", 600)
        free_room = self._make_room("Free Target", 601)
        self.assertFalse(room_from.reservation)
        self.assertFalse(free_room.reservation)

        wiz_record = self.env["rfid_pms_base.room_move_wiz"].with_context(
            active_id=room_from.id,
        ).new()
        domain = wiz_record._get_free_room_domain()
        self.assertEqual(len(domain), 1)
        field, op, candidates = domain[0]
        self.assertEqual(field, "id")
        self.assertEqual(op, "in")
        self.assertIn(free_room.id, candidates)
        self.assertNotIn(room_from.id, candidates,
                         "Source room must be excluded from the target choices")

    def test_room_move_wiz_default_room_from(self):
        room = self._make_room("Active", 700)
        target = self._make_room("Idle", 701)
        wiz = self.env["rfid_pms_base.room_move_wiz"].with_context(
            active_id=room.id,
        ).create({"room_to_id": target.id})
        wiz.invalidate_recordset()
        self.assertEqual(wiz.room_from_id, room)

    def test_compute_temperature_returns_stub_values(self):
        # Placeholder until a BMS sensor module supplies live data.
        room = self._make_room("Sensor stub", 800)
        self.assertEqual(room.last_temperature, 21.5)
        self.assertEqual(room.last_humidity, 45.7)
        self.assertEqual(room.last_occupancy, "1")

    def test_compute_last_insert_name_unknown_when_no_event(self):
        room = self._make_room("Quiet", 900)
        self.assertEqual(room.last_insert_name, "Unknown")

    def test_toggle_hotel_dnd_flips_door_flag(self):
        room = self._make_room("DND test", 1000)
        self.assertFalse(room.hb_dnd)
        room.with_context(btn="dnd").toggle_hotel()
        self.assertTrue(room.hb_dnd)
        room.with_context(btn="dnd").toggle_hotel()
        self.assertFalse(room.hb_dnd)

    def test_toggle_hotel_clean_flips_door_flag(self):
        room = self._make_room("Clean test", 1100)
        self.assertFalse(room.hb_clean)
        room.with_context(btn="clean").toggle_hotel()
        self.assertTrue(room.hb_clean)
        room.with_context(btn="clean").toggle_hotel()
        self.assertFalse(room.hb_clean)

    def test_toggle_hotel_unknown_btn_is_noop(self):
        # Defensive: an unrecognised btn must not raise.
        room = self._make_room("Noop test", 1200)
        room.with_context(btn="bogus").toggle_hotel()
        self.assertFalse(room.hb_dnd)
        self.assertFalse(room.hb_clean)

    def test_user_events_act_returns_action_for_door(self):
        room = self._make_room("Events", 1300)
        action = room.user_events_act()
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get("type"), "ir.actions.act_window")
        self.assertEqual(action.get("res_model"), "hr.rfid.event.user")
