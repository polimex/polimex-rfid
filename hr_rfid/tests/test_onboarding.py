# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from unittest.mock import patch

from markupsafe import Markup
from psycopg2 import errors as pgerrors

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_onboarding")
class TestOnboardingPanel(TransactionCase):
    """The onboarding banner reuses core's server-rendered panel template."""

    def test_panel_html_renders_core_markup(self):
        html = self.env["onboarding.onboarding"].get_onboarding_panel_html("hr_rfid_setup")
        self.assertIsInstance(
            html, Markup,
            "The panel must be returned as Markup so the OWL banner can inject it safely",
        )
        # Native Odoo onboarding markup (not a hand-rolled copy) is what makes
        # the banner translation- and overflow-safe.
        self.assertIn("o_onboarding_main", html)
        self.assertIn("o_onboarding_step", html)
        # The first step title is rendered server-side (translated).
        self.assertIn("Configure RFID Settings", html)

    def test_panel_html_unknown_route_is_false(self):
        self.assertFalse(
            self.env["onboarding.onboarding"].get_onboarding_panel_html("does_not_exist"),
            "An unknown route must yield no banner, not an error",
        )

    def test_panel_html_hidden_after_close(self):
        Onboarding = self.env["onboarding.onboarding"]
        # Render once so a progress record exists, then close the panel.
        self.assertTrue(Onboarding.get_onboarding_panel_html("hr_rfid_setup"))
        Onboarding.action_close_panel_rfid_setup()
        self.assertFalse(
            Onboarding.get_onboarding_panel_html("hr_rfid_setup"),
            "A closed onboarding panel must not be rendered again",
        )


@tagged("post_install", "-at_install", "rfid_onboarding")
class TestOnboardingPanelFirstLoadRace(TransactionCase):
    """Two users opening the RFID list at the same moment both get the banner.

    The very first load of the panel starts tracking the user's progress.
    When two browser tabs do that in the same instant, only one of them can
    win - the other used to be left without a banner at all (and put two
    scary lines in the customer's log for a situation that is completely
    normal).
    """

    STEP_TITLES = [
        "Configure RFID Settings",
        "Add Hardware Module",
        "Discover Controllers",
        "Create Access Group",
        "Register First Card",
    ]

    def setUp(self):
        super().setUp()
        self.Onboarding = self.env["onboarding.onboarding"]
        self.onboarding = self.env.ref("hr_rfid.onboarding_rfid_setup")
        # Start from a genuine first load: no tracking record yet, so the
        # panel really has to create one.
        self.onboarding.progress_ids.unlink()

    def _assert_full_panel(self, html):
        self.assertIsInstance(
            html, Markup,
            "The panel must be returned as Markup so the OWL banner can inject it safely",
        )
        self.assertIn("o_onboarding_main", html)
        for title in self.STEP_TITLES:
            self.assertIn(
                title, html,
                "Every setup step must be listed on the banner: %s" % title,
            )

    def test_panel_still_shown_when_another_request_wins_the_first_load(self):
        """Losing the first-load race must not cost the user the banner."""
        progress_before = self.env["onboarding.progress"].search_count([])
        progress_steps_before = self.env["onboarding.progress.step"].search_count([])

        def _lose_the_race(records):
            raise pgerrors.UniqueViolation(
                'duplicate key value violates unique constraint '
                '"onboarding_progress__onboarding_company_uniq"'
            )

        with patch.object(type(self.Onboarding), "_create_progress", _lose_the_race):
            html = self.Onboarding.get_onboarding_panel_html("hr_rfid_setup")

        self._assert_full_panel(html)
        self.assertNotIn(
            "o_onboarding_completed_message", html,
            "A panel that has only just been started is not finished",
        )
        self.assertEqual(
            self.env["onboarding.progress"].search_count([]), progress_before,
            "The losing request must not leave a half-created tracking record behind",
        )
        self.assertEqual(
            self.env["onboarding.progress.step"].search_count([]), progress_steps_before,
            "The losing request must not leave orphan step records behind",
        )

    def test_first_load_starts_tracking_exactly_once(self):
        """The winning request tracks progress, and a reload does not duplicate it."""
        self._assert_full_panel(self.Onboarding.get_onboarding_panel_html("hr_rfid_setup"))
        self.assertEqual(
            len(self.onboarding.progress_ids), 1,
            "Opening the panel must start tracking progress",
        )

        self._assert_full_panel(self.Onboarding.get_onboarding_panel_html("hr_rfid_setup"))
        self.assertEqual(
            len(self.onboarding.progress_ids), 1,
            "Reloading the page must reuse the tracking already started",
        )
