from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class CctvCameraCommand(models.Model):
    _name = 'cctv.camera.command'
    _description = 'Camera Command for Execution'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string="Command Reference", readonly=True, copy=False,
                       default=lambda self: _('New'))
    command_type = fields.Selection([
        ('set_http_host', "Set HTTP Host"),
        ('get_snapshot', "Get Snapshot"),
        ('update_list', "Update List"),
        ('barrier_control', "Barrier Control"),
        ('add_plate', "Add Plate"),
        ('remove_plate', "Remove Plate"),
        ('set_time', "Set Time"),
        ('other', "Other"),
    ], string="Command Type", required=True, tracking=True)
    execution_time = fields.Datetime(string="Execution Time", readonly=True)
    request_data = fields.Text(string="Request Data", tracking=True,
                               help="Data sent to the camera as part of the command, e.g. in param=value per line format.")
    response_data = fields.Text(string="Response Data", tracking=True)
    camera_id = fields.Many2one('cctv.camera', string="Camera", required=True, tracking=True)
    retry_count = fields.Integer(string="Retry Count", default=0, tracking=True)
    state = fields.Selection([
        ('new', "New"),
        ('in_progress', "In Progress"),
        ('done', "Done"),
        ('error', "Error"),
    ], string="State", default='new', tracking=True)

    @api.constrains('retry_count')
    def _check_retry_count(self):
        for rec in self:
            if rec.retry_count > 5:
                raise UserError(_("Retry count cannot exceed 5."))

    @api.model_create_multi
    def create(self, vals_list):
        # Ensure that no other command is in progress for the same camera.
        for vals in vals_list:
            camera_id = vals.get('camera_id')
            if camera_id:
                existing = self.search([
                    ('camera_id', '=', camera_id),
                    ('state', 'in', ['new', 'in_progress'])
                ])
                if existing:
                    raise UserError(_("There is already a command in progress or waiting to be executed for this camera."))
        records = super().create(vals_list)
        for rec in records:
            rec.action_execute()
        return records

    def _parse_request_data(self, request_data):
        """Парсира request_data, съдържащ редове във формат 'param=value', и връща речник."""
        data = {}
        if request_data:
            for line in request_data.splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    data[key.strip()] = value.strip()
        return data

    def _execute_barrier_control(self, cam_api, params):
        """Изпълнява командата за контрол на бариерата."""
        operation = params.get('operation', 'on')
        try:
            gate_num = int(params.get('gate_num', 1))
        except ValueError:
            gate_num = 1
        return cam_api.barrier_gate_control(operation, gate_num)

    def action_execute(self):
        """
        Изпълнява командата. Методът променя състоянието на командата на 'in_progress',
        записва времето на изпълнение и извиква съответния API метод според command_type.
        При успех, състоянието се задава на 'done', в противен случай - 'error'.
        """
        for rec in self:
            if rec.state != 'new':
                continue
            rec.state = 'in_progress'
            rec.execution_time = fields.Datetime.now()
            try:
                with rec.camera_id.get_api() as cam_api:
                    params = self._parse_request_data(rec.request_data)
                    if rec.command_type == 'set_http_host':
                        result = cam_api.set_http_host(params)
                    elif rec.command_type == 'get_snapshot':
                        result = cam_api.get_snapshot()
                    elif rec.command_type == 'update_list':
                        result = cam_api.update_lists()
                    elif rec.command_type == 'barrier_control':
                        result = self._execute_barrier_control(cam_api, params)
                    elif rec.command_type == 'add_plate':
                        # При add_plate очакваме да има поне ключ 'plateNum'
                        if 'plateNum' not in params:
                            raise UserError(_("Missing required parameter 'plateNum' for add_plate command."))
                        result = cam_api.add_plate_to_list([params])
                    elif rec.command_type == 'remove_plate':
                        if 'plateNum' not in params:
                            raise UserError(_("Missing required parameter 'plateNum' for remove_plate command."))
                        result = cam_api.delete_plate_from_list([{'plateNum': params.get('plateNum')}])
                    elif rec.command_type == 'set_time':
                        result = cam_api.set_time_config(params)
                    else:
                        result = {"status": "success", "response": "Command executed."}
                rec.response_data = str(result)
                rec.state = "done" if result.get("status") == "success" else "error"
            except Exception as e:
                rec.response_data = str(e)
                rec.state = "error"
                _logger.error("Error executing command %s: %s", rec.name, e)
        return True
