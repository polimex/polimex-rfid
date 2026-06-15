import xml.etree.ElementTree as ET
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.polimex_ip_cam.helpers.camera_api import HikvisionCamera

NS = {"ns": "http://www.isapi.org/ver20/XMLSchema"}

# A realistic capabilities document as returned by
# GET /ISAPI/Event/notification/httpHosts/capabilities on a DS-TCG406-E:
# the heartbeat range is advertised as [0, 180].
CAPABILITIES_XML = (
    '<HttpHostNotificationCap version="2.0" '
    'xmlns="http://www.isapi.org/ver20/XMLSchema">'
    '<id min="1" max="1"/>'
    '<SubscribeEvent>'
    '<heartbeat min="0" max="180">20</heartbeat>'
    '<eventMode opt="all,alarm,none"/>'
    '</SubscribeEvent>'
    '</HttpHostNotificationCap>'
)

# A realistic current-configuration document as returned by
# GET /ISAPI/Event/notification/httpHosts/1. Note it carries the
# <checkResponseEnabled> element that the module never used to emit, plus a
# stale heartbeat of 3600 that our write must overwrite.
CURRENT_HTTP_HOST_XML = (
    '<HttpHostNotification version="2.0" '
    'xmlns="http://www.isapi.org/ver20/XMLSchema">'
    "<id>1</id>"
    "<url>/</url>"
    "<protocolType>HTTP</protocolType>"
    "<parameterFormatType>XML</parameterFormatType>"
    "<addressingFormatType>ipaddress</addressingFormatType>"
    "<ipAddress>0.0.0.0</ipAddress>"
    "<portNo>80</portNo>"
    "<userName></userName>"
    "<httpAuthenticationMethod>none</httpAuthenticationMethod>"
    "<ANPR><detectionUpLoadPicturesType>all</detectionUpLoadPicturesType></ANPR>"
    "<SubscribeEvent><heartbeat>3600</heartbeat><eventMode>all</eventMode></SubscribeEvent>"
    "<checkResponseEnabled>true</checkResponseEnabled>"
    "<enabled>false</enabled>"
    "</HttpHostNotification>"
)


