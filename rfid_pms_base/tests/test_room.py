# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Backend tests for rfid_pms_base — basic CRUD and the move-customers
wizard whose v18 domain syntax (filtering on a non-stored field) was
the original blocker for the v19 install.
"""
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
        # rfid_pms_base.room requires a door — build a minimal hardware
        # stack: webstack → controller → doors.
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
        """SQL constraint 'unique(number)' is global — not per-group."""
        from odoo.tools import mute_logger
        self._make_room("Room A", 300, group="Floor 3")
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Exception):
                self._make_room("Room B", 300, group="Floor 4")

    def test_room_number_must_be_within_range(self):
        """_check_number rejects numbers outside [1, 65535]."""
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self._make_room("Out of range", 70000)

    def test_reservation_is_empty_when_no_contacts(self):
        room = self._make_room("Empty", 500)
        self.assertFalse(room.reservation,
                         "A room with no AG contacts must report no reservation")

    # ==================================================================
    # Move wizard — covers the v18→v19 domain fix
    # ==================================================================

    def test_room_move_wiz_lists_only_free_rooms(self):
        """Regression: the v18 helper used SQL domain on the non-stored
        compute field 'reservation' and crashed in v19. The v19 fix
        materialises the candidate set in Python. We exercise the
        helper at the model layer because room_to_id is required."""
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
