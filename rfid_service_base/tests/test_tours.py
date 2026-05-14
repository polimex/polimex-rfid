# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "rfid_service", "rfid_service_tour")
class TestRfidServiceTours(HttpCase):

    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # Force English UI so the tour's text-based selectors (e.g. the
        # "Sale RFID Service" action menu entry) match irrespective of the
        # DB's default language (workflow rule 8 — language-agnostic).
        en = cls.env.ref("base.lang_en")
        if not en.active:
            en.active = True
        # start_tour() logs in as login="admin" — switch THAT user's lang
        # and timezone (the wizard's onchange does pytz.timezone(user.tz)).
        admin = cls.env["res.users"].search([("login", "=", "admin")], limit=1)
        admin.write({"lang": "en_US", "tz": "Europe/Sofia"})
        cls.partner_parent = cls.env["res.partner"].create({
            "name": "Tour Visitors Parent",
            "is_company": True,
        })

        cls.webstack = cls.env["hr.rfid.webstack"].create({
            "name": "TourSvcStack",
            "serial": "TOURSVC001",
            "company_id": cls.company.id,
            "available": "a",
            "tz": "Europe/Sofia",
            "active": True,
        })
        cls.controller = cls.env["hr.rfid.ctrl"].create({
            "name": "TourSvcCtrl",
            "ctrl_id": 80,
            "webstack_id": cls.webstack.id,
        })
        cls.door = cls.env["hr.rfid.door"].create({
            "name": "TourSvcDoor",
            "number": 8001,
            "controller_id": cls.controller.id,
            "company_id": cls.company.id,
        })
        cls.access_group = cls.env["hr.rfid.access.group"].create({
            "name": "TourSvcAG",
            "company_id": cls.company.id,
        })
        # An AG needs at least one door for write_card to succeed.
        cls.access_group.write({
            "door_ids": [(0, 0, {"door_id": cls.door.id})],
        })
        cls.service = cls.env["rfid.service"].create({
            "name": "Tour Day Pass",
            "company_id": cls.company.id,
            "parent_id": cls.partner_parent.id,
            "service_type": "time_count",
            "visits": "1",
            "card_type": cls.env.ref("hr_rfid.hr_rfid_card_type_barcode").id,
            "time_interval_number": 4,
            "time_interval_type": "hours",
            "time_interval_start": 8.0,
            "time_interval_end": 18.0,
            "access_group_id": cls.access_group.id,
        })

    def test_issue_visitor_card_tour(self):
        """Golden-path tour: open Services, pick the seeded service,
        run the Sale wizard, encode a card, and verify the resulting
        rfid.service.sale was created."""
        before_count = self.env["rfid.service.sale"].search_count([
            ("service_id", "=", self.service.id),
        ])

        self.start_tour(
            "/odoo/action-rfid_service_base.hr_rfid_service_action",
            "rfid_service_base_issue_visitor_card_tour",
            login="admin",
        )

        after_count = self.env["rfid.service.sale"].search_count([
            ("service_id", "=", self.service.id),
        ])
        self.assertEqual(
            after_count, before_count + 1,
            "Exactly one new rfid.service.sale should have been created",
        )
        new_sale = self.env["rfid.service.sale"].search([
            ("service_id", "=", self.service.id),
        ], order="id desc", limit=1)
        # Card number is zero-padded by write_card to 10 digits.
        self.assertTrue(new_sale.card_id)
        self.assertEqual(new_sale.card_id.number, "9000000042".zfill(10))
