import json
from datetime import datetime, timedelta

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "rfid_voting")
class TestVotingPublicControllers(HttpCase):
    """End-to-end coverage of the public /voting_display/* endpoints used
    by the kiosk OWL DisplayView component.
    """

    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.display = cls.env["voting.display"].create({
            "name": "Test Display",
            "company_id": cls.env.company.id,
        })
        cls.access_token = cls.display.access_token
        cls.short_code = cls.display.short_code
        cls.participant_group = cls.env["voting.participants"].create({
            "name": "Test Board",
            "company_id": cls.env.company.id,
        })
        today_start = datetime.combine(datetime.today(), datetime.min.time())
        cls.open_session = cls.env["voting.session"].create({
            "name": "Budget approval",
            "display_id": cls.display.id,
            "participant_group_id": cls.participant_group.id,
            "company_id": cls.env.company.id,
            "state": "open",
            "planned_date": today_start.date(),
            "start_datetime": today_start,
            "end_datetime": today_start + timedelta(minutes=5),
            "voting_time": 300,
        })
        cls.closed_session = cls.env["voting.session"].create({
            "name": "Old motion",
            "display_id": cls.display.id,
            "participant_group_id": cls.participant_group.id,
            "company_id": cls.env.company.id,
            "state": "closed",
            "planned_date": (today_start - timedelta(days=1)).date(),
            "start_datetime": today_start - timedelta(days=1),
            "end_datetime": today_start - timedelta(days=1) + timedelta(minutes=5),
        })

    # ---- /voting_display/<short_code>/voting ----

    def test_voting_main_returns_kiosk_html(self):
        response = self.url_open(f"/voting_display/{self.short_code}/voting")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("Content-Type", ""))

    def test_voting_main_unknown_short_code_returns_404(self):
        response = self.url_open("/voting_display/does-not-exist/voting")
        self.assertEqual(response.status_code, 404)

    # ---- /voting_display/<token>/get_existing_sessions ----

    def _jsonrpc(self, url, params=None):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params or {},
            "id": 1,
        }
        return self.url_open(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

    def test_get_existing_sessions_returns_only_today(self):
        response = self._jsonrpc(
            f"/voting_display/{self.access_token}/get_existing_sessions"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("result", data)
        names = [s["name"] for s in data["result"]]
        self.assertIn("Budget approval", names)
        self.assertNotIn("Old motion", names, "Sessions from prior days must not leak")

    def test_get_existing_sessions_invalid_token_returns_404(self):
        response = self._jsonrpc(
            "/voting_display/invalid-token-1234/get_existing_sessions"
        )
        # JSON-RPC controllers wrap NotFound exceptions; an HTTP 404 is acceptable
        # but Odoo also surfaces it as a JSON error object. Accept both.
        if response.status_code == 200:
            data = response.json()
            self.assertIn("error", data)
        else:
            self.assertEqual(response.status_code, 404)

    # ---- /voting_display/<token>/session/<id>/close ----

    def test_session_close_persists_state(self):
        # voting_session.write enforces "no closing without votes" — feed at
        # least one vote so the close transition is allowed.
        voter = self.env["res.partner"].create({"name": "Voter A"})
        item = self.env["voting.item"].create({"name": "Item 1"})
        self.open_session.write({"item_ids": [(4, item.id)]})
        self.env["voting.vote"].create({
            "voting_session_id": self.open_session.id,
            "voting_item_id": item.id,
            "voter_id": voter.id,
            "vote": "yes",
        })

        response = self._jsonrpc(
            f"/voting_display/{self.access_token}/session/{self.open_session.id}/close",
            params={"state": "closed"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("error", body, f"JSON-RPC error: {body.get('error')}")
        self.open_session.invalidate_recordset()
        self.assertEqual(self.open_session.state, "closed")
        self.assertIsNotNone(self.open_session.end_datetime)

    def test_session_close_unknown_session_returns_404(self):
        response = self._jsonrpc(
            f"/voting_display/{self.access_token}/session/9999999/close",
            params={"state": "closed"},
        )
        if response.status_code == 200:
            data = response.json()
            self.assertIn("error", data)
        else:
            self.assertEqual(response.status_code, 404)
