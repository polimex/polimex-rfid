from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged

from odoo.addons.polimex_ip_cam.helpers.ipcam_discovery import CameraDiscoverer

CANNED = [
    {"ip_address": "192.168.74.76", "brand": "hikvision", "model": "DS-TCG406-E",
     "serial_number": "DS-TCG406-E 20250322AIFX8693470", "mac_address": "e8-a0-ed-30-57-1b",
     "http_port": "88", "activated": True, "discovery_method": "SADP"},
    {"ip_address": "192.168.74.90", "brand": "onvif_generic", "model": "AC-9000",
     "serial_number": "", "http_port": "", "discovery_method": "ONVIF"},
]


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_discovery_tour")
class TestDiscoveryTour(HttpCase):
    """Drives the discover-and-adopt wizard in a real browser. The network probe
    is patched to CANNED results (same process), so the wizard opens populated;
    the tour drops one device and adopts the other into a real camera."""

    _registry_readonly_enabled = False  # the tour creates a camera (DB write)

    def test_discovery_wizard_tour(self):
        with patch.object(CameraDiscoverer, "discover", return_value=CANNED):
            self.start_tour(
                "/odoo/action-polimex_ip_cam.action_cctv_camera_discovery",
                "ipcam_discovery_tour",
                login="admin",
            )
        # sudo(): the wizard-created camera is company-scoped by record rule;
        # mirror the module's HttpCase pattern (test_anpr_auth) to read it back.
        Camera = self.env["cctv.camera"].sudo()
        created = Camera.search([("ip_address", "=", "192.168.74.76")])
        self.assertEqual(len(created), 1, "the kept Hikvision device must be adopted")
        self.assertEqual(created.brand, "hikvision")
        self.assertFalse(
            Camera.search([("ip_address", "=", "192.168.74.90")]),
            "the dropped ONVIF device must NOT be created",
        )
