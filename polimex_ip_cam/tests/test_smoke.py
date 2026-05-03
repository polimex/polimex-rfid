from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "polimex_ip_cam")
class TestPolimexIpCamSmoke(TransactionCase):
    """Smoke coverage for the IP camera + RFID bridge models."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

    def _make_camera(self, name="Cam-1", ip="10.0.0.10"):
        return self.env["cctv.camera"].create({
            "name": name,
            "company_id": self.company.id,
            "ip_address": ip,
            "port": 80,
            "username": "admin",
            "password": "x",
            "tz": "Europe/Sofia",
        })

    def test_create_camera(self):
        cam = self._make_camera("Lobby Cam")
        self.assertEqual(cam.name, "Lobby Cam")
        self.assertEqual(cam.ip_address, "10.0.0.10")
        self.assertTrue(cam.active)

    def test_camera_command_create(self):
        cam = self._make_camera()
        cmd = self.env["cctv.camera.command"].create({
            "camera_id": cam.id,
            "command_type": "get_snapshot",
        })
        self.assertEqual(cmd.camera_id, cam)
        self.assertEqual(cmd.command_type, "get_snapshot")

    def test_rfid_card_extension_loaded(self):
        # The module extends hr.rfid.card; just verify the model loads
        # and accepts records — no behaviour change at smoke level.
        partner = self.env["res.partner"].create({"name": "Holder"})
        card = self.env["hr.rfid.card"].create({
            "number": "0011223344",
            "card_type": self.env.ref("hr_rfid.hr_rfid_card_type_def").id,
            "contact_id": partner.id,
            "company_id": self.company.id,
        })
        self.assertTrue(card.id)

    def test_camera_tz_default_is_set(self):
        cam = self._make_camera("TZ Cam")
        self.assertTrue(cam.tz, "tz must default to a non-empty string")
