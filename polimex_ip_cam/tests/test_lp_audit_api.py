import io
import json

import xlrd
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.polimex_ip_cam.helpers import camera_api
from odoo.addons.polimex_ip_cam.helpers.camera_api import HikvisionCamera

NS = {"ns": "http://www.isapi.org/ver20/XMLSchema"}


class _Resp:
    def __init__(self, status_code=200, text="", content=b""):
        self.status_code = status_code
        self.text = text
        self.content = content or text.encode("utf-8")


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_lpaudit")
class TestBuildLpXls(TransactionCase):
    """The LP-audit list import is an Excel .xls with a fixed 5-column layout;
    'Belong to' is Allowlist for whitelist (listType 0) and Blocklist for
    blacklist (listType 1)."""

    def _read(self, blob):
        wb = xlrd.open_workbook(file_contents=blob)
        sh = wb.sheet_by_index(0)
        return [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)]

    def test_header_and_belong_to_mapping(self):
        blob = HikvisionCamera._build_lp_xls([
            {"plateNum": "CA1234AB", "listType": "0"},
            {"plateNum": "CA5678CD", "listType": "1"},
        ])
        rows = self._read(blob)
        self.assertEqual(
            rows[0],
            ["License Plate Number", "Belong to", "Card No.",
             "Start Time For Entry", "End Time For Entry"],
        )
        self.assertEqual(rows[1][0], "CA1234AB")
        self.assertEqual(rows[1][1], "Allowlist")   # listType 0 -> whitelist
        self.assertEqual(rows[2][0], "CA5678CD")
        self.assertEqual(rows[2][1], "Blocklist")   # listType 1 -> blacklist

    def test_times_and_cardno_passthrough(self):
        blob = HikvisionCamera._build_lp_xls([{
            "plateNum": "CA0001AA", "listType": "0", "cardNo": "12345",
            "startTime": "2026-06-16T15:00:00+03:00",
            "endTime": "2099-12-31T23:59:59+03:00",
        }])
        rows = self._read(blob)
        self.assertEqual(rows[1][2], "12345")
        self.assertEqual(rows[1][3], "2026-06-16T15:00:00+03:00")
        self.assertEqual(rows[1][4], "2099-12-31T23:59:59+03:00")

    def test_missing_times_get_a_default_window(self):
        # A plate with no validity must still import — a non-empty End Time is
        # required by the camera, so a far-future default is supplied.
        blob = HikvisionCamera._build_lp_xls([{"plateNum": "CA0002BB", "listType": "0"}])
        rows = self._read(blob)
        self.assertTrue(rows[1][4], "End Time must default to a non-empty value")


@tagged("post_install", "-at_install", "polimex_ip_cam", "ipcam_lpaudit")
class TestLpAuditRouting(TransactionCase):
    """add/delete route to the VCL API on cameras that support it, and to the
    newer LP-audit API (Excel import / DelLicensePlateAuditData) otherwise."""

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

    def test_add_uses_lp_audit_when_vcl_unsupported(self):
        captured = {}

        def _put(url, *a, **k):
            captured["url"] = url
            captured["data"] = k.get("data")
            return _Resp(200, "<ResponseStatus><statusCode>1</statusCode><successNum>1</successNum></ResponseStatus>")

        with patch.object(camera_api.requests, "get", side_effect=lambda *a, **k: self._vcl_caps(False)), \
             patch.object(camera_api.requests, "put", side_effect=_put):
            res = self.cam.add_plate_to_list([{"plateNum": "CA9999XX", "listType": "0"}])
        self.assertEqual(res.get("status"), "success")
        self.assertIn("/licensePlateAuditData", captured["url"])
        self.assertIn("fileType=xls", captured["url"])
        # Body is a real .xls workbook with the plate in it.
        wb = xlrd.open_workbook(file_contents=captured["data"])
        self.assertEqual(wb.sheet_by_index(0).cell_value(1, 0), "CA9999XX")

    def test_add_reports_failure_when_successnum_zero(self):
        # The camera accepts the file (statusCode 1) but applies 0 rows when the
        # data is rejected — that must NOT be reported as success, or a plate the
        # camera never stored would be marked done in Odoo.
        def _put(url, *a, **k):
            return _Resp(200, "<ResponseStatus><statusCode>1</statusCode>"
                              "<successNum>0</successNum></ResponseStatus>")

        with patch.object(camera_api.requests, "get", side_effect=lambda *a, **k: self._vcl_caps(False)), \
             patch.object(camera_api.requests, "put", side_effect=_put):
            res = self.cam.add_plate_to_list([{"plateNum": "CA9999XX", "listType": "0"}])
        self.assertEqual(res.get("status"), "failed",
                         "successNum=0 (file accepted but nothing applied) must be a failure")

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
