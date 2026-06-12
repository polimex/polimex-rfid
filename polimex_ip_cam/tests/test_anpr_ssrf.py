# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install', 'polimex_ip_cam', 'ipcam_anpr_ssrf')
class TestAnprSsrf(HttpCase):
    """Security regression for the unauthenticated ANPR webhook.

    The webhook used to overwrite the stored camera IP with the IP reported in
    the (untrusted) event body. The server's outbound calls (get_api ->
    HTTPDigestAuth with the camera admin credentials) then targeted that IP,
    giving an attacker SSRF + credential theft. The stored, admin-configured IP
    must never be changed from the event body.
    """

    _registry_readonly_enabled = False

    def setUp(self):
        super().setUp()
        # These tests target the body-IP overwrite (SSRF), not the source-IP
        # webhook auth — disable the latter so the request reaches parse_event
        # regardless of the test client's source IP.
        self.env['ir.config_parameter'].sudo().set_param(
            'polimex_ip_cam.anpr_verify_source_ip', '0')
        self.stored_ip = '10.99.0.5'
        self.camera = self.env['cctv.camera'].create({
            'name': 'SSRF Probe Cam',
            'company_id': self.env.company.id,
            'ip_address': self.stored_ip,
            'port': 80,
            'username': 'admin',
            'password': 'super-secret',
            'serial_number': 'SSRFTESTUUID',
            'tz': 'Europe/Sofia',
        })

    def _anpr_xml(self, device_uuid, reported_ip):
        return (
            '<EventNotificationAlert xmlns="http://www.isapi.org/ver20/XMLSchema">'
            f'<deviceUUID>{device_uuid}</deviceUUID>'
            f'<ipAddress>{reported_ip}</ipAddress>'
            '<eventType>ANPR</eventType>'
            '<dateTime>2026-06-11T09:00:00+02:00</dateTime>'
            '<ANPR><licensePlate>XX0000XX</licensePlate>'
            '<barrierGateCtrlType>0</barrierGateCtrlType></ANPR>'
            '</EventNotificationAlert>'
        ).encode('utf-8')

    def test_event_body_ip_does_not_overwrite_stored_ip(self):
        """A forged ANPR event reporting an attacker IP must NOT change the
        camera's stored IP, and outbound calls must still target it."""
        attacker_ip = '6.6.6.6'
        self.url_open(
            '/ipcam/anpr/event',
            files={'anpr.xml': ('anpr.xml', self._anpr_xml('SSRFTESTUUID', attacker_ip),
                                'application/xml')},
        )
        self.camera.invalidate_recordset(['ip_address'])
        self.assertEqual(
            self.camera.ip_address, self.stored_ip,
            'The ANPR webhook must not overwrite the stored camera IP from the body')
        # The credentialed client must still point at the admin-configured host.
        self.assertEqual(self.camera.get_api().ip_address, self.stored_ip)

    def test_unknown_device_uuid_is_not_found(self):
        """An event for an unknown camera UUID is rejected (404), creating no
        camera and changing nothing."""
        resp = self.url_open(
            '/ipcam/anpr/event',
            files={'anpr.xml': ('anpr.xml', self._anpr_xml('NOSUCHCAM', '6.6.6.6'),
                                'application/xml')},
        )
        self.assertEqual(resp.status_code, 404)
        self.camera.invalidate_recordset(['ip_address'])
        self.assertEqual(self.camera.ip_address, self.stored_ip)

    def test_missing_datetime_does_not_crash_webhook(self):
        """An ANPR event without a dateTime must not 500 the public webhook —
        the required timestamp falls back to server time (C1)."""
        xml = (
            '<EventNotificationAlert xmlns="http://www.isapi.org/ver20/XMLSchema">'
            '<deviceUUID>SSRFTESTUUID</deviceUUID>'
            '<eventType>ANPR</eventType>'
            '<ANPR><licensePlate>NOCARD99</licensePlate>'
            '<barrierGateCtrlType>0</barrierGateCtrlType></ANPR>'
            '</EventNotificationAlert>'
        ).encode('utf-8')
        before = self.env['hr.rfid.event.system'].sudo().search_count(
            [('camera_id', '=', self.camera.id)])
        resp = self.url_open(
            '/ipcam/anpr/event',
            files={'anpr.xml': ('anpr.xml', xml, 'application/xml')},
        )
        self.assertNotEqual(resp.status_code, 500, 'Missing dateTime must not 500')
        sys_event = self.env['hr.rfid.event.system'].sudo().search(
            [('camera_id', '=', self.camera.id)], order='id desc', limit=1)
        self.assertEqual(
            self.env['hr.rfid.event.system'].sudo().search_count(
                [('camera_id', '=', self.camera.id)]),
            before + 1, 'Unknown plate must record a system event')
        self.assertTrue(sys_event.timestamp, 'timestamp must be set (defaulted to now)')
