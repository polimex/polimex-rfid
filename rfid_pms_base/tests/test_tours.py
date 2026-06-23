# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "rfid_pms", "rfid_pms_tour")
class TestRfidPmsRoomTours(HttpCase):

    # Required for HttpCase tests that issue DB writes in v19.
    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.access_group_src = cls.env["hr.rfid.access.group"].create({
            "name": "TourAG-Src",
            "company_id": cls.company.id,
        })
        cls.access_group_dst = cls.env["hr.rfid.access.group"].create({
            "name": "TourAG-Dst",
            "company_id": cls.company.id,
        })
        cls.webstack = cls.env["hr.rfid.webstack"].create({
            "name": "TourStack",
            "serial": "TOUR001",
            "company_id": cls.company.id,
            "available": "a",
            "tz": "Europe/Sofia",
            "active": True,
        })
        cls.controller = cls.env["hr.rfid.ctrl"].create({
            "name": "TourCtrl",
            "ctrl_id": 50,
            "webstack_id": cls.webstack.id,
        })
        cls._door_counter = 5000

    @classmethod
    def _make_door(cls, label):
        cls._door_counter += 1
        return cls.env["hr.rfid.door"].create({
            "name": f"TourDoor-{label}",
            "number": cls._door_counter,
            "controller_id": cls.controller.id,
            "company_id": cls.company.id,
        })

    def test_onboarding_panel_tour(self):
        """A new hotelier is greeted by the onboarding banner above the
        rooms kanban and can dismiss it cleanly. No rooms are created so the
        onboarding steps stay open and the banner is shown."""
        self.start_tour(
            "/odoo/action-rfid_pms_base.action_window_room",
            "rfid_pms_base_onboarding_panel_tour",
            login="admin",
        )

    def test_room_kanban_actions_tour(self):
        """User flow: toggle DND, toggle Clean, navigate to user events."""
        self.env["rfid_pms_base.room"].create({
            "name": "Tour-Room-1",
            "number": 5001,
            "company_id": self.company.id,
            "access_group_id": self.access_group_src.id,
            "door_id": self._make_door("kanban-1").id,
        })
        self.start_tour(
            "/odoo/action-rfid_pms_base.action_window_room",
            "rfid_pms_base_kanban_actions_tour",
            login="admin",
        )

    def test_room_move_tour(self):
        """User flow: move the occupant from one room to another."""
        src = self.env["rfid_pms_base.room"].create({
            "name": "Move-Src",
            "number": 5101,
            "company_id": self.company.id,
            "access_group_id": self.access_group_src.id,
            "door_id": self._make_door("move-src").id,
        })
        self.env["rfid_pms_base.room"].create({
            "name": "Move-Dst",
            "number": 5102,
            "company_id": self.company.id,
            "access_group_id": self.access_group_dst.id,
            "door_id": self._make_door("move-dst").id,
        })
        # Populate the source AG with a contact rel so `reservation` resolves
        # and the kanban "Move" button becomes visible.
        parent = self.env["res.partner"].create({"name": "Tour-Parent"})
        guest = self.env["res.partner"].create({
            "name": "Tour-Guest",
            "parent_id": parent.id,
        })
        self.env["hr.rfid.access.group.contact.rel"].create({
            "access_group_id": self.access_group_src.id,
            "contact_id": guest.id,
        })
        src.invalidate_recordset()
        self.assertTrue(src.reservation,
                        "Pre-condition: Move-Src must have a reservation")
        self.start_tour(
            "/odoo/action-rfid_pms_base.action_window_room",
            "rfid_pms_base_room_move_tour",
            login="admin",
        )
