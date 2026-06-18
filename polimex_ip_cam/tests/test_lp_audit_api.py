import json

from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.polimex_ip_cam.helpers import camera_api
from odoo.addons.polimex_ip_cam.helpers.camera_api import (
    HikvisionCamera, LP_DEFAULT_START_TIME, LP_DEFAULT_END_TIME,
)


class _Resp:
    def __init__(self, status_code=200, text="", content=b""):
        self.status_code = status_code
        self.text = text
        self.content = content or text.encode("utf-8")


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_lpaudit")
class TestLpRecordBody(TransactionCase):
    """The LP-audit list upsert is a JSON record (licensePlateAuditData/record),
    confirmed against the camera web-UI traffic. listType maps to
    allowList/blockList and a plate without an explicit validity window gets a
    permanent createTime/effectiveTime window."""

    def test_listtype_and_plate_mapping(self):
        allow = HikvisionCamera._lp_record_info({"plateNum": "CA1234AB", "listType": "0"})
        block = HikvisionCamera._lp_record_info({"plateNum": "CA5678CD", "listType": "1"})
        self.assertEqual(allow["LicensePlate"], "CA1234AB")
        self.assertEqual(allow["listType"], "allowList")   # 0 -> whitelist
        self.assertEqual(block["listType"], "blockList")   # 1 -> blacklist

    def test_default_validity_window(self):
        info = HikvisionCamera._lp_record_info({"plateNum": "CA0002BB", "listType": "0"})
        self.assertEqual(info["createTime"], LP_DEFAULT_START_TIME)
        self.assertEqual(info["effectiveTime"], LP_DEFAULT_END_TIME)
        self.assertTrue(info["effectiveTime"], "effectiveTime must be non-empty")

    def test_cardno_and_times_passthrough(self):
        info = HikvisionCamera._lp_record_info({
            "plateNum": "CA0001AA", "listType": "0", "cardNo": "12345",
            "startTime": "2026-06-16T15:00:00", "endTime": "2099-12-31T23:59:59",
        })
        self.assertEqual(info["cardNo"], "12345")
        self.assertEqual(info["cardID"], "12345")
        self.assertEqual(info["createTime"], "2026-06-16T15:00:00")
        self.assertEqual(info["effectiveTime"], "2099-12-31T23:59:59")


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_lpaudit")
class TestLpAuditRouting(TransactionCase):
    """add/delete route to the VCL API on cameras that support it, and to the
    newer LP-audit JSON API (record upsert / DelLicensePlateAuditData)
    otherwise."""

    def setUp(self):
        super().setUp()
        self.cam = HikvisionCamera("10.0.0.30", 80, "admin", "x")

    def _vcl_caps(self, supported):
        # VCL/capabilities returns 200 on VCL-capable cameras, statusCode-4
        # notSupport (HTTP 403) on the newer LP-audit firmware.
        if supported:
            return _Resp(200, "<VCLCap/>")
        return _Resp(403, "<ResponseStatus><statusCode>4</statusCode>"
                          "<subStatusCode>notSupport</subStatusCode></ResponseStatus>")

    def test_add_uses_lp_audit_record_when_vcl_unsupported(self):
        captured = {}

        def _put(url, *a, **k):
            captured["url"] = url
            captured["data"] = k.get("data")
            captured["headers"] = k.get("headers")
            return _Resp(200, '{"statusCode":1,"statusString":"OK"}')

        with patch.object(camera_api.requests, "get", side_effect=lambda *a, **k: self._vcl_caps(False)), \
             patch.object(camera_api.requests, "put", side_effect=_put):
            res = self.cam.add_plate_to_list([{"plateNum": "CA9999XX", "listType": "0"}])
        self.assertEqual(res.get("status"), "success")
        self.assertIn("/licensePlateAuditData/record", captured["url"])
        self.assertIn("format=json", captured["url"])
        self.assertEqual(captured["headers"]["Content-Type"], "application/json")
        payload = json.loads(captured["data"])
        info = payload["LicensePlateInfoList"][0]
        self.assertEqual(info["LicensePlate"], "CA9999XX")
        self.assertEqual(info["listType"], "allowList")

    def test_add_reports_failure_on_non_success_status(self):
        # 200 with statusCode != 1 means the camera rejected the record — that
        # must NOT be reported as success, or a plate the camera never stored
        # would be marked done in Odoo.
        def _put(url, *a, **k):
            return _Resp(200, '{"statusCode":6,"statusString":"Invalid Content"}')

        with patch.object(camera_api.requests, "get", side_effect=lambda *a, **k: self._vcl_caps(False)), \
             patch.object(camera_api.requests, "put", side_effect=_put):
            res = self.cam.add_plate_to_list([{"plateNum": "CA9999XX", "listType": "0"}])
        self.assertEqual(res.get("status"), "failed",
                         "statusCode != 1 must be a failure")

    def test_add_uses_vcl_when_supported(self):
        captured = {}

        def _put(url, *a, **k):
            captured["url"] = url
            captured["data"] = k.get("data")
            return _Resp(200, "OK")

        with patch.object(camera_api.requests, "get", side_effect=lambda *a, **k: self._vcl_caps(True)), \
             patch.object(camera_api.requests, "put", side_effect=_put):
            self.cam.add_plate_to_list([{"plateNum": "CA9999XX", "listType": "0"}])
        self.assertIn("/ISAPI/ITC/Entrance/VCL", captured["url"])
        body = captured["data"].decode("utf-8") if isinstance(captured["data"], bytes) else captured["data"]
        self.assertIn("SetVCLData", body)

    # Verbatim search response from a live DS-TCG406-E V5.5.0 (two of the seven
    # plates shown). Note the READ bucket wording <type>whiteList</type> differs
    # from the WRITE listType 'allowList', and the body is ver20-namespaced.
    _REAL_SEARCH_RESPONSE = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<LPListAuditSearchResult version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">'
        '<searchID>0</searchID><responseStatus>true</responseStatus>'
        '<responseStatusStrg>OK</responseStatusStrg>'
        '<LicensePlateInfoList>'
        '<numOfMatches>7</numOfMatches><totalMatches>7</totalMatches>'
        '<searchResultPosition>0</searchResultPosition><maxResults>10</maxResults>'
        '<LicensePlateInfo><id>PB4181KC</id><LicensePlate>PB4181KC</LicensePlate>'
        '<type>whiteList</type><cardNo>09809876</cardNo>'
        '<effectiveTime>2099-12-31T23:59:59+03:00</effectiveTime>'
        '<createTime>2000-01-01T00:00:00+03:00</createTime></LicensePlateInfo>'
        '<LicensePlateInfo><id>EA1499AB</id><LicensePlate>EA1499AB</LicensePlate>'
        '<type>whiteList</type>'
        '<effectiveTime>2027-06-01T18:02:00+03:00</effectiveTime>'
        '<createTime>2026-06-15T18:01:59+03:00</createTime></LicensePlateInfo>'
        '</LicensePlateInfoList></LPListAuditSearchResult>'
    )

    def test_search_lp_audit_posts_and_parses_real_response(self):
        captured = {}

        def _post(url, *a, **k):
            captured["url"] = url
            captured["data"] = k.get("data")
            captured["headers"] = k.get("headers")
            return _Resp(200, self._REAL_SEARCH_RESPONSE)

        with patch.object(camera_api.requests, "post", side_effect=_post):
            res = self.cam.search_lp_audit(max_results=10, position=0)
        self.assertEqual(res.get("status"), "success")
        self.assertIn("/searchLPListAudit", captured["url"])
        self.assertEqual(captured["headers"]["Content-Type"], "application/xml")
        self.assertIn("<maxResults>10</maxResults>", captured["data"])
        self.assertEqual(res["total"], 7)
        self.assertEqual(res["plates"], ["PB4181KC", "EA1499AB"])
        first = res["records"][0]
        self.assertEqual(first["plate"], "PB4181KC")
        self.assertEqual(first["type"], "whiteList")
        # READ wording 'whiteList' maps back to the Odoo list_category.
        self.assertEqual(first["list_category"], "whitelist")
        self.assertEqual(first["card_no"], "09809876")
        # A record without a <cardNo> still parses, with card_no None.
        self.assertIsNone(res["records"][1]["card_no"])

    def test_search_lp_audit_unparseable_body_is_empty(self):
        with patch.object(camera_api.requests, "post",
                          side_effect=lambda *a, **k: _Resp(200, "not xml")):
            res = self.cam.search_lp_audit()
        self.assertEqual(res["plates"], [])
        self.assertEqual(res["total"], 0)

    def test_delete_uses_del_endpoint_on_lp_audit(self):
        captured = {}

        def _put(url, *a, **k):
            captured["url"] = url
            captured["data"] = k.get("data")
            return _Resp(200, '{"statusCode":1,"statusString":"OK"}')

        with patch.object(camera_api.requests, "get", side_effect=lambda *a, **k: self._vcl_caps(False)), \
             patch.object(camera_api.requests, "put", side_effect=_put):
            res = self.cam.delete_plate_from_list([{"plateNum": "CA9999XX"}])
        self.assertEqual(res.get("status"), "success")
        self.assertIn("/DelLicensePlateAuditData", captured["url"])
        payload = json.loads(captured["data"])
        self.assertEqual(payload["CompoundCond"]["licensePlate"], "CA9999XX")
        self.assertFalse(payload["deleteAllEnabled"])
