from datetime import datetime, timezone

import pytz

from odoo import models, fields, api, _, Command, SUPERUSER_ID
import logging
from odoo.addons.polimex_ip_cam.helpers.camera_api import HikvisionCamera  # import our Hikvision-specific class
from odoo.addons.hr_rfid.models.hr_rfid_webstack import get_local_ip
import json

_logger = logging.getLogger(__name__)

# Hikvision ISAPI ANPR `barrierGateCtrlType`. '1' = the camera drove the barrier
# open for an in-list plate. This is NOT a reliable allow/deny signal: on
# installations where the camera does not control the barrier the field is
# always '0', even for recognised whitelist plates (confirmed in production on
# DS-TCG406-E V5.4.4 — the push omits the list-match result entirely, listType
# arrives empty). The granted/denied decision for user events is therefore taken
# from this camera's own plate lists in Odoo (cctv.camera.rfid.rel), NOT from
# this field. The constant is kept only as a descriptive hint in the
# unknown-plate system-event text (see docs/SECURITY_AUDIT_2026-06.md, H5).
BARRIER_GATE_IN_LIST = '1'

# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]
def _tz_get(self):
    return _tzs


class CctvCamera(models.Model):
    _name = 'cctv.camera'
    _description = 'CCTV Camera Management'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'balloon.mixin']

    # Original fields (unchanged)
    name = fields.Char(string='Name', required=True, tracking=True,
                       help="Camera name for easy identification")
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Uncheck to archive the camera. Inactive cameras no longer receive commands or accept push events; existing plate-list records remain for history.",
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="Company that owns the camera. Cameras are isolated per company; record rules prevent users seeing devices outside their allowed companies.",
    )
    tz = fields.Selection(
        selection=_tzs, string='Timezone',
        # The camera's timezone is a property of its physical location, so prefer
        # the company's timezone over the session user's (who may be elsewhere).
        default=lambda self: self.env.company.partner_id.tz or self.env.context.get('tz'),
        help="The timezone of the camera's location. The camera's on-screen clock "
             "(burned onto recordings) and the plate timestamps are set in this "
             "timezone; Odoo stores everything in UTC and converts."
    )

    tz_offset = fields.Char(
        compute='_compute_tz_offset',
        string='Timezone offset',
        help="UTC offset string derived from the timezone above. Sent to the camera when synchronising clocks.",
    )

    behind_nat = fields.Boolean(
        string='Behind NAT',
        help="Camera is behind a NAT (Network Address Translation) router",
        default=False,
    )
    ip_address = fields.Char(string='IP Address', required=True, tracking=True,
                             help="Camera IP address")
    port = fields.Integer(string='Port', default=80, tracking=True,
                          help="Camera port (usually 80 or 8000)")
    username = fields.Char(string='Username', default='admin', tracking=True,
                           help="Camera access username")
    password = fields.Char(
        string='Password',
        groups='polimex_ip_cam.group_cctv_manager',
        help="Camera access password. Restricted to CCTV managers — it is the "
             "credential an attacker would need; do not expose it to plain "
             "CCTV users or in shared exports.")
    brand = fields.Selection([
        ('hikvision', 'Hikvision'),
        ('dahua', 'Dahua'),
        ('onvif_generic', 'ONVIF (generic)'),
    ], string='Brand', required=True, default='hikvision', tracking=True,
        help="Camera brand. 'ONVIF (generic)' is set by network discovery for a "
             "non-Hikvision device that answered ONVIF — it supports the standard "
             "ONVIF surface (video, device info) but not the Hikvision-specific "
             "ANPR/plate-list features.")
    model = fields.Char(string='Model', tracking=True,
                        help="Camera model (obtained via ISAPI)", readonly=True)
    serial_number = fields.Char(string='Serial Number', tracking=True,
                                help="Camera serial number", readonly=True)
    sub_serial_number = fields.Char(
        string='Sub-Serial (Device UUID)', tracking=True, index=True, readonly=True,
        help="Short device serial the camera reports as 'deviceUUID' in ANPR "
             "events (ISAPI subSerialNumber). Incoming plate events are matched "
             "to this camera by this value. Filled automatically on Check "
             "Connection, or learned from the first event received from the "
             "camera's IP.")
    firmware = fields.Char(string='Firmware', tracking=True,
                           help="Camera firmware version", readonly=True)
    description = fields.Text(string='Description',
                              help="Additional camera information")
    server_setup = fields.Text(string="Server Setup",
                               help="Camera server setup configuration (param=value per line)")
    entrance_setup = fields.Text(string="Entrance Setup",
                               help="Camera entrance setup configuration (param=value per line)")
    snapshot = fields.Image(
        string="Snapshot",
        help="Camera snapshot image (base64 encoded)",
        # default=''   # TODO - set a default image
    )

    # Integration type to separate logic (discovery, configuration, event processing)
    integration_type = fields.Selection(
        selection=[
            ('anpr', 'ANPR IP Camera'),
            ('cctv_cam', 'IP CCTV Camera'),
            ('cctv_nvr', 'IP CCTV Network Video Recorder'),
        ], string='Integration Type',
        default='anpr',
        help="Type of integration logic used for this camera")

    connection_status = fields.Selection(
        selection=[
        ('unknown', 'Not checked yet'),
        ('connected', 'Online'),
        ('unreachable', 'Not reachable'),
        ('auth_failed', 'Wrong credentials'),
        ('protocol_error', 'Unexpected response'),
        ('error', 'Error'),
        ('failed', 'Failed'),  # legacy value, re-classified on next check
    ],
        string='Connection Status',
        default='unknown',
        tracking=True,
        help="Latest connection check result")
    connection_message = fields.Char(
        string='Connection Details',
        compute='_compute_connection_message',
        help="Plain-language explanation of the latest connection status and "
             "what to do about it.")
    last_seen = fields.Datetime(
        string='Last Seen Online',
        readonly=True,
        help="When the camera last answered a connection check successfully.")
    connection_error_detail = fields.Text(
        string='Technical Details',
        readonly=True,
        help="Raw error returned by the last failed connection check "
             "(for support/diagnostics).")
    last_heart_beat = fields.Datetime(
        string='Last Heartbeat',
        help="Last successful received HeartBeat from the camera",
        readonly=True)
    reader_ids = fields.Many2many(
        comodel_name='hr.rfid.reader',
        string='Reader',
        help="RFID reader linked to this camera",
        ondelete='cascade',
    )
    door_id = fields.One2many(
        comodel_name='hr.rfid.door',
        inverse_name='camera_id',
        help="RFID doors whose readers are wired to this camera. Card assignments on these doors are mirrored to the camera's plate whitelist automatically.",
    )
    # Intermediate relations to link RFID cards with a list category
    rfid_rel_ids = fields.One2many(
        comodel_name='cctv.camera.rfid.rel',
        inverse_name='camera_id',
        string='RFID Card Relations',
        help="Relations linking this camera with RFID cards and their list types"
    )
    # Computed Many2many field for easy access to all linked RFID cards
    rfid_card_ids = fields.Many2many(
        comodel_name='hr.rfid.card',
        compute='_compute_rfid_card_ids',
        string='RFID Cards',
        help="Flat view of every RFID card registered with this camera, across all list categories. Convenience field for searches and reports.",
    )
    rfid_whitelist_count = fields.Integer(
        string='Whitelist Count',
        compute='_compute_list_counts', store=True,
        help="Live count of plates classified as Whitelist (auto-grant). Used by the smart button on the form.",
    )
    rfid_blacklist_count = fields.Integer(
        string='Blacklist Count',
        compute='_compute_list_counts', store=True,
        help="Live count of plates classified as Blacklist (auto-deny). Used by the smart button on the form.",
    )

    @api.depends('tz')
    def _compute_tz_offset(self):
        for cam in self:
            cam.tz_offset = datetime.now(pytz.timezone(cam.tz or 'GMT')).strftime('%z')

    @api.depends('connection_status')
    def _compute_connection_message(self):
        # Plain-language, actionable copy — what happened and what to do — kept
        # out of the server log (operators read the log; users read the form).
        messages = {
            'unknown': self.env._("Not checked yet. Use “Check Connection” to test."),
            'connected': self.env._("Online — the camera is reachable and responding."),
            'unreachable': self.env._(
                "Camera not reachable. Check that it is powered on, the network "
                "cable, and that the IP address is correct."),
            'auth_failed': self.env._(
                "Wrong username or password for the camera. Update the "
                "credentials and check again."),
            'protocol_error': self.env._(
                "The camera answered but in an unexpected format "
                "(wrong model or firmware?)."),
            'error': self.env._("Connection error — see the technical details below."),
            'failed': self.env._(
                "Connection failed. Run “Check Connection” for an updated diagnosis."),
        }
        for cam in self:
            cam.connection_message = messages.get(cam.connection_status, '')

    @api.depends('rfid_rel_ids.card_id')
    def _compute_rfid_card_ids(self):
        for rec in self:
            rec.rfid_card_ids = rec.rfid_rel_ids.mapped('card_id')

    @api.depends('rfid_rel_ids.list_category')
    def _compute_list_counts(self):
        for rec in self:
            rec.rfid_whitelist_count = len(rec.rfid_rel_ids.filtered(lambda r: r.list_category == 'whitelist'))
            rec.rfid_blacklist_count = len(rec.rfid_rel_ids.filtered(lambda r: r.list_category == 'blacklist'))

    @api.depends('model', 'name', 'brand')
    def _compute_display_name(self):
        for record in self:
            brand_dict = dict(record._fields['brand'].selection)
            brand_label = brand_dict.get(record.brand, record.brand)
            record.display_name = f"{record.name} ({brand_label}/ {record.model})"

    def action_show_reader(self):
        reader_action = self.env.ref('hr_rfid.hr_rfid_reader_action').read()[0]
        reader_action['domain'] = [('camera_id', 'in', self.ids)]
        reader_action['context'] = {'create': False}
        reader_action['name'] = _('%s Readers', self.name)
        return reader_action

    @api.model_create_multi
    def create(self, vals_list):
        new_records = self.env['cctv.camera']
        for vals in vals_list:
            new_record = super().create(vals)
            if self.env.context.get('no_hardware_commands'):
                # A migrated camera gets its readers and door from the source,
                # each carrying its own origin. Manufacturing them here would
                # leave two sets in the target with no way to tell which one
                # the historical events belong to.
                new_records += new_record
                continue
            reader_in_id = self.env['hr.rfid.reader'].sudo().create([{
                'name': _('In Reader %s', new_record.name),
                'reader_type': '0', # In reader
                'mode': '01',
                'number': 1,
                'camera_id': new_record.id,
            }])
            reader_out_id = self.env['hr.rfid.reader'].sudo().create([{
                'name': _('Out Reader %s', new_record.name),
                'reader_type': '1', # Out reader
                'mode': '01',
                'number': 2,
                'camera_id': new_record.id,
            }])
            door_id = self.env['hr.rfid.door'].sudo().create([{  # Create a door for the reader
                'name': _('Door %s', new_record.name),
                'reader_ids': [Command.link(reader_in_id.id),Command.link(reader_out_id.id)],
                'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_8').id,
                'number': 1,
            }])
            new_record.reader_ids = [Command.link(reader_in_id.id),Command.link(reader_out_id.id)]
            new_records += new_record
        return new_records

    def get_api(self):
        # Always connect to the admin-configured endpoint. The ANPR webhook
        # must never feed an IP from the (unauthenticated) event body into
        # this credentialed client — see anpr_controller for the SSRF context.
        self.ensure_one()
        return HikvisionCamera(self.ip_address, self.port, self.username, self.password)

    @api.model
    def _resolve_anpr_camera(self, device_uuid, src_ip, source_verify_on):
        """Map an ANPR webhook event to its cctv.camera.

        The camera reports its ISAPI ``subSerialNumber`` as the event
        ``deviceUUID`` (e.g. ``GN9163457``), which differs from the full
        ``serialNumber`` (e.g. ``DS-TCG406-E 20260120AIGN9163457``). Match in
        order:
          1. stored ``sub_serial_number`` == deviceUUID (canonical);
          2. ``serial_number`` == deviceUUID (firmwares that report the full
             serial as deviceUUID);
          3. only when the source IP is trusted (source verification on), the
             request IP — and learn/store the deviceUUID on that camera so
             subsequent events match directly.

        ``device_uuid`` comes from the unauthenticated event body, so it is only
        ever used to look up an existing record, never to create one; the IP
        fallback is the trusted anchor. Returns an (empty) cctv.camera recordset.
        """
        Camera = self.sudo()

        def _single(domain):
            # Never guess: an identity matching >1 camera is a duplicate
            # serial/sub-serial/IP misconfiguration — booking the event against
            # whichever row the DB returns first could attribute it to the wrong
            # camera/company. Refuse and log loudly so the duplicate gets fixed.
            recs = Camera.search(domain)
            if len(recs) > 1:
                _logger.error(
                    "ANPR identity matched %s cameras for %s (ids %s); refusing "
                    "to guess — fix the duplicate serial/sub-serial/IP.",
                    len(recs), domain, recs.ids)
                return Camera.browse()
            return recs

        camera = Camera.browse()
        if device_uuid:
            camera = _single([('sub_serial_number', '=', device_uuid)])
            if not camera:
                camera = _single([('serial_number', '=', device_uuid)])
        if not camera and source_verify_on and src_ip:
            by_ip = _single([('ip_address', '=', src_ip)])
            if by_ip:
                if device_uuid and not by_ip.sub_serial_number:
                    by_ip.sub_serial_number = device_uuid
                    _logger.info(
                        "Learned ANPR deviceUUID %s for camera %s (id %s).",
                        device_uuid, by_ip.name, by_ip.id)
                camera = by_ip
        return camera

    def action_check_connection(self):
        """
        When the camera brand is hikvision, instantiate the HikvisionCamera API class and use it.
        Update the record's connection_status and, if available, update the camera's model and serial number.
        Also, check the HTTP host configuration and time configuration.
        """
        for rec in self:
            if rec.brand == 'hikvision':
                with HikvisionCamera(rec.ip_address, rec.port, rec.username, rec.password) as cam_api:
                    result = cam_api.check_connection()
                rec._apply_connection_result(result)
                if result.get("status") == "connected":
                    rec.model = result.get("model")
                    rec.serial_number = result.get("serial")
                    rec.sub_serial_number = result.get("subserial")
                    rec.firmware = result.get("firmware")
                    rec.action_set_http_host()
                    rec.action_set_entrance_param()
                    rec.action_get_snapshot()
            else:
                rec._apply_connection_result({
                    "status": "unknown",
                    "error": _("No camera API for brand '%s'.", rec.brand),
                })
        # Feedback for the button click (single record): green when online,
        # otherwise the plain-language reason — never a raw stack/telemetry dump.
        if len(self) == 1:
            if self.connection_status == 'connected':
                return self.balloon_success(
                    title=_("Camera online"), message=self.connection_message)
            return self.balloon_warning_sticky(
                title=_("Connection check"), message=self.connection_message)
        return True

    def _apply_connection_result(self, result):
        """Store a classified connection result: status + raw detail + last-seen.

        Logs at WARNING only when the state *changes*, so a permanently
        unreachable/misconfigured camera does not spam the operator log on
        every poll (the previous code logged ERROR on each call). The
        user-facing explanation lives in the computed ``connection_message``.
        """
        self.ensure_one()
        status = result.get("status", "error")
        raw = result.get("error") or ""
        previous = self.connection_status
        vals = {
            "connection_status": status,
            "connection_error_detail": raw if status != 'connected' else False,
        }
        if status == 'connected':
            vals["last_seen"] = fields.Datetime.now()
        self.write(vals)
        if status != previous:
            if status == 'connected':
                _logger.info("Camera %s is back online.", self.name)
            else:
                _logger.warning("Camera %s connection %s: %s",
                                self.name, status, raw or "no detail")
        return True

    def action_get_http_host(self):
        """
        Retrieve the camera's HTTP host configuration, store it in server_setup as param=value lines,
        and display a user-friendly balloon message with bullet points.
        """
        for rec in self:
            if rec.brand == 'hikvision':
                with HikvisionCamera(rec.ip_address, rec.port, rec.username, rec.password) as cam_api:
                    result = cam_api.get_http_host()
                    if result.get("status") == "success":
                        config_dict = result.get("response", {})

                        # 1) Flatten nested dict keys: ANPR.detectionUpLoadPicturesType -> 'all'
                        def flatten_dict(d, parent_key='', sep='.'):
                            items = []
                            for k, v in d.items():
                                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                                if isinstance(v, dict):
                                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                                else:
                                    items.append((new_key, v))
                            return dict(items)

                        flattened = flatten_dict(config_dict)

                        # 2) Convert flattened dict to param=value lines for server_setup
                        param_value_lines = []
                        for k, v in flattened.items():
                            param_value_lines.append(f"{k}={v}")
                        rec.server_setup = "\n".join(param_value_lines)

                        # 3) Build a user-friendly balloon message (bullet‐point style)
                        #    e.g. "• ipAddress: 192.168.48.2"
                        lines = [_("HTTP Host Configuration:")]
                        for k, v in flattened.items():
                            lines.append(f"• {k}: {v}")
                        balloon_msg = "\n".join(lines)

                        # 4) Return a success balloon with the formatted message
                        # return self.balloon_success_sticky(
                        #     title=_("HTTP Host Configuration Read"),
                        #     message=balloon_msg
                        # )
                    else:
                        # On failure, return a danger balloon with the error
                        error_msg = _("Failed to read HTTP host configuration: %s") % result.get("error")
                        return self.balloon_danger_sticky(
                            title=_("HTTP Host Configuration Read Failed"),
                            message=error_msg
                        )
            else:
                rec.message_post(body="HTTP host configuration read not implemented for brand " + rec.brand)
        return True

    def action_set_http_host(self):
        """
        Задава HTTP host конфигурация на камерата, като използва стойностите от server_setup.
        server_setup трябва да бъде във формат "param=value" на отделни редове.
        Ключовете с точкова нотация се преобразуват в вложени структури.
        """

        def parse_server_setup(setup_text):
            """
            Преобразува конфигурационния текст от server_setup във вложен речников формат.
            Ако ключът съдържа точка ('.'), той се разбива и създава вложена структура.
            """
            config = {}
            for line in setup_text.splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if '.' in key:
                        parts = key.split('.')
                        d = config
                        for part in parts[:-1]:
                            if part not in d:
                                d[part] = {}
                            d = d[part]
                        d[parts[-1]] = value
                    else:
                        config[key] = value
            return config

        for rec in self:
            if rec.brand == 'hikvision':
                # Парсиране на rec.server_setup във вложен речников формат.
                config = {}
                if rec.server_setup:
                    config = parse_server_setup(rec.server_setup)

                # Приложете дефолтни стойности за липсващи ключове.
                config.setdefault('id', '1')
                # Embed the camera's sub-serial (deviceUUID) in the callback URL
                # so every notification — ANPR event AND heartbeat — carries the
                # camera's identity in the path. The webhook then identifies the
                # camera by this token, which is stable behind NAT (where the
                # source/body IPs are not). Falls back to the plain path until a
                # Check Connection has populated sub_serial_number.
                default_url = '/ipcam/anpr/event'
                if rec.sub_serial_number:
                    default_url = '/ipcam/anpr/event/%s' % rec.sub_serial_number
                config.setdefault('url', default_url)
                config.setdefault('protocolType', 'HTTP')
                config.setdefault('parameterFormatType', 'XML')
                config.setdefault('addressingFormatType', 'ipaddress')
                config.setdefault('ipAddress', get_local_ip())
                config.setdefault('portNo', '80')
                config.setdefault('userName', '')
                config.setdefault('httpAuthenticationMethod', 'none')

                # Process nested ANPR block.
                if not isinstance(config.get('ANPR'), dict):
                    config['ANPR'] = {}
                config['ANPR'].setdefault('detectionUpLoadPicturesType', 'all')

                # Process nested SubscribeEvent block.
                if not isinstance(config.get('SubscribeEvent'), dict):
                    config['SubscribeEvent'] = {}
                # Keep the default within typical ISAPI limits. The HTTP-host
                # capabilities advertise a max (180 on the DS-TCG406-E); the API
                # layer clamps this to the camera's real range before sending.
                config['SubscribeEvent'].setdefault('heartbeat', '30')
                config['SubscribeEvent'].setdefault('eventMode', 'all')

                config.setdefault('enabled', 'true' if rec.active else 'false')

                with HikvisionCamera(rec.ip_address, rec.port, rec.username, rec.password) as cam_api:
                    result = cam_api.set_http_host(config)
                    if result.get("status") == "success":
                        return self.balloon_success(
                            title=_("HTTP Host Configuration Set"),
                            message=_("HTTP host configuration set successfully.")
                        )
                    else:
                        return self.balloon_danger_sticky(
                            title=_("HTTP Host Configuration Set Failed"),
                            message=_("Failed to set HTTP host configuration: %s") % result.get("error")
                        )
            else:
                rec.message_post(body="HTTP host configuration not implemented for brand " + rec.brand)
        return True

    def action_get_entrance_param(self):
        """
        Извлича entrance параметрите от камерата и ги записва във rec.entrance_setup във формат 'param=value'.
        При това вложената структура се представя с точкова нотация.
        """

        def flatten_dict(d, parent_key='', sep='.'):
            """
            Преобразува вложен речник/списък в плосък речник с ключове във формат 'a.b.0.c'
            """
            items = []
            if isinstance(d, list):
                for index, item in enumerate(d):
                    new_key = f"{parent_key}{sep}{index}" if parent_key else str(index)
                    if isinstance(item, (dict, list)):
                        items.extend(flatten_dict(item, new_key, sep=sep).items())
                    else:
                        items.append((new_key, item))
            elif isinstance(d, dict):
                for k, v in d.items():
                    new_key = f"{parent_key}{sep}{k}" if parent_key else k
                    if isinstance(v, (dict, list)):
                        items.extend(flatten_dict(v, new_key, sep=sep).items())
                    else:
                        items.append((new_key, v))
            else:
                items.append((parent_key, d))
            return dict(items)
        for rec in self:
            if rec.brand == 'hikvision':
                with HikvisionCamera(rec.ip_address, rec.port, rec.username, rec.password) as cam_api:
                    result = cam_api.get_entrance_param()
                    if result.get("status") == "success":
                        # Плоско представяне на получената вложена структура
                        flattened = flatten_dict(result.get("response", {}))
                        # Преобразуване във формат "ключ=стойност" на отделни редове
                        param_value_lines = [f"{k}={v}" for k, v in flattened.items()]
                        rec.entrance_setup = "\n".join(param_value_lines)

                        # Показване на конфигурацията със bullet points
                        lines = [_("Entrance Configuration:")]
                        for k, v in flattened.items():
                            lines.append(f"• {k}: {v}")
                        rec.message_post(body="\n".join(lines))
                    else:
                        return self.balloon_danger_sticky(
                            title=_("Entrance Configuration Retrieval Failed"),
                            message=_("Failed to retrieve entrance configuration: %s") % result.get("error")
                        )
            else:
                rec.message_post(body="Entrance configuration retrieval not implemented for brand " + rec.brand)
        return True

    def action_set_entrance_param(self):
        """
        Задава entrance параметрите на камерата чрез API, като прочита конфигурацията от
        rec.entrance_setup (форматирана като "param=value" на редове), възстановява вложената структура
        с unflatten_dict и задава дефолтни стойности, ако липсват данни.
        """

        def unflatten_dict(flat_dict, sep='.'):
            """
            Възстановява вложена структура от плосък речник с ключове във формат 'a.b.0.c'
            """
            output = {}
            for composite_key, value in flat_dict.items():
                keys = composite_key.split(sep)
                current = output
                for i, key in enumerate(keys):
                    if key.isdigit():
                        key = int(key)
                    if i == len(keys) - 1:
                        if isinstance(current, list):
                            while len(current) <= key:
                                current.append(None)
                            current[key] = value
                        else:
                            current[key] = value
                    else:
                        next_key = keys[i + 1]
                        if isinstance(current, list):
                            # Ако текущият контейнер е списък, гарантираме че има елемент на позиция key
                            while len(current) <= key:
                                current.append({} if not next_key.isdigit() else [])
                            if not ((next_key.isdigit() and isinstance(current[key], list)) or
                                    (not next_key.isdigit() and isinstance(current[key], dict))):
                                current[key] = {} if not next_key.isdigit() else []
                            current = current[key]
                        else:
                            # Текущият контейнер е речник
                            if next_key.isdigit():
                                if key not in current or not isinstance(current.get(key), list):
                                    current[key] = []
                            else:
                                if key not in current or not isinstance(current.get(key), dict):
                                    current[key] = {}
                            current = current[key]
            return output

        def parse_entrance_setup(setup_text):
            """
            Преобразува текста от rec.entrance_setup във flat речник (ключ=стойност на редове)
            """
            flat_config = {}
            for line in setup_text.splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    flat_config[key.strip()] = value.strip()
            return flat_config

        for rec in self:
            if rec.brand == 'hikvision':
                # Прочитаме flat конфигурацията от rec.entrance_setup, ако има такава
                flat_config = {}
                if rec.entrance_setup:
                    flat_config = parse_entrance_setup(rec.entrance_setup)
                nested_config = unflatten_dict(flat_config)

                # Основни параметри
                nested_config.setdefault('laneNum', '1')
                nested_config.setdefault('bEnable', 'true')
                nested_config.setdefault('ctrlMode', '2')
                nested_config.setdefault('relateTriggerMode', '0')

                # vehControlMeasure
                if not isinstance(nested_config.get('vehControlMeasure'), dict):
                    nested_config['vehControlMeasure'] = {}
                nested_config['vehControlMeasure'].setdefault('plateNumFuzzyEnabled', 'false')
                nested_config['vehControlMeasure'].setdefault('plateNumOnlyEnable', 'true')
                nested_config['vehControlMeasure'].setdefault('plateNumColorEnable', 'false')
                nested_config['vehControlMeasure'].setdefault('personVerificationType', 'plateAssociatedFace')

                # vehInfoManagList – очакваме списък с 4 елемента
                default_info = [
                    {'vehInfoManagNum': '0', 'barrierGateOper': '0', 'relayOutAlarmEnable': 'false',
                     'upAlarmEnable': 'false', 'hostUpAlarmEnable': 'false', 'emailAlarmEnable': 'false'},
                    {'vehInfoManagNum': '1', 'barrierGateOper': '0', 'relayOutAlarmEnable': 'false',
                     'upAlarmEnable': 'false', 'hostUpAlarmEnable': 'false', 'emailAlarmEnable': 'false'},
                    {'vehInfoManagNum': '2', 'barrierGateOper': '1', 'relayOutAlarmEnable': 'false',
                     'upAlarmEnable': 'false', 'hostUpAlarmEnable': 'false', 'emailAlarmEnable': 'false'},
                    {'vehInfoManagNum': '3', 'barrierGateOper': '0', 'relayOutAlarmEnable': 'false',
                     'upAlarmEnable': 'false', 'hostUpAlarmEnable': 'false', 'emailAlarmEnable': 'false'}
                ]
                if 'vehInfoManagList' not in nested_config or not isinstance(nested_config['vehInfoManagList'], list):
                    nested_config['vehInfoManagList'] = default_info
                else:
                    for i, default_entry in enumerate(default_info):
                        if i < len(nested_config['vehInfoManagList']):
                            for key, val in default_entry.items():
                                nested_config['vehInfoManagList'][i].setdefault(key, val)
                        else:
                            nested_config['vehInfoManagList'].append(default_entry)

                # relayList – очакваме списък с 2 елемента
                default_relay = [
                    {'relayNum': '1', 'relayFunction': '1', 'relayOutTime': '350'},
                    {'relayNum': '2', 'relayFunction': '2', 'relayOutTime': '350'}
                ]
                if 'relayList' not in nested_config or not isinstance(nested_config['relayList'], list):
                    nested_config['relayList'] = default_relay
                else:
                    for i, default_entry in enumerate(default_relay):
                        if i < len(nested_config['relayList']):
                            for key, val in default_entry.items():
                                nested_config['relayList'][i].setdefault(key, val)
                        else:
                            nested_config['relayList'].append(default_entry)

                # IOAlarmList – очакваме списък с 3 елемента
                default_io = [
                    {'IOAlarmNum': '1', 'IOAlarmType': '0'},
                    {'IOAlarmNum': '2', 'IOAlarmType': '0'},
                    {'IOAlarmNum': '3', 'IOAlarmType': '0'}
                ]
                if 'IOAlarmList' not in nested_config or not isinstance(nested_config['IOAlarmList'], list):
                    nested_config['IOAlarmList'] = default_io
                else:
                    for i, default_entry in enumerate(default_io):
                        if i < len(nested_config['IOAlarmList']):
                            for key, val in default_entry.items():
                                nested_config['IOAlarmList'][i].setdefault(key, val)
                        else:
                            nested_config['IOAlarmList'].append(default_entry)

                # Останали параметри
                nested_config.setdefault('notCloseCarFollow', 'true')

                if not isinstance(nested_config.get('bigCarKeepOpen'), dict):
                    nested_config['bigCarKeepOpen'] = {}
                nested_config['bigCarKeepOpen'].setdefault('enabled', 'false')
                nested_config['bigCarKeepOpen'].setdefault('duration', '3')

                if not isinstance(nested_config.get('ParkingDetection'), dict):
                    nested_config['ParkingDetection'] = {}
                nested_config['ParkingDetection'].setdefault('enabled', 'false')
                nested_config['ParkingDetection'].setdefault('judgeTime', '5')

                if not isinstance(nested_config.get('MasterSlaveMode'), dict):
                    nested_config['MasterSlaveMode'] = {}
                nested_config['MasterSlaveMode'].setdefault('enabled', 'false')
                nested_config['MasterSlaveMode'].setdefault('Ipv4Address', '0.0.0.0')
                nested_config['MasterSlaveMode'].setdefault('portNo', '80')
                nested_config['MasterSlaveMode'].setdefault('username', 'admin')
                nested_config['MasterSlaveMode'].setdefault('uploadMode', 'mutilUpload')
                nested_config['MasterSlaveMode'].setdefault('uploadWaitTime', '500')
                nested_config['MasterSlaveMode'].setdefault('plateNumTolerantEnabled', 'false')
                nested_config['MasterSlaveMode'].setdefault('triggerSnapEnabled', 'false')
                nested_config['MasterSlaveMode'].setdefault('password', 'None')

                with HikvisionCamera(rec.ip_address, rec.port, rec.username, rec.password) as cam_api:
                    result = cam_api.set_entrance_param(nested_config)
                    if result.get("status") == "success":
                        return self.balloon_success(
                            title=_("Entrance Configuration Set"),
                            message=_("Entrance configuration set successfully.")
                        )
                    else:
                        return self.balloon_danger_sticky(
                            title=_("Entrance Configuration Set Failed"),
                            message=_("Failed to set entrance configuration: %s") % result.get("error")
                        )
            else:
                rec.message_post(body="Entrance configuration setting not implemented for brand " + rec.brand)
        return True

    def action_get_snapshot(self):
        """
        Get a snapshot from the camera (base64 encoded) and store it in the snapshot field.
        """
        for rec in self:
            if rec.brand == 'hikvision':
                with HikvisionCamera(rec.ip_address, rec.port, rec.username, rec.password) as cam_api:
                    result = cam_api.get_snapshot()
                    if result.get("status") == "success":
                        rec.snapshot = result.get("snapshot_b64")
                        rec.balloon_success(
                            title=_("Snapshot Retrieved"),
                            message=_("Snapshot retrieved and stored successfully.")
                        )
                    else:
                        rec.balloon_danger(
                            title=_("Snapshot Retrieval Failed"),
                            message=_("Snapshot retrieval failed: %s") % result.get("error")
                        )
            else:
                rec.message_post(body="Snapshot retrieval not implemented for brand " + rec.brand)
        return True

    def action_control_barrier(self, operation, gate_num):
        """
        Control the camera's barrier gate by sending an open/close command.
        :param
        operation: Стрингово описание на операцията(напр.'on', 'off', 'stop', 'locked')
        :param
        gate_num: Номер на бариерата
        """
        for rec in self:
            if rec.brand == 'hikvision':
                with HikvisionCamera(rec.ip_address, rec.port, rec.username, rec.password) as cam_api:
                    result = cam_api.barrier_gate_control(operation, gate_num)
                    rec.message_post(body="Barrier control result: " + str(result))
            else:
                rec.message_post(body="Barrier control не е имплементиран за марката " + rec.brand)
        return True

    def update_plate_in_list(self, plate_number, new_list_type):
        """
        Change the type in the list for a given registration number.
        """
        delete_result = self.delete_plate_from_list(plate_number)
        if delete_result.get("status") == "success":
            add_result = self.add_plate_to_list(plate_number, new_list_type)
            return add_result
        else:
            return {"status": "failed", "error": "Failed to delete plate before updating."}

    def notify_by_discuss(self, recipients, msg, attachments=None):
        odoobot_id = self.env.ref("base.partner_root").id
        for recipient in recipients:
            partners_to = [recipient.id]
            channel = self.env["discuss.channel"].with_user(SUPERUSER_ID).channel_get(partners_to)
            channel.message_post(
                body=msg,
                author_id=odoobot_id,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                attachments=attachments or []
            )

    def parse_event(self, files_data):
        """
        Parse the event data received from the camera.
        {'ANPR': {'ADRNo': 'unknown', 'CRIndex': '26', 'alarmDataType': '0', 'barrierGateCtrlType': '0',
                  'confidenceLevel': '100', 'country': '26', 'dangmark': 'unknown', 'decoration': 'unknown',
                  'detectDir': '8', 'detectType': '2', 'direction': 'forward', 'dwIllegalTime': '0',
                  'envprosign': 'unknown', 'featurePicFileName': '1', 'frontChild': 'unknown', 'helmet': 'unknown',
                  'illegalInfo': {'illegalCode': '0', 'illegalDescription': None, 'illegalName': 'Normal'},
                  'label': 'unknown', 'licenseBright': '104', 'licensePlate': 'CA8605CB', 'line': '1', 'listType': None,
                  'nonMotorManned': 'unknown', 'nonMotorShedUmbrella': 'unknown', 'originalLicensePlate': 'CA8605CB',
                  'pdvs': 'unknown', 'pendant': 'unknown', 'perfumeBox': 'unknown', 'pictureInfoList': {
                'pictureInfo': {'PilotRect': {'height': '0', 'width': '0', 'x': '0', 'y': '0'},
                                'VehicelWindowRect': {'height': '0', 'width': '0', 'x': '0', 'y': '0'},
                                'VicepilotRect': {'height': '0', 'width': '0', 'x': '0', 'y': '0'},
                                'absTime': '20250321131430417', 'capturePicSecurityCode': None, 'dataType': '0',
                                'fileName': 'detectionPicture.jpg', 'pId': 'FA99518774373121944546',
                                'plateRect': {'X': '426', 'Y': '560', 'height': '184', 'width': '252'},
                                'type': 'detectionPicture',
                                'vehicelRect': {'X': '48', 'Y': '0', 'height': '138', 'width': '950'}}},
                  'pilotmask': 'unknown', 'pilotsafebelt': 'unknown', 'pilotsunvisor': 'unknown',
                  'plateCharBelieve': '99,99,99,99,99,99,99,99', 'plateColor': 'unknown', 'plateType': 'unknown',
                  'playMobilePhone': 'unknown', 'relaLaneDirectionType': '0', 'smoking': 'unknown', 'speedLimit': '0',
                  'tissueBox': 'unknown', 'uphone': 'unknown', 'vehicleInfo': {
                'CarBodyFeature': {'rack': 'unknown', 'reflectiveStripe': 'unknown', 'sparetire': 'unknown',
                                   'sunRoof': 'unknown', 'words': 'unknown'},
                'CarWindowFeature': {'carCard': 'unknown', 'passCard': 'unknown', 'tempPlate': 'unknown'},
                'color': 'unknown', 'colorDepth': '0', 'index': '43', 'length': '0', 'speed': '0',
                'vehicleLogoRecog': '0', 'vehicleType': '0', 'vehicleUseType': 'unknown', 'vehileModel': '0',
                'vehileSubLogoRecog': '0'}, 'vehicleType': 'unknown', 'vicepilotMask': 'unknown',
                  'vicepilotsafebelt': 'unknown', 'vicepilotsunvisor': 'unknown'},
         'DeviceGPSInfo': {'Latitude': {'degree': '0', 'minute': '0', 'sec': '0.000000'},
                           'Longitude': {'degree': '0', 'minute': '0', 'sec': '0.000000'}, 'latitudeType': 'S',
                           'longitudeType': 'E'}, 'UUID': '6caa1332-1dd2-11b2-8bae-d3def3c1e05a',
         'VehicleGATInfo': {'colorByGAT': 'K', 'palteTypeByGAT': '42', 'plateColorByGAT': '5',
                            'vehicleTypeByGAT': 'X99'}, 'activePostCount': '12', 'carDirectionType': '0',
         'channelID': '1', 'channelName': 'IP CAPTURE CAMERA', 'dateTime': '2025-03-21T13:14:30.417+01:00',
         'detectionBackgroundImageResolution': {'height': '1552', 'width': '2688'}, 'deviceID': None,
         'deviceUUID': 'DS-TCG406-E 20240308AIFA9951877', 'dynChannelID': '1', 'eventDescription': 'ANPR',
         'eventState': 'active', 'eventType': 'ANPR', 'ipAddress': '192.168.10.64', 'ipv6Address': '::',
         'macAddress': 'bc:5e:33:4e:a4:10', 'monitorDescription': None, 'monitoringSiteID': None, 'picNum': '2',
         'protocol': 'HTTP'}
        """

        self.ensure_one()
        anpr_data = files_data.get('anpr', {})
        if anpr_data:
            event_info = anpr_data.get('ANPR', {})
            event_type = files_data.get('eventType', 'ANPR')

            date_str = anpr_data.get('dateTime')
            event_datetime = False
            if date_str:
                try:
                    dt_with_tz = datetime.fromisoformat(date_str)
                    dt_utc = dt_with_tz.astimezone(timezone.utc)
                    event_datetime = dt_utc.replace(tzinfo=None)
                except (ValueError, TypeError):
                    _logger.warning("Camera %s sent an unparseable dateTime %r; "
                                    "using server time.", self.name, date_str)
            # hr.rfid.event.system.timestamp / event.user.event_time are NOT
            # NULL; a missing/odd dateTime must fall back to now() or the
            # (public, unauthenticated) webhook 500s on the unknown-plate path.
            if not event_datetime:
                event_datetime = fields.Datetime.now()

            if event_type == 'ANPR':
                plate_number = event_info.get('licensePlate', '')
                confidenceLevel = event_info.get('confidenceLevel', 0)
                country = event_info.get('country', '')
                detectType = event_info.get('detectType', '')
                vehicleLogoRecog = event_info.get('vehicleLogoRecog', '')

                file_name = event_info.get('pictureInfoList', {}) \
                    .get('pictureInfo', {}) \
                    .get('fileName', '')

                activePostCount = anpr_data.get('activePostCount', 0)
                event_state = anpr_data.get('eventState', '')
                ipaddress = anpr_data.get('ipAddress', '')
                macAddress = anpr_data.get('macAddress', '')
                barrierGateCtrlType = event_info.get('barrierGateCtrlType', '9') #granted/denied
                # Direction lives INSIDE the <ANPR> block (event_info), not at the
                # top level — reading it from anpr_data always yielded the default
                # 'forward'. The companion raw fields (detectDir / carDirectionType /
                # relaLaneDirectionType) are recorded for diagnosis: firmware may
                # encode the real travel direction in one of those rather than in
                # <direction>.  R1 In (forward) vs R2 Out (reverse).
                direction = event_info.get('direction', 'forward')
                detect_dir = event_info.get('detectDir', '')
                rela_lane_dir = event_info.get('relaLaneDirectionType', '')
                car_dir_type = anpr_data.get('carDirectionType', '')

                # A reader (and its door) is mandatory to record either event
                # type. They are auto-created with the camera, but a manager can
                # detach/delete one — guard the index access so a live event on
                # the public webhook can't IndexError into a 500.
                if not self.reader_ids:
                    _logger.warning(
                        "Camera %s has no readers configured; cannot record the "
                        "ANPR event for plate %s.", self.name, plate_number)
                    return
                reader_in = self.reader_ids[0]
                reader_out = self.reader_ids[1] if len(self.reader_ids) > 1 else reader_in

                # търсене на собственик на регистрационния номер
                card_id = self.env['hr.rfid.card'].with_context(active_test=False).sudo().search([
                    ('number', '=', plate_number),
                    ('company_id', '=', self.company_id.id)
                ])
                snapshot_b64 = files_data.get('detectionPicture.jpg', False)
                if snapshot_b64 and snapshot_b64.startswith('data:'):
                    snapshot_b64 = snapshot_b64.split(',', 1)[1]

                if plate_number == 'unknown': # fix camera bug
                    _logger.warning('Plate number is unknown for camera %s', self.name)
                elif not card_id: # Make system event
                    # msg = _('Plate number not found in database (%s)', plate_number)
                    # attachments = [('detectionPicture.jpg', snapshot_b64)] if snapshot_b64 else []
                    # self.notify_by_discuss(self.message_partner_ids, msg, attachments)
                    ed = _('Plate number not found in database (%s), ', plate_number)
                    ed+= _('but exist in the camera memory. ') if barrierGateCtrlType == BARRIER_GATE_IN_LIST else _('nor in camera memory. ')
                    # Raw camera telemetry appended for integrator diagnosis. This is
                    # NOT user-facing copy: it is a verbatim Hikvision field dump, so
                    # it is deliberately left out of the translatable corpus —
                    # translating identifiers such as detectDir would be meaningless
                    # and the field names must stay exactly as the camera reports them.
                    ed+= (
                        "Direction: %s (detectDir: %s, carDirectionType: %s, "
                        "relaLaneDirectionType: %s), DetectType: %s, ActivePostCount: %s, "
                        "EventState: %s, IPAddress: %s, MACAddress: %s, "
                        "BarrierGateCtrlType: %s."
                    ) % (direction, detect_dir, car_dir_type, rela_lane_dir, detectType,
                         activePostCount, event_state, ipaddress, macAddress, barrierGateCtrlType)
                    sys_event_vals= {
                        'timestamp': event_datetime,
                        'event_action': '39',
                        'license_plate': plate_number,
                        'card_number': plate_number,
                        'error_description': ed,
                        'camera_id': self.id,
                        'door_id': reader_in.door_id.id,
                        'anpr_confidence': confidenceLevel,
                        'snapshot': snapshot_b64
                    }
                    new_sys_event = self.env['hr.rfid.event.system'].sudo().create([sys_event_vals])
                else: # Make User event
                    # The camera push does NOT report the allow/deny result of
                    # its local plate-list match (barrierGateCtrlType reflects
                    # physical barrier control and is '0' when the camera does
                    # not drive a barrier — see BARRIER_GATE_IN_LIST note above).
                    # Decide granted/denied from THIS camera's plate lists in
                    # Odoo instead: a plate whose card is on the camera whitelist
                    # is granted; blacklist — or no relation for this camera —
                    # is denied. card_id is a search result that may hold more
                    # than one card for the same plate number, so collapse to a
                    # single record before use. There is no unique constraint on
                    # (camera, card), so a card may carry several relations;
                    # fail safe — any blacklist relation denies, even if a
                    # whitelist one also exists.
                    card = card_id[:1]
                    rels = self.rfid_rel_ids.filtered(
                        lambda r: r.card_id.id == card.id)
                    access_granted = bool(rels) and all(
                        r.list_category == 'whitelist' for r in rels)
                    event_vals = {
                        'event_time': event_datetime,
                        'event_action': '1' if access_granted else '2',
                        'license_plate': plate_number,
                        'more_json': str(event_info),
                        'camera_id': self.id,
                        'reader_id': reader_in.id if direction == 'forward' else reader_out.id,
                        'card_id': card.id if card else False,
                        'anpr_confidence': confidenceLevel,
                        'snapshot': snapshot_b64
                    }
                    new_event = self.env['hr.rfid.event.user'].sudo().create([event_vals])

                # Only write when the value actually changes — parse_event runs
                # on every car passage and the camera is a mail.thread; an
                # unconditional write here amplified into a tracking/recompute
                # write per event on a hot path.
                behind_nat = not (ipaddress and ipaddress == self.ip_address)
                if self.behind_nat != behind_nat:
                    self.behind_nat = behind_nat

            elif event_type == 'illaccess':
                _logger.warning("Illegal access detected for camera %s", self.name)
            else:
                _logger.warning("Unknown event type: %s for camera %s", event_type, self.name)
        return True

    def add_plate_to_cam(self, plate_number, list_type):
        """
        Add a plate number to the camera's list.
        """
        for rec in self:
            if rec.brand == 'hikvision':
                with HikvisionCamera(rec.ip_address, rec.port, rec.username, rec.password) as cam_api:
                    result = cam_api.add_plate_to_list(plate_number, list_type)
                    if result.get("status") == "success":
                        return self.balloon_success_sticky(
                            title=_("Plate Added to List"),
                            message=_("Plate number added to list successfully.")
                        )
                    else:
                        return self.balloon_danger_sticky(
                            title=_("Plate Add to List Failed"),
                            message=_("Failed to add plate number to list: %s") % result.get("error")
                        )
            else:
                rec.message_post(body="Plate add to list not implemented for brand " + rec.brand)
        return True

    def remove_plate_from_cam(self, plate_number):
        """
        Remove a plate number from the camera's list.
        """
        for rec in self:
            if rec.brand == 'hikvision':
                with HikvisionCamera(rec.ip_address, rec.port, rec.username, rec.password) as cam_api:
                    result = cam_api.remove_plate_from_list(plate_number)
                    if result.get("status") == "success":
                        return self.balloon_success_sticky(
                            title=_("Plate Removed from List"),
                            message=_("Plate number removed from list successfully.")
                        )
                    else:
                        return self.balloon_danger_sticky(
                            title=_("Plate Removal from List Failed"),
                            message=_("Failed to remove plate number from list: %s") % result.get("error")
                        )
            else:
                rec.message_post(body="Plate removal from list not implemented for brand " + rec.brand)
        return True

    def add_card_id_to_list(self, card_id=None):
        """
        Add a card id to the camera's list.
        """
        card_id = card_id if isinstance(card_id, int) else card_id.id
        for cam in self:
            if card_id not in cam.rfid_card_ids.ids:
                cam.rfid_rel_ids = [Command.create({
                    'card_id': card_id,
                    'list_category': 'whitelist'
                })]
    def remove_card_id_from_list(self, card_id=None):
        """
        Remove a card id from the camera's list.
        """
        card_id = card_id if isinstance(card_id, int) else card_id.id
        for cam in self:
            if card_id in cam.rfid_card_ids.ids:
                cam.rfid_rel_ids.filtered(lambda r: r.card_id.id == card_id).unlink()

    def action_reload_whitelist(self):
        """
        Reload each whitelist plate as a separate add_plate command.
        """
        cmd_env = self.env['cctv.camera.command'].sudo()
        for cam in self:
            if cam.brand != 'hikvision':
                continue
            # Филтрираме само whitelist записи
            whitelist_rels = cam.rfid_rel_ids.filtered(
                lambda r: r.list_category == 'whitelist'
            )
            for rel in whitelist_rels:
                request_data = rel._hv_get_request_data()
                if request_data:
                    try:
                        cmd_env.create([{
                            'camera_id': rel.camera_id.id,
                            'command_type': 'add_plate',
                            'request_data': request_data,
                        }])
                    except Exception as e:
                        _logger.error("Error creating add_plate command for relation ID %s: %s", rel.id, e)
        return True





