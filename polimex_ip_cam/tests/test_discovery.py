from odoo.tests.common import TransactionCase, tagged

from odoo.addons.polimex_ip_cam.helpers.ipcam_discovery import CameraDiscoverer

# Real ProbeMatch payloads captured on site (DS-TCG406-E), trimmed to the fields
# the parsers read. SADP carries the rich identity; ONVIF carries the service URL.
SADP_MATCH = (
    '<?xml version="1.0" encoding="utf-8"?>'
    "<ProbeMatch><Uuid>X</Uuid><Types>inquiry</Types>"
    "<IPv4Address>192.168.74.76</IPv4Address>"
    "<DeviceDescription>DS-TCG406-E</DeviceDescription>"
    "<DeviceSN>DS-TCG406-E 20250322AIFX8693470</DeviceSN>"
    "<MAC>e8-a0-ed-30-57-1b</MAC><CommandPort>8000</CommandPort>"
    "<HttpPort>88</HttpPort><SoftwareVersion>V5.4.5build 260429</SoftwareVersion>"
    "<Activated>true</Activated></ProbeMatch>"
)
SADP_INACTIVE = SADP_MATCH.replace("<Activated>true</Activated>", "<Activated>false</Activated>")

WSD_MATCH_HIK = (
    '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://www.w3.org/2003/05/soap-envelope">'
    "<SOAP-ENV:Body>"
    '<d:ProbeMatches xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery">'
    "<d:ProbeMatch><d:Types>dn:NetworkVideoTransmitter</d:Types>"
    "<d:Scopes>onvif://www.onvif.org/name/HIKVISION "
    "onvif://www.onvif.org/hardware/DS-TCG406-E "
    "onvif://www.onvif.org/Profile/Streaming</d:Scopes>"
    "<d:XAddrs>http://192.168.74.57/onvif/device_service "
    "http://[fe80::eaa0:edff:fe3f:b4f7]/onvif/device_service</d:XAddrs>"
    "</d:ProbeMatch></d:ProbeMatches></SOAP-ENV:Body></SOAP-ENV:Envelope>"
)
WSD_MATCH_GENERIC = (
    WSD_MATCH_HIK.replace("/name/HIKVISION", "/name/AcmeCam")
    .replace("/hardware/DS-TCG406-E", "/hardware/AC-9000")
    .replace("192.168.74.57", "192.168.74.90")
)


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_discovery")
class TestDiscoveryParsers(TransactionCase):
    """The probe parsers are pure — verify they extract the right identity from
    real ProbeMatch payloads and reject anything that is not a match."""

    def test_parse_sadp(self):
        rec = CameraDiscoverer.parse_sadp(SADP_MATCH)
        self.assertEqual(rec["ip_address"], "192.168.74.76")
        self.assertEqual(rec["brand"], "hikvision")
        self.assertEqual(rec["model"], "DS-TCG406-E")
        self.assertEqual(rec["serial_number"], "DS-TCG406-E 20250322AIFX8693470")
        self.assertEqual(rec["mac_address"], "e8-a0-ed-30-57-1b")
        self.assertEqual(rec["http_port"], "88")
        self.assertTrue(rec["activated"])
        self.assertEqual(rec["discovery_method"], "SADP")

    def test_parse_sadp_inactive(self):
        self.assertFalse(CameraDiscoverer.parse_sadp(SADP_INACTIVE)["activated"])

    def test_parse_sadp_rejects_non_match(self):
        self.assertIsNone(CameraDiscoverer.parse_sadp("<html>not sadp</html>"))
        self.assertIsNone(CameraDiscoverer.parse_sadp(b"\x00\x01 binary junk"))

    def test_parse_wsd_hikvision(self):
        rec = CameraDiscoverer.parse_wsd(WSD_MATCH_HIK, src_ip="192.168.74.57")
        self.assertEqual(rec["ip_address"], "192.168.74.57")  # from XAddrs, not link-local
        self.assertEqual(rec["brand"], "hikvision")
        self.assertEqual(rec["model"], "DS-TCG406-E")
        self.assertEqual(rec["onvif_url"], "http://192.168.74.57/onvif/device_service")
        self.assertEqual(rec["discovery_method"], "ONVIF")

    def test_parse_wsd_generic_brand(self):
        rec = CameraDiscoverer.parse_wsd(WSD_MATCH_GENERIC)
        self.assertEqual(rec["brand"], "onvif_generic")
        self.assertEqual(rec["model"], "AC-9000")
        self.assertEqual(rec["ip_address"], "192.168.74.90")

    def test_parse_wsd_rejects_non_match(self):
        self.assertIsNone(CameraDiscoverer.parse_wsd("<not><a>probematch</a></not>"))


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_discovery")
class TestDiscoveryWizard(TransactionCase):
    """The wizard adopts injected discovery results into real cameras. The
    context seam (ipcam_discovery_results) replaces the socket probe so the flow
    is deterministic without cameras on the wire."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.Wizard = cls.env["cctv.camera.discovery"]
        cls.Camera = cls.env["cctv.camera"]

    def _results(self):
        return [
            {"ip_address": "192.168.74.76", "brand": "hikvision",
             "model": "DS-TCG406-E", "serial_number": "DS-TCG406-E 20250322AIFX8693470",
             "mac_address": "e8-a0-ed-30-57-1b", "http_port": "88",
             "activated": True, "discovery_method": "SADP"},
            {"ip_address": "192.168.74.90", "brand": "onvif_generic",
             "model": "AC-9000", "serial_number": "", "http_port": "",
             "discovery_method": "ONVIF"},
        ]

    def _wizard(self, results):
        return self.Wizard.with_context(ipcam_discovery_results=results).create({})

    def test_wizard_lists_and_creates(self):
        wiz = self._wizard(self._results())
        self.assertEqual(len(wiz.found_camera_ids), 2)
        hik = wiz.found_camera_ids.filtered(lambda l: l.brand == "hikvision")
        self.assertEqual(hik.name, "DS-TCG406-E 192.168.74.76")
        self.assertTrue(hik.activated)

        action = wiz.action_create_cameras()
        created = self.Camera.search([("ip_address", "in", ["192.168.74.76", "192.168.74.90"])])
        self.assertEqual(len(created), 2)
        hik_cam = created.filtered(lambda c: c.ip_address == "192.168.74.76")
        self.assertEqual(hik_cam.brand, "hikvision")
        self.assertEqual(hik_cam.model, "DS-TCG406-E")
        self.assertEqual(hik_cam.serial_number, "DS-TCG406-E 20250322AIFX8693470")
        self.assertEqual(hik_cam.port, 88)
        self.assertEqual(action["res_model"], "cctv.camera")
        self.assertEqual(set(action["domain"][0][2]), set(created.ids))

    def test_wizard_names_the_registered_and_adds_only_the_new(self):
        """Операторът вижда КОИ камери вече има, поименно - не джунгла от
        серийни номера (собственикът, дословно: "как да разбера кои камери
        вече сме добавили"). Познатата се показва с името на записа си -
        което е и потвърждение, че е жива в мрежата - но не се добавя
        втори път; само новата е кандидат."""
        registered = self.Camera.create({
            "name": "Бариера ВХОД", "ip_address": "10.9.9.9", "port": 80,
            "username": "admin", "password": "x", "tz": "Europe/Sofia",
            "serial_number": "DS-TCG406-E 20250322AIFX8693470",
        })
        wiz = self._wizard(self._results())
        self.assertEqual(len(wiz.found_camera_ids), 2,
                         'познатата камера е скрита - операторът губи '
                         'потвърждението, че е жива')
        known = wiz.found_camera_ids.filtered(lambda l: l.status == 'known')
        self.assertEqual(known.existing_camera_id, registered)
        self.assertEqual(known.name, 'Бариера ВХОД',
                         'познатият ред не носи бизнес името, а джунглата')
        before = self.Camera.search_count([])
        wiz.action_create_cameras()
        self.assertEqual(
            self.Camera.search_count([]), before + 1,
            'познатата камера е добавена втори път - серийният номер е '
            'идентичността')

    def test_wizard_brand_agnostic(self):
        wiz = self._wizard([self._results()[1]])
        wiz.action_create_cameras()
        cam = self.Camera.search([("ip_address", "=", "192.168.74.90")])
        self.assertEqual(cam.brand, "onvif_generic")

    def test_wizard_rejects_out_of_range_port(self):
        bad = dict(self._results()[0], ip_address="192.168.74.77",
                   serial_number="", http_port="99999")
        self._wizard([bad]).action_create_cameras()
        cam = self.Camera.search([("ip_address", "=", "192.168.74.77")])
        self.assertEqual(cam.port, 80, "an out-of-range discovered port must fall back to default 80")

    def test_wizard_empty_closes(self):
        wiz = self._wizard([])
        self.assertFalse(wiz.found_camera_ids)
        self.assertEqual(wiz.action_create_cameras().get("type"), "ir.actions.act_window_close")
