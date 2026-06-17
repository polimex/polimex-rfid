from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_refresh")
class TestCameraEventCompanyResolution(TransactionCase):
    """A camera-originated system event (unregistered plate) must resolve its
    company through the camera. The synthetic camera door has no webstack, so
    the refresh.mixin company resolver used to short-circuit on the empty
    webstack_id and never reach the door (whose company is the camera's). The
    consequence was not cosmetic: the realtime dashboard refresh was silently
    skipped for every camera system event."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.plate_type = cls.env.ref("hr_rfid.hr_rfid_card_type_8")
        cls.cam = cls.env["cctv.camera"].create({
            "name": "Refresh Cam", "company_id": cls.company.id,
            "ip_address": "10.0.0.50", "port": 80, "username": "admin",
            "password": "x", "tz": "Europe/Sofia",
        })

    def setUp(self):
        super().setUp()
        # The resolver lives on the event model via hr_rfid_refresh_views
        # (auto_install). Skip if that layer is absent from this DB.
        if not hasattr(self.env["hr.rfid.event.system"], "get_company_id"):
            self.skipTest("hr_rfid_refresh_views not installed")

    def _files(self, plate):
        return {"anpr": {
            "ANPR": {
                "licensePlate": plate, "direction": "forward",
                "detectDir": "8", "detectType": "2",
            },
            "dateTime": "2027-01-01T10:00:00+02:00",
            "eventType": "ANPR", "ipAddress": "192.168.74.79",
            "eventState": "active",
        }}

    def test_system_event_resolves_company_via_camera_door(self):
        self.cam.parse_event(self._files("XX0000XX"))
        ev = self.env["hr.rfid.event.system"].search(
            [("camera_id", "=", self.cam.id), ("license_plate", "=", "XX0000XX")],
            order="id desc", limit=1)
        self.assertTrue(ev, "an unregistered plate must create a system event")
        self.assertEqual(
            ev.get_company_id(), self.company,
            "camera system event must resolve the company via the camera door, "
            "not short-circuit to an empty company on the empty webstack_id")

    def test_system_event_create_emits_refresh_notice(self):
        self.company.realtime_refresh = True
        bus_cls = type(self.env["bus.bus"])
        with patch.object(bus_cls, "_sendone") as mock_send:
            self.cam.parse_event(self._files("YY0000YY"))
        sys_calls = [
            c for c in mock_send.call_args_list
            if c.args and c.args[0] == "polimex.hr.rfid.event.system"
        ]
        self.assertTrue(
            sys_calls,
            "creating a camera system event must emit a realtime refresh "
            "notification for the camera's company")
        self.assertEqual(sys_calls[-1].args[2]["company_id"], self.company.id)
