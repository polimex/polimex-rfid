import json
import logging
import base64
import time
import xml.etree.ElementTree as ET
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
        # --- Log the incoming request ---
        # Използваме Odoo парсването на multipart/form-data:
        # form_data = dict(request.httprequest.form)
        # headers = dict(request.httprequest.headers)
        # files_dict = {}
        #
        # for key, file_storage in request.httprequest.files.items():
        #     try:
        #         content = file_storage.read()
        #         # Възстановяваме позицията в стрийма, ако е необходимо по-късно
        #         file_storage.stream.seek(0)
        #         files_dict[file_storage.filename] = base64.b64encode(content).decode('utf-8')
        #     except Exception as e:
        #         _logger.error("Грешка при четене на файл %s: %s", file_storage.filename, e)
        #
        # # Създаваме структура за логване на заявката
        # log_record = {
        #     'timestamp': time.time(),
        #     'headers': headers,
        #     'form': form_data,
        #     'files': files_dict
        # }
        #
        # try:
        #     with open("/tmp/request1", "a") as log_file:
        #         log_file.write(json.dumps(log_record) + "\n")
        # except Exception as e:
        #     _logger.error("Грешка при запис във файла /tmp/request1: %s", e)
        #
        # _logger.info("Заявката е записана във файла /tmp/request1")
        # --- End log ---

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
                camera_id.parse_event(files_data)
                _logger.info(f'Camera ID detected: {camera_id}')
        if 'heartBeat' in files_data:
            heartbeat_data = files_data["heartBeat"]
            # Намери камерата по IP адрес
            camera = request.env['cctv.camera'].sudo().search(
                [('ip_address', '=', heartbeat_data.get('ipAddress'))],
                limit=1)
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

                # Текущо сървърно време
                server_time = fields.Datetime.now()

                if hb_time:
                    # Преобразуваме текущото време в часовата зона на камерата, ако е зададена
                    if camera.tz:
                        tz_obj = pytz.timezone(camera.tz)
                        server_time_local = server_time.astimezone(tz_obj)
                    else:
                        server_time_local = server_time

                    # Форматираме офсета – от "+0200" към "GMT+02:00"
                    offset = camera.tz_offset or "+0000"
                    formatted_offset = "GMT" + offset[:3] + ":" + offset[3:]

                    # Изчисляваме разликата
                    try:
                        hb_time_local = hb_time.astimezone(tz_obj) if camera.tz else hb_time
                    except Exception:
                        hb_time_local = hb_time
                    diff = abs((server_time_local - hb_time_local).total_seconds())
                    if diff > 300:
                        _logger.info(
                            f"Heartbeat time difference ({diff} seconds) is greater than 5 minutes. Synchronizing time.")
                        new_time_config = {
                            "timeMode": "manual",  # или "NTP" според нуждите
                            "timeZone": formatted_offset,
                            "localTime": server_time_local.replace(microsecond=0).isoformat()
                        }
                        with camera.get_api() as cam_api:
                            result = cam_api.set_time_config(new_time_config)
                            if result.get("status") == "success":
                                _logger.info("Time synchronized successfully for camera %s", camera.name)
                            else:
                                _logger.error("Failed to synchronize time for camera %s: %s", camera.name,
                                              result.get("error"))
            else:
                _logger.error("Camera with IP %s not found in the model.", heartbeat_data.get('ipAddress'))

        return 'OK'
