# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "rfid_tour")
class TestHrRfidTours(HttpCase):

    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        admin = cls.env["res.users"].search([("login", "=", "admin")], limit=1)
        admin.write({"lang": "en_US", "tz": "Europe/Sofia"})

        # Hardware seed used by the AG-add-door tour.
        cls.webstack = cls.env["hr.rfid.webstack"].create({
            "name": "AGTour Stack",
            "serial": "AGTOUR00001",
            "company_id": cls.company.id,
            "available": "a",
            "tz": "Europe/Sofia",
            "active": True,
        })
        cls.controller = cls.env["hr.rfid.ctrl"].create({
            "name": "AGTour Controller",
            "ctrl_id": 82,
            "webstack_id": cls.webstack.id,
        })
        cls.door = cls.env["hr.rfid.door"].create({
            "name": "AGTour Door",
            "number": 8201,
            "controller_id": cls.controller.id,
            "company_id": cls.company.id,
        })

        # Owner used by the card-assign tour.
        cls.contact = cls.env["res.partner"].create({
            "name": "CardTour Contact A",
            "company_id": cls.company.id,
        })

    def test_add_webstack_tour(self):
        """Process 1: admin registers a brand-new RFID module."""
        before = self.env["hr.rfid.webstack"].search_count([
            ("serial", "=", "TOURWS9000042"),
        ])
        self.start_tour(
            "/odoo/action-hr_rfid.hr_rfid_webstack_action",
            "hr_rfid_add_webstack_tour",
            login="admin",
        )
        after = self.env["hr.rfid.webstack"].search_count([
            ("serial", "=", "TOURWS9000042"),
        ])
        self.assertEqual(
            after, before + 1,
            "The webstack tour should create exactly one hr.rfid.webstack",
        )
        new_ws = self.env["hr.rfid.webstack"].search([
            ("serial", "=", "TOURWS9000042"),
        ], limit=1)
        # The wizard's onchange seeds a friendly name from the serial.
        self.assertIn("TOURWS9000042", new_ws.name)
        self.assertTrue(new_ws.active)

    def test_realtime_channel_tour(self):
        """Process: an operator enables the real-time channel on a module
        from its form and sees the state flip (button + online field)."""
        self.assertFalse(self.webstack.ws_enabled)
        self.start_tour(
            "/odoo/action-hr_rfid.hr_rfid_webstack_action/%d" % self.webstack.id,
            "hr_rfid_realtime_channel_tour",
            login="admin",
        )
        self.assertTrue(
            self.webstack.ws_enabled,
            "The real-time tour should enable the channel on the module",
        )
        self.assertTrue(
            self.webstack.ws_token,
            "Enabling generates the 128-bit channel token",
        )

    def test_access_group_add_door_tour(self):
        """Process 2: admin creates an Access Group and attaches a door."""
        before = self.env["hr.rfid.access.group"].search_count([
            ("name", "=", "AGTour Lobby Access"),
        ])
        self.start_tour(
            "/odoo/action-hr_rfid.hr_rfid_access_group_action",
            "hr_rfid_access_group_add_door_tour",
            login="admin",
        )
        after = self.env["hr.rfid.access.group"].search_count([
            ("name", "=", "AGTour Lobby Access"),
        ])
        self.assertEqual(
            after, before + 1,
            "The AG tour should create exactly one hr.rfid.access.group",
        )
        new_ag = self.env["hr.rfid.access.group"].search([
            ("name", "=", "AGTour Lobby Access"),
        ], limit=1)
        # door_ids is the AccessGroupDoorRel One2many — verify our seeded
        # door is now attached.
        self.assertIn(self.door, new_ag.door_ids.mapped("door_id"))

    def test_onboarding_panel_tour(self):
        """Process 0: a new admin lands on User Events and is guided by the
        native onboarding banner, then opens a step's action."""
        self.start_tour(
            "/odoo/action-hr_rfid.hr_rfid_event_user_action",
            "hr_rfid_onboarding_panel_tour",
            login="admin",
        )

    def test_card_assign_tour(self):
        """Process 3: admin issues a card to a contact."""
        before = self.env["hr.rfid.card"].search_count([
            ("number", "=", "8000000123"),
        ])
        self.start_tour(
            "/odoo/action-hr_rfid.hr_rfid_card_action",
            "hr_rfid_card_assign_tour",
            login="admin",
        )
        after = self.env["hr.rfid.card"].search_count([
            ("number", "=", "8000000123"),
        ])
        self.assertEqual(
            after, before + 1,
            "The card tour should create exactly one hr.rfid.card",
        )
        new_card = self.env["hr.rfid.card"].search([
            ("number", "=", "8000000123"),
        ], limit=1)
        self.assertEqual(new_card.contact_id, self.contact)