class _FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text
        self.content = text.encode("utf-8")


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_http_host")
class TestHeartbeatClamp(TransactionCase):
    """Pure-logic coverage for heartbeat clamping and capabilities parsing."""

    def test_clamp_above_max_returns_max(self):
        self.assertEqual(HikvisionCamera._clamp_heartbeat(3600, 0, 180), 180)

    def test_clamp_below_min_returns_min(self):
        self.assertEqual(HikvisionCamera._clamp_heartbeat(-5, 0, 180), 0)

    def test_clamp_within_range_is_unchanged(self):
        self.assertEqual(HikvisionCamera._clamp_heartbeat(30, 0, 180), 30)

    def test_clamp_non_numeric_uses_default(self):
        # An unparseable value must collapse to the safe default (30), which is
        # within [0, 180] and therefore returned unchanged.
        self.assertEqual(HikvisionCamera._clamp_heartbeat("abc", 0, 180), 30)

    def test_clamp_none_default_then_clamped_up_to_min(self):
        # None -> default 30, but the camera's min is 60, so it clamps up.
        self.assertEqual(HikvisionCamera._clamp_heartbeat(None, 60, 180), 60)

    def test_parse_capabilities_reads_min_max(self):
        self.assertEqual(
            HikvisionCamera._parse_heartbeat_capabilities(CAPABILITIES_XML),
            {"min": 0, "max": 180},
        )

    def test_parse_capabilities_missing_element_returns_none(self):
        xml = (
            '<HttpHostNotificationCap version="2.0" '
            'xmlns="http://www.isapi.org/ver20/XMLSchema"><id min="1" max="1"/>'
            "</HttpHostNotificationCap>"
        )
        self.assertIsNone(HikvisionCamera._parse_heartbeat_capabilities(xml))

    def test_parse_capabilities_missing_attrs_returns_none(self):
        xml = (
            '<HttpHostNotificationCap version="2.0" '
            'xmlns="http://www.isapi.org/ver20/XMLSchema"><SubscribeEvent>'
            "<heartbeat>20</heartbeat></SubscribeEvent></HttpHostNotificationCap>"
        )
        self.assertIsNone(HikvisionCamera._parse_heartbeat_capabilities(xml))


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_http_host")
class TestSetHttpHostBuild(TransactionCase):
    """Behavioural coverage for set_http_host read-modify-write + clamping."""

    def setUp(self):
        super().setUp()
        self.cam = HikvisionCamera("10.0.0.10", 80, "admin", "x")

    @staticmethod
    def _dispatch_get(capabilities=None, current=None):
        """Return a requests.get side_effect that answers by URL."""

        def _get(url, *args, **kwargs):
            if url.endswith("/httpHosts/capabilities"):
                return capabilities if capabilities is not None else _FakeResponse(404, "")
            if url.endswith("/httpHosts/1"):
                return current if current is not None else _FakeResponse(404, "")
            return _FakeResponse(404, "")

        return _get

    def _run_set(self, get_side_effect):
        captured = {}

        def _put(url, *args, **kwargs):
            captured["url"] = url
            captured["data"] = kwargs.get("data")
            return _FakeResponse(200, "<ResponseStatus><statusCode>1</statusCode></ResponseStatus>")

        with patch("odoo.addons.polimex_ip_cam.helpers.camera_api.requests.get",
                   side_effect=get_side_effect), \
             patch("odoo.addons.polimex_ip_cam.helpers.camera_api.requests.put",
                   side_effect=_put):
            result = self.cam.set_http_host({"SubscribeEvent": {"heartbeat": "3600", "eventMode": "all"}})
        return result, captured

    def test_clamps_heartbeat_and_preserves_check_response(self):
        result, captured = self._run_set(self._dispatch_get(
            capabilities=_FakeResponse(200, CAPABILITIES_XML),
            current=_FakeResponse(200, CURRENT_HTTP_HOST_XML),
        ))
        self.assertEqual(result.get("status"), "success")
        body = captured["data"]
        self.assertIsNotNone(body, "a PUT body must have been sent")
        body_text = body.decode("utf-8") if isinstance(body, bytes) else body
        # No raw ns0: prefixes must leak into the wire format.
        self.assertNotIn("ns0:", body_text)
        root = ET.fromstring(body_text)
        hb = root.findtext("ns:SubscribeEvent/ns:heartbeat", namespaces=NS)
        self.assertEqual(hb, "180", "3600 must be clamped down to the camera max")
        # checkResponseEnabled from the GET document must be preserved.
        self.assertEqual(
            root.findtext("ns:checkResponseEnabled", namespaces=NS), "true",
            "checkResponseEnabled returned by GET must be preserved in the PUT",
        )

    def test_capabilities_unreadable_uses_conservative_cap(self):
        result, captured = self._run_set(self._dispatch_get(
            capabilities=_FakeResponse(400, ""),
            current=_FakeResponse(200, CURRENT_HTTP_HOST_XML),
        ))
        self.assertEqual(result.get("status"), "success")
        body_text = captured["data"].decode("utf-8")
        root = ET.fromstring(body_text)
        hb = root.findtext("ns:SubscribeEvent/ns:heartbeat", namespaces=NS)
        self.assertEqual(hb, "180", "without capabilities, fall back to the 180 conservative cap")

    def test_current_get_fails_falls_back_to_rebuild(self):
        result, captured = self._run_set(self._dispatch_get(
            capabilities=_FakeResponse(200, CAPABILITIES_XML),
            current=_FakeResponse(404, ""),
        ))
        self.assertEqual(result.get("status"), "success")
        body_text = captured["data"].decode("utf-8")
        self.assertNotIn("ns0:", body_text)
        root = ET.fromstring(body_text)
        # Rebuild path: heartbeat still clamped (3600 -> 180), document well-formed.
        hb = root.findtext("ns:SubscribeEvent/ns:heartbeat", namespaces=NS)
        self.assertEqual(hb, "180")
        # Without a GET base we cannot preserve checkResponseEnabled; the PUT
        # must still succeed without it (camera accepts the document).
        self.assertIsNone(root.findtext("ns:checkResponseEnabled", namespaces=NS))

    def test_config_check_response_overrides_camera_value(self):
        # An explicit checkResponseEnabled in config (e.g. edited in
        # server_setup) must win over the value read from the camera.
        captured = {}

        def _put(url, *args, **kwargs):
            captured["data"] = kwargs.get("data")
            return _FakeResponse(200, "<ResponseStatus><statusCode>1</statusCode></ResponseStatus>")

        get_side_effect = self._dispatch_get(
            capabilities=_FakeResponse(200, CAPABILITIES_XML),
            current=_FakeResponse(200, CURRENT_HTTP_HOST_XML),  # camera says "true"
        )
        with patch("odoo.addons.polimex_ip_cam.helpers.camera_api.requests.get",
                   side_effect=get_side_effect), \
             patch("odoo.addons.polimex_ip_cam.helpers.camera_api.requests.put",
                   side_effect=_put):
            self.cam.set_http_host({
                "SubscribeEvent": {"heartbeat": "30"},
                "checkResponseEnabled": "false",
            })
        root = ET.fromstring(captured["data"].decode("utf-8"))
        self.assertEqual(root.findtext("ns:checkResponseEnabled", namespaces=NS), "false")


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_http_host")
class TestGetHttpHost(TransactionCase):
    """get_http_host must surface checkResponseEnabled so it round-trips."""

    def setUp(self):
        super().setUp()
        self.cam = HikvisionCamera("10.0.0.10", 80, "admin", "x")

    def test_get_http_host_parses_check_response_enabled(self):
        def _get(url, *args, **kwargs):
            return _FakeResponse(200, CURRENT_HTTP_HOST_XML)

        with patch("odoo.addons.polimex_ip_cam.helpers.camera_api.requests.get",
                   side_effect=_get):
            result = self.cam.get_http_host()
        self.assertEqual(result.get("status"), "success")
        self.assertEqual(result["response"].get("checkResponseEnabled"), "true")
