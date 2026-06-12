# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install', 'polimex_ip_cam', 'ipcam_anpr_auth')
class TestAnprWebhookAuth(HttpCase):
    """Security regression for the public /ipcam/anpr/event webhook auth.

    The webhook is auth='public' with no shared secret. Without source-IP
    verification anyone who can reach the host could forge ANPR events (fake
    access / attendance). The webhook now authenticates the sender against the
    camera's configured IP (gated by polimex_ip_cam.anpr_verify_source_ip,
    default ON). The HttpCase client always connects from 127.0.0.1.
    """

    _registry_readonly_enabled = False

    def _make_camera(self, ip):
        return self.env['cctv.camera'].create({
            'name': 'Auth Probe Cam',
            'company_id': self.env.company.id,
            'ip_address': ip,
            'port': 80,
            'username': 'admin',
            'password': 'super-secret',
            'serial_number': 'AUTHUUID1',
            'tz': 'Europe/Sofia',
        })

    def _anpr_xml(self):
        return (
            '<EventNotificationAlert xmlns="http://www.isapi.org/ver20/XMLSchema">'
            '<deviceUUID>AUTHUUID1</deviceUUID>'
            '<eventType>ANPR</eventType>'
            '<dateTime>2026-06-11T09:00:00+02:00</dateTime>'
            '<ANPR><licensePlate>AUTH9999</licensePlate>'
            '<barrierGateCtrlType>0</barrierGateCtrlType></ANPR>'
            '</EventNotificationAlert>'
        ).encode('utf-8')

    def _post(self):
        return self.url_open(
            '/ipcam/anpr/event',
            files={'anpr.xml': ('anpr.xml', self._anpr_xml(), 'application/xml')},
        )

    def _events_for(self, camera):
        return (
            self.env['hr.rfid.event.system'].sudo().search_count([('camera_id', '=', camera.id)])
            + self.env['hr.rfid.event.user'].sudo().search_count([('camera_id', '=', camera.id)])
        )

    def test_forged_event_from_wrong_source_is_rejected(self):
        """Default (verification ON): a request whose source IP does not match
        the camera's configured IP creates no event."""
        cam = self._make_camera('10.0.0.99')  # != 127.0.0.1 (the test client)
        before = self._events_for(cam)
        self._post()
        self.assertEqual(self._events_for(cam), before,
                         'A request from an unverified source must not create any event')

    def test_event_from_matching_source_is_accepted(self):
        """A request whose source IP matches the camera's configured IP is
        authenticated and processed."""
        cam = self._make_camera('127.0.0.1')  # == the HttpCase client source
        before = self._events_for(cam)
        self._post()
        self.assertEqual(self._events_for(cam), before + 1,
                         'A request from the configured camera IP must be processed')

    def test_verification_off_allows_any_source(self):
        """With the system parameter disabled (NAT escape hatch), any source is
        accepted (identification falls back to deviceUUID)."""
        self.env['ir.config_parameter'].sudo().set_param(
            'polimex_ip_cam.anpr_verify_source_ip', '0')
        cam = self._make_camera('10.0.0.99')  # != source, but verification off
        before = self._events_for(cam)
        self._post()
        self.assertEqual(self._events_for(cam), before + 1,
                         'With verification disabled the event must still be processed')
