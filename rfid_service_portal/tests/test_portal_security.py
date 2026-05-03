# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Regression test for the /my/rfid_services portal route.

Earlier the route was declared auth='public' with a defensive guard
that never fired (request.env.user is always a User record under
auth='public' — it's the public user). This locked anonymous visitors
out only nominally; they could still hit the endpoint and the
controller would search rfid.service.sale records linked to the public
partner.

The fix flipped the route to auth='user'. This test asserts that an
anonymous visit is now redirected to the login page, while an
authenticated portal user gets a 200 OK.
"""
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "rfid_service_portal_security")
class TestRfidServicePortalSecurity(HttpCase):
    _registry_readonly_enabled = False

    def test_anonymous_visit_is_blocked(self):
        """Hitting /my/rfid_services anonymously must NOT return 200 with
        portal content — auth='user' redirects the visitor through the
        login flow."""
        response = self.url_open("/my/rfid_services", allow_redirects=False)
        # Odoo redirects anonymous portal hits to /web/login (302 or 303).
        self.assertIn(response.status_code, (301, 302, 303),
                      f"Expected redirect, got {response.status_code}")
        location = response.headers.get("Location", "")
        self.assertTrue(
            "/web/login" in location or "/odoo" in location,
            f"Expected redirect to login, got Location={location!r}",
        )

    def test_authenticated_user_can_visit(self):
        """An authenticated portal user must receive the listing page
        (or at least a 200 — empty list is fine)."""
        # admin is authenticated and has permissions to list services.
        self.authenticate("admin", "admin")
        response = self.url_open("/my/rfid_services")
        self.assertEqual(response.status_code, 200)
