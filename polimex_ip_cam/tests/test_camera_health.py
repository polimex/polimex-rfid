# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytz
import requests

from odoo import fields
from odoo.tests.common import HttpCase, TransactionCase, tagged

from odoo.addons.polimex_ip_cam.helpers.camera_api import HikvisionCamera

_GET = "odoo.addons.polimex_ip_cam.helpers.camera_api.requests.get"


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_health")
class TestCameraHealth(TransactionCase):
    """Classified connection status + plain-language message + last-seen."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.camera = cls.env["cctv.camera"].create({
            "name": "Health Cam", "ip_address": "10.0.0.7",
            "username": "admin", "password": "x",
            "brand": "hikvision", "tz": "Europe/Sofia",
        })

    def test_every_status_has_a_plain_language_message(self):
        for status in ("unknown", "connected", "unreachable", "auth_failed",
                       "protocol_error", "error"):
            self.camera.connection_status = status
            self.assertTrue(self.camera.connection_message,
                            "status %s must yield a message" % status)
        # The failure message is actionable, not raw telemetry/jargon.
        self.camera.connection_status = "auth_failed"
        self.assertIn("password", self.camera.connection_message.lower())

    def test_apply_result_sets_fields_and_last_seen(self):
        before = fields.Datetime.now()
        self.camera._apply_connection_result({"status": "connected"})
        self.assertEqual(self.camera.connection_status, "connected")
        self.assertFalse(self.camera.connection_error_detail)
        self.assertTrue(self.camera.last_seen and self.camera.last_seen >= before)
        # A later failure keeps the raw detail and must NOT bump last_seen.
        seen = self.camera.last_seen
        self.camera._apply_connection_result(
            {"status": "unreachable", "error": "No route to host"})
        self.assertEqual(self.camera.connection_status, "unreachable")
        self.assertIn("No route", self.camera.connection_error_detail)
        self.assertEqual(self.camera.last_seen, seen,
                         "a failure must not update last_seen")

    def test_check_connection_classifies_each_failure(self):
        api = HikvisionCamera("10.0.0.7", 80, "admin", "x")
        with patch(_GET, side_effect=requests.exceptions.ConnectionError("No route to host")):
            self.assertEqual(api.check_connection()["status"], "unreachable")
        with patch(_GET, side_effect=requests.exceptions.Timeout("timed out")):
            self.assertEqual(api.check_connection()["status"], "unreachable")
        with patch(_GET, return_value=MagicMock(status_code=401, text="")):
            self.assertEqual(api.check_connection()["status"], "auth_failed")
        with patch(_GET, return_value=MagicMock(status_code=200, text="<not-xml", content=b"<not-xml")):
            self.assertEqual(api.check_connection()["status"], "protocol_error")


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_clock")
class TestHeartbeatClockSync(HttpCase):
    """Regression: the heartbeat must not loop set_time when the camera reports
    the correct wall-clock with Hikvision's inverted timeZone offset (#1)."""

    _registry_readonly_enabled = False  # the heartbeat queues a DB command

    def _make_camera(self):
        return self.env["cctv.camera"].sudo().create({
            "name": "Clock Cam",
            "ip_address": "127.0.0.1",  # == HttpCase client source -> auth passes
            "username": "admin", "password": "x",
            "brand": "hikvision", "tz": "Europe/Sofia",
        })

    def _post_heartbeat(self, dt_str):
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<EventNotificationAlert>'
            f'<dateTime>{dt_str}</dateTime>'
            '<ipAddress>127.0.0.1</ipAddress>'
            '<eventType>videoloss</eventType>'
            '</EventNotificationAlert>'
        )
        self.url_open(
            "/ipcam/anpr/event",
            files={'heartBeat.xml': ('heartBeat.xml', body, 'application/xml')},
        )

    def _set_time_cmds(self, cam):
        return self.env["cctv.camera.command"].sudo().search([
            ("camera_id", "=", cam.id), ("command_type", "=", "set_time")])

    @staticmethod
    def _sofia_wall():
        cam_tz = pytz.timezone("Europe/Sofia")
        return pytz.utc.localize(fields.Datetime.now()).astimezone(cam_tz)

    def test_inverted_offset_heartbeat_does_not_loop_set_time(self):
        cam = self._make_camera()
        wall = self._sofia_wall()
        off = wall.strftime('%z')  # e.g. '+0300'
        inv = ('-' if off[0] == '+' else '+') + off[1:3] + ':' + off[3:5]
        dt_str = wall.strftime('%Y-%m-%dT%H:%M:%S') + inv  # as Hikvision reports
        self._post_heartbeat(dt_str)
        self.assertFalse(
            self._set_time_cmds(cam),
            "correct wall time with inverted offset must NOT queue set_time")

    def test_real_drift_still_queues_set_time(self):
        cam = self._make_camera()
        drifted = (self._sofia_wall() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S')
        self._post_heartbeat(drifted)
        self.assertTrue(
            self._set_time_cmds(cam),
            "a genuine >5 min drift must still queue a set_time command")
