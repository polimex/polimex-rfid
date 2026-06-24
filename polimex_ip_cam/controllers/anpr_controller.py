import logging
import base64
from datetime import datetime

import pytz
from lxml import etree

from odoo import fields
from odoo.http import Controller, route, request
from odoo.addons.polimex_ip_cam.helpers.safe_xml import parse_untrusted_xml

_logger = logging.getLogger(__name__)

# Re-sync the camera clock only past this drift (seconds); below it the small
# offset is left alone to avoid churning set_time on every heartbeat.
HEARTBEAT_CLOCK_DRIFT_TOLERANCE = 300


def _hikvision_timezone(iso_offset):
    """Build a Hikvision <timeZone> string from an ISO offset.

    Hikvision follows the POSIX/inverted sign convention: a zone of UTC+3 must
    be sent as ``GMT-03:00`` — sending ``GMT+03:00`` is applied by the camera as
    UTC-3, which keeps the clock ~2x off and triggers an endless set_time loop.
    Invert the ISO offset's sign; tolerate a missing/garbage value (-> UTC).
    """
    iso_offset = (iso_offset or "").strip()
    if len(iso_offset) < 5 or iso_offset[0] not in "+-":
        iso_offset = "+0000"
    sign = "-" if iso_offset[0] == "+" else "+"
    return "GMT%s%s:%s" % (sign, iso_offset[1:3], iso_offset[3:5])


