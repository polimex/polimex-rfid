import logging
import base64
import defusedxml.ElementTree as ET
from datetime import datetime

import pytz

from odoo import fields
from odoo.http import Controller, route, request

_logger = logging.getLogger(__name__)


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

    @route(['/ipcam/anpr/event'], type='http', auth='public', methods=['POST'], csrf=False)
    def receive_anpr_event(self, **kwargs):
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
                    root = ET.fromstring(file_content)
                    parsed_xml = self.parse_xml_to_dict(root)
                    # illaccess.xml, anpr.xml, etc.
                    file_base_name = file_storage.filename.rsplit('.', 1)[0]
                    files_data[file_base_name] = parsed_xml
                except ET.ParseError as e:
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
            # Searching for camera ID in anpr.xml
            if 'deviceUUID' in anpr_data:
                camera_id = request.env['cctv.camera'].sudo().search([('serial_number', '=', anpr_data['deviceUUID'])])
                if not camera_id:
                    _logger.error(f"Camera with serial number {anpr_data['deviceUUID']} not found.")
                    # TODO Log System Event
                    return request.not_found()
                # SECURITY: authenticate the sender (the webhook is public).
                if not self._verify_camera_source(camera_id):
                    return request.not_found()
                # SECURITY: never trust the IP reported in this unauthenticated
                # event body. Overwriting the stored camera IP here let an
                # attacker point the server's credentialed outbound calls
                # (get_api -> HTTPDigestAuth) at an arbitrary host — SSRF plus
                # theft of the camera admin credentials. The admin-configured
                # ip_address is the only trusted endpoint; a mismatch is only
                # logged for manual review, never auto-applied.
                reported_ip = anpr_data.get('ipAddress')
                if reported_ip and reported_ip != camera_id.ip_address:
                    _logger.warning(
                        "ANPR event for camera %s reports IP %s but the "
                        "configured IP is %s; ignoring it (possible DHCP "
                        "change or spoofing attempt).",
                        camera_id.name, reported_ip, camera_id.ip_address)
                camera_id.parse_event(files_data)
                _logger.info(f'Camera ID detected: {camera_id}')
        if 'heartBeat' in files_data:
            heartbeat_data = files_data["heartBeat"]
            # SECURITY: identify the camera by the request's network source IP
            # (trustworthy on an isolated camera LAN) rather than the body IP,
            # so a forged heartbeat cannot trigger an outbound time-sync. Only
            # when source verification is disabled do we fall back to the
            # body-reported IP for identification.
            src_ip = request.httprequest.remote_addr
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
                except Exception as e:
                    _logger.error(f"Error parsing heartbeat dateTime: {e}")
                    hb_time = None

                # fields.Datetime.now() is naive UTC; localise it before any
                # astimezone() or the local-time math (and the camera time-sync
                # it drives) is wrong whenever the server OS tz is not UTC.
                server_time = pytz.utc.localize(fields.Datetime.now())

                if hb_time:
                    cam_tz = pytz.timezone(camera.tz) if camera.tz else pytz.utc
                    server_time_local = server_time.astimezone(cam_tz)

                    # Форматираме офсета – от "+0200" към "GMT+02:00"
                    offset = camera.tz_offset or "+0000"
                    formatted_offset = "GMT" + offset[:3] + ":" + offset[3:]

                    # Normalise the camera time to aware-UTC for the comparison:
                    # a camera may send an offset-aware OR a naive local time.
                    if hb_time.tzinfo is None:
                        hb_aware = cam_tz.localize(hb_time)
                    else:
                        hb_aware = hb_time
                    diff = abs((server_time - hb_aware.astimezone(pytz.utc)).total_seconds())
                    if diff > 300:
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
