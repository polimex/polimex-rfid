# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from markupsafe import Markup

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
