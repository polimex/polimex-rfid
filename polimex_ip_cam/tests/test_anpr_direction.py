from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_direction")
class TestAnprDirection(TransactionCase):
    """Travel direction comes from <direction> INSIDE the <ANPR> block
    (event_info). Reading it from the top level always yielded 'forward', so a
    reverse passage was wrongly booked on the In reader. Confirmed live: the
    camera sends direction='reverse' for a reverse passage (detectDir stays 8)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.plate_type = cls.env.ref("hr_rfid.hr_rfid_card_type_8")
        cls.cam = cls.env["cctv.camera"].create({
            "name": "Dir Cam", "company_id": cls.company.id,
            "ip_address": "10.0.0.40", "port": 80, "username": "admin",
            "password": "x", "tz": "Europe/Sofia",
        })

    def _files(self, plate, direction):
        return {"anpr": {
            "ANPR": {
                "licensePlate": plate, "direction": direction,
                "detectDir": "8", "detectType": "2",
                "barrierGateCtrlType": "1", "confidenceLevel": "90",
            },
            "dateTime": "2027-01-01T10:00:00+02:00",
            "eventType": "ANPR", "ipAddress": "192.168.74.79",
            "macAddress": "aa:bb", "activePostCount": "1", "eventState": "active",
            "carDirectionType": "0",
        }}

    def _card(self, plate):
        partner = self.env["res.partner"].create({"name": "H %s" % plate})
        return self.env["hr.rfid.card"].create({
            "number": plate, "card_type": self.plate_type.id,
            "contact_id": partner.id, "company_id": self.company.id,
        })

    def test_forward_uses_in_reader(self):
        self._card("CA1000AA")
        self.cam.parse_event(self._files("CA1000AA", "forward"))
        ev = self.env["hr.rfid.event.user"].search(
            [("camera_id", "=", self.cam.id), ("license_plate", "=", "CA1000AA")],
            order="id desc", limit=1)
        self.assertTrue(ev)
        self.assertEqual(ev.reader_id, self.cam.reader_ids[0], "forward -> In reader")

    def test_reverse_uses_out_reader(self):
        self._card("CA2000BB")
        self.cam.parse_event(self._files("CA2000BB", "reverse"))
        ev = self.env["hr.rfid.event.user"].search(
            [("camera_id", "=", self.cam.id), ("license_plate", "=", "CA2000BB")],
            order="id desc", limit=1)
        self.assertTrue(ev)
        self.assertEqual(ev.reader_id, self.cam.reader_ids[1],
                         "reverse must book the Out reader, not the In reader")

    def test_system_event_records_real_direction(self):
        # Unregistered plate -> system event; its description must carry the
        # real direction (reverse) read from event_info, not the old default.
        self.cam.parse_event(self._files("ZZ9999ZZ", "reverse"))
        ev = self.env["hr.rfid.event.system"].search(
            [("camera_id", "=", self.cam.id), ("license_plate", "=", "ZZ9999ZZ")],
            order="id desc", limit=1)
        self.assertTrue(ev)
        self.assertIn("reverse", (ev.error_description or ""))


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_direction")
class TestHttpHostUrlToken(TransactionCase):
    """action_set_http_host embeds the camera sub-serial (deviceUUID) in the
    callback URL so every notification carries the camera identity (NAT-proof)."""

    def setUp(self):
        super().setUp()
        self.cam = self.env["cctv.camera"].create({
            "name": "Tok Cam", "company_id": self.env.company.id,
            "ip_address": "10.0.0.41", "port": 80, "username": "admin",
            "password": "x", "sub_serial_number": "GN9163457",
        })

    def test_url_embeds_sub_serial(self):
        captured = {}

        def _set(self_api, config):
            captured["url"] = config.get("url")
            return {"status": "success", "response": "ok"}

        with patch("odoo.addons.polimex_ip_cam.helpers.camera_api.HikvisionCamera.set_http_host",
                   _set):
            self.cam.action_set_http_host()
        self.assertEqual(captured.get("url"), "/ipcam/anpr/event/GN9163457")