class IpcamController(Controller):

    def parse_xml_to_dict(self, element):
        tag = element.tag.split('}', 1)[-1]  # remove namespace
        data_dict = {}
        for child in element:
            child_tag = child.tag.split('}', 1)[-1]
            data_dict[child_tag] = self.parse_xml_to_dict(child) if len(child) > 0 else child.text
        return data_dict

    def _source_ip_verification_on(self):
        return request.env['ir.config_parameter'].sudo().get_param(
            'polimex_ip_cam.anpr_verify_source_ip', '1') in ('1', 'true', 'True')

    def _verify_camera_source(self, camera):
        """Authenticate the webhook: the request must originate from the
        camera's configured IP.

        The /ipcam/anpr/event route is auth='public' with no shared secret, so
        without this check anyone who can reach the host could forge ANPR /
        heartbeat events (fake access & attendance, or trigger a credentialed
        outbound time-sync). Gated by the system parameter
        polimex_ip_cam.anpr_verify_source_ip (default ON); NAT'd deployments
        where Odoo cannot see the camera's real source IP can set it to 0.
        """
        if not self._source_ip_verification_on():
            return True
        src = request.httprequest.remote_addr
        if src and camera.ip_address and src == camera.ip_address:
            return True
        _logger.warning(
            "Rejected ANPR webhook for camera %s: request from %s does not "
            "match the configured camera IP %s. If this camera is behind NAT, "
            "set system parameter polimex_ip_cam.anpr_verify_source_ip to 0.",
            camera.name, src, camera.ip_address)
        return False

    def validate_files(self, files):
        allowed_extensions = ['.xml', '.jpg']
        for file_key, file_storage in files.items():
            if not any(file_storage.filename.endswith(ext) for ext in allowed_extensions):
                _logger.error(f"Invalid file type for file: {file_storage.filename}")
                return False
            if file_storage.content_length > 5 * 1024 * 1024:  # 5MB size limit
                _logger.error(f"File size exceeds limit: {file_storage.filename}")
                return False
        return True

    @route(['/ipcam/anpr/event', '/ipcam/anpr/event/<camera_token>'],
           type='http', auth='public', methods=['POST'], csrf=False)
    def receive_anpr_event(self, camera_token=None, **kwargs):
        # The camera posts to a URL that embeds its own identifier (sub-serial /
        # deviceUUID), set by action_set_http_host. That token rides in EVERY
        # request — including the heartbeat, whose body carries no UUID — and is
        # stable behind NAT where the source and body IPs are not. It is the
        # primary way to identify the camera; IP is only a legacy fallback.
        token_camera = request.env['cctv.camera'].sudo().search(
            [('sub_serial_number', '=', camera_token)], limit=1) if camera_token else request.env['cctv.camera'].sudo().browse()
        files = request.httprequest.files
        if not files:
            _logger.error("No files uploaded.")
            return request.not_found()

        if not self.validate_files(files):
            return request.not_found()

        files_data = {}
        for file_key, file_storage in files.items():
            file_content = file_storage.read()
            if file_storage.filename.endswith('.xml'):
                try:
                    root = parse_untrusted_xml(file_content)
                    parsed_xml = self.parse_xml_to_dict(root)
                    # illaccess.xml, anpr.xml, etc.
                    file_base_name = file_storage.filename.rsplit('.', 1)[0]
                    files_data[file_base_name] = parsed_xml
                except etree.XMLSyntaxError as e:
                    _logger.error(f"Invalid XML content in {file_storage.filename}: {e}")
                    return request.not_found()
            elif file_storage.filename.endswith('.jpg'):
                image_base64 = base64.b64encode(file_content).decode('utf-8')
                files_data[file_storage.filename] = f'data:image/jpeg;base64,{image_base64}'

        # _logger.info('Parsed files data: %s', files_data)
        # Логване на получените файлове по имена
        _logger.info("Received file: %s", ','.join([filename for filename in files_data]))

        # searching for anpr.xml
        if 'illaccess' in files_data:
            illaccess_data = files_data['illaccess']
            _logger.info(f'illaccess_data: {illaccess_data})')
        if 'anpr' in files_data:
            anpr_data = files_data['anpr']
            # Identify the camera by the deviceUUID it reports (its ISAPI
            # subSerialNumber, stored as sub_serial_number), with a full-serial
            # and a trusted-source-IP fallback — see _resolve_anpr_camera.
            device_uuid = anpr_data.get('deviceUUID')
            src_ip = request.httprequest.remote_addr
            # Prefer the URL token (NAT-proof); fall back to body deviceUUID / IP.
            camera_id = token_camera or request.env['cctv.camera'].sudo()._resolve_anpr_camera(
                device_uuid, src_ip, self._source_ip_verification_on())
            if not camera_id:
                _logger.error("ANPR event (token=%s, deviceUUID=%s) from %s matched no camera.",
                              camera_token, device_uuid, src_ip)
                return request.not_found()
            # SECURITY: when the camera is identified by its URL token the token
            # IS the authentication and works behind NAT, so the source-IP check
            # (which fails behind NAT) is skipped. Without a token, fall back to
            # verifying the request's source IP as before.
            if not token_camera and not self._verify_camera_source(camera_id):
                return request.not_found()
            # The body-reported IP is never trusted for identification or for
            # repointing outbound calls (SSRF guard). It frequently differs from
            # the real address (stale camera config / NAT) — log at debug only;
            # it does NOT affect processing of the event.
            reported_ip = anpr_data.get('ipAddress')
            if reported_ip and reported_ip != camera_id.ip_address:
                _logger.debug(
                    "ANPR event for camera %s carries body IP %s (stored %s); "
                    "body IP is informational only, not used for identification.",
                    camera_id.name, reported_ip, camera_id.ip_address)
            camera_id.parse_event(files_data)
            _logger.info("ANPR event processed for camera %s.", camera_id.name)
        if 'heartBeat' in files_data:
            heartbeat_data = files_data["heartBeat"]
            # The heartbeat body carries NO device UUID — only an IP — so without
            # the URL token it can only be matched by IP, which fails behind NAT.
            # Prefer the URL token (NAT-proof); otherwise match by the request's
            # network source IP, and only when source verification is disabled
            # fall back to the body-reported IP.
            src_ip = request.httprequest.remote_addr
            camera = token_camera
            if not camera:
                camera = request.env['cctv.camera'].sudo().search(
                    [('ip_address', '=', src_ip)], limit=1)
            if not camera and not self._source_ip_verification_on():
                camera = request.env['cctv.camera'].sudo().search(
                    [('ip_address', '=', heartbeat_data.get('ipAddress'))], limit=1)
            if camera:
                # Актуализиране на last_heart_beat
                camera.sudo().write({'last_heart_beat': fields.Datetime.now()})
                # Опит за парсване на dateTime от heartbeat
                hb_time_str = heartbeat_data.get('dateTime')
                try:
                    hb_time = datetime.fromisoformat(hb_time_str)
                    # Hikvision reports the heartbeat time with its INVERTED
                    # timeZone offset (e.g. '-03:00' for a UTC+3 camera, because
                    # we configure it as GMT-03:00 — see _hikvision_timezone).
                    # Trusting that offset makes the comparison below see a
                    # constant ~6h false drift and re-queue set_time on every
                    # heartbeat, forever. Drop the unreliable offset and treat
                    # the value as a naive wall-clock in the camera's configured
                    # timezone (re-anchored just below).
                    if hb_time is not None and hb_time.tzinfo is not None:
                        hb_time = hb_time.replace(tzinfo=None)
                except Exception as e:
                    _logger.warning("Could not parse heartbeat dateTime %r: %s", hb_time_str, e)
                    hb_time = None

                # fields.Datetime.now() is naive UTC; localise it before any
                # astimezone() or the local-time math (and the camera time-sync
                # it drives) is wrong whenever the server OS tz is not UTC.
                server_time = pytz.utc.localize(fields.Datetime.now())

                if hb_time:
                    cam_tz = pytz.timezone(camera.tz) if camera.tz else pytz.utc
                    server_time_local = server_time.astimezone(cam_tz)

                    # Hikvision uses the POSIX/inverted timeZone sign: UTC+3
                    # must be sent as "GMT-03:00" (sending "GMT+03:00" is applied
                    # as UTC-3 and loops set_time forever). See _hikvision_timezone.
                    formatted_offset = _hikvision_timezone(camera.tz_offset)

                    # Normalise the camera time to aware-UTC for the comparison:
                    # a camera may send an offset-aware OR a naive local time.
                    if hb_time.tzinfo is None:
                        hb_aware = cam_tz.localize(hb_time)
                    else:
                        hb_aware = hb_time
                    diff = abs((server_time - hb_aware.astimezone(pytz.utc)).total_seconds())
                    _logger.debug("Heartbeat clock diff for camera %s: %.0fs", camera.name, diff)
                    if diff > HEARTBEAT_CLOCK_DRIFT_TOLERANCE:
                        _logger.info(
                            "Heartbeat time difference (%s s) > 5 min for camera %s; "
                            "queuing a time-sync command.", diff, camera.name)
                        new_time_config = {
                            "timeMode": "manual",  # или "NTP" според нуждите
                            "timeZone": formatted_offset,
                            # Naive local wall-clock (no offset suffix); the tz
                            # is carried separately in timeZone.
                            "localTime": server_time_local.replace(tzinfo=None, microsecond=0).isoformat()
                        }
                        # Do NOT run the credentialed outbound HTTP inline in the
                        # public web worker (it blocks the request and can 500 /
                        # cause camera retry-storms). Queue it; cctv.camera.command
                        # delivers it asynchronously on a fresh cursor.
                        request.env['cctv.camera.command'].sudo().create([{
                            'camera_id': camera.id,
                            'command_type': 'set_time',
                            'request_data': "\n".join(f"{k}={v}" for k, v in new_time_config.items()),
                        }])
            else:
                _logger.warning("Heartbeat from %s did not match any configured camera IP.",
                                request.httprequest.remote_addr)

        return 'OK'
