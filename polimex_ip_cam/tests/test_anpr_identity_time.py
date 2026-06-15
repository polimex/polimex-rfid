from odoo.tests.common import TransactionCase, tagged

from odoo.addons.polimex_ip_cam.controllers.anpr_controller import _hikvision_timezone


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_anpr")
class TestHikvisionTimezone(TransactionCase):
    """Hikvision uses the POSIX/inverted sign for the timeZone string."""

    def test_positive_offset_is_inverted(self):
        # UTC+3 must be sent as GMT-03:00, else the camera applies UTC-3 and
        # loops set_time forever.
        self.assertEqual(_hikvision_timezone("+0300"), "GMT-03:00")

    def test_negative_offset_is_inverted(self):
        self.assertEqual(_hikvision_timezone("-0500"), "GMT+05:00")

    def test_half_hour_offset(self):
        self.assertEqual(_hikvision_timezone("+0545"), "GMT-05:45")

    def test_utc_and_empty(self):
        self.assertEqual(_hikvision_timezone("+0000"), "GMT-00:00")
        # Defensive: a missing/garbage offset must not raise.
        self.assertEqual(_hikvision_timezone(""), "GMT-00:00")


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_anpr")
class TestResolveAnprCamera(TransactionCase):
    """cctv.camera._resolve_anpr_camera maps an ANPR event to its camera by
    the stored subSerialNumber (deviceUUID), with legacy-serial and
    trusted-source-IP fallbacks."""

    def _make_camera(self, name, ip, serial=False, sub=False):
        return self.env["cctv.camera"].create({
            "name": name,
            "company_id": self.env.company.id,
            "ip_address": ip,
            "port": 80,
            "username": "admin",
            "password": "x",
            "serial_number": serial,
            "sub_serial_number": sub,
        })

    def test_match_by_sub_serial(self):
        cam = self._make_camera("Cam-A", "10.0.0.1", serial="DS-TCG406-E 20260120AIGN9163457", sub="GN9163457")
        found = self.env["cctv.camera"]._resolve_anpr_camera("GN9163457", "9.9.9.9", True)
        self.assertEqual(found, cam)

    def test_legacy_match_by_full_serial(self):
        # Firmwares whose deviceUUID equals the full serial (no sub stored yet).
        cam = self._make_camera("Cam-B", "10.0.0.2", serial="DS-TCG406-E 20240308AIFA9951877")
        found = self.env["cctv.camera"]._resolve_anpr_camera("DS-TCG406-E 20240308AIFA9951877", "9.9.9.9", True)
        self.assertEqual(found, cam)

    def test_match_by_trusted_ip_learns_uuid(self):
        cam = self._make_camera("Cam-C", "192.168.74.57")  # no serial/sub yet
        self.assertFalse(cam.sub_serial_number)
        found = self.env["cctv.camera"]._resolve_anpr_camera("GN9163457", "192.168.74.57", True)
        self.assertEqual(found, cam)
        self.assertEqual(cam.sub_serial_number, "GN9163457",
                         "the deviceUUID must be learned and stored on first trusted-IP event")

    def test_no_ip_fallback_when_source_verify_off(self):
        # When source verification is OFF the source IP is untrusted, so it must
        # NOT be used to identify the camera; only the body deviceUUID may match.
        self._make_camera("Cam-D", "192.168.74.57")
        found = self.env["cctv.camera"]._resolve_anpr_camera("UNKNOWNUUID", "192.168.74.57", False)
        self.assertFalse(found)

    def test_no_match_returns_empty(self):
        self._make_camera("Cam-E", "10.0.0.5", sub="AAA")
        found = self.env["cctv.camera"]._resolve_anpr_camera("ZZZ", "8.8.8.8", True)
        self.assertFalse(found)

    def test_ambiguous_sub_serial_refuses_to_guess(self):
        # Two cameras sharing a sub-serial must NOT be silently guessed — the
        # event would otherwise be booked against the wrong camera/company.
        self._make_camera("Dup-1", "10.0.0.8", sub="DUP123")
        self._make_camera("Dup-2", "10.0.0.9", sub="DUP123")
        found = self.env["cctv.camera"]._resolve_anpr_camera("DUP123", "9.9.9.9", True)
        self.assertFalse(found, "an ambiguous sub-serial must resolve to nothing")
