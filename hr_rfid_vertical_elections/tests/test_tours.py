# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "voting_tour")
class TestVotingTours(HttpCase):

    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        admin = cls.env["res.users"].search([("login", "=", "admin")], limit=1)
        admin.write({"lang": "en_US", "tz": "Europe/Sofia"})

        # Hardware seed (participants.terminal_ids requires hr.rfid.door).
        cls.webstack = cls.env["hr.rfid.webstack"].create({
            "name": "VoteTourStack",
            "serial": "VOTETOUR01",
            "company_id": cls.company.id,
            "available": "a",
            "tz": "Europe/Sofia",
            "active": True,
        })
        cls.controller = cls.env["hr.rfid.ctrl"].create({
            "name": "VoteTourCtrl",
            "ctrl_id": 81,
            "webstack_id": cls.webstack.id,
        })
        cls.door = cls.env["hr.rfid.door"].create({
            "name": "VoteTourTerminal",
            "number": 8101,
            "controller_id": cls.controller.id,
            "company_id": cls.company.id,
        })

        cls.voter = cls.env["res.partner"].create({
            "name": "Tour Voter A",
            "company_id": cls.company.id,
        })

        # Seeds for the session-lifecycle tour.
        cls.display = cls.env["voting.display"].create({
            "name": "Tour Kiosk",
            "company_id": cls.company.id,
        })
        cls.participants = cls.env["voting.participants"].create({
            "name": "VoteTour Voters",
            "company_id": cls.company.id,
            "participant_ids": [(6, 0, [cls.voter.id])],
            "terminal_ids": [(6, 0, [cls.door.id])],
        })
        cls.item = cls.env["voting.item"].create({
            "name": "VoteTour Question",
            "short_description": "Should we ship it?",
            "company_id": cls.company.id,
        })

    def test_create_display_tour(self):
        """Process 1: admin creates a fresh voting display from scratch."""
        before = self.env["voting.display"].search_count([
            ("name", "=", "Tour Polling Kiosk"),
        ])
        self.start_tour(
            "/odoo/action-hr_rfid_vertical_elections.voting_display_action",
            "elections_create_display_tour",
            login="admin",
        )
        after = self.env["voting.display"].search_count([
            ("name", "=", "Tour Polling Kiosk"),
        ])
        self.assertEqual(
            after, before + 1,
            "The display tour should create exactly one voting.display",
        )
        new_display = self.env["voting.display"].search([
            ("name", "=", "Tour Polling Kiosk"),
        ], limit=1)
        # Defaults auto-fill short_code + access_token + display_url.
        self.assertTrue(new_display.short_code)
        self.assertTrue(new_display.access_token)

    def test_session_lifecycle_tour(self):
        """Process 2: admin creates a session and opens voting.

        Closing without votes resets the session to draft (legacy
        voting_session.write() override), so the tour only covers
        draft → open. Closed/revoted lifecycle is exercised by
        controller-level tests.
        """
        before = self.env["voting.session"].search_count([
            ("name", "=", "Tour Board Meeting Vote"),
        ])
        self.start_tour(
            "/odoo/action-hr_rfid_vertical_elections.vote_session_action",
            "elections_session_lifecycle_tour",
            login="admin",
        )
        after = self.env["voting.session"].search_count([
            ("name", "=", "Tour Board Meeting Vote"),
        ])
        self.assertEqual(
            after, before + 1,
            "The session-lifecycle tour should create exactly one voting.session",
        )
        new_session = self.env["voting.session"].search([
            ("name", "=", "Tour Board Meeting Vote"),
        ], limit=1)
        self.assertEqual(new_session.state, "open")
        self.assertTrue(new_session.start_datetime)
        self.assertEqual(new_session.display_id, self.display)
        self.assertEqual(new_session.participant_group_id, self.participants)
        self.assertIn(self.item, new_session.item_ids)
