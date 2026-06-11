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
