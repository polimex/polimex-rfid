import threading

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError
import logging
import json

from odoo.modules.registry import Registry

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
    execution_time = fields.Datetime(
        string="Execution Time",
        readonly=True,
        help="Timestamp the command was successfully delivered to the camera. Empty while the command is queued or has failed.",
    )
    request_data = fields.Text(string="Request Data", tracking=True,
                               help="Data sent to the camera as part of the command, e.g. in param=value per line format.")
    response_data = fields.Text(
        string="Response Data",
        tracking=True,
        help="Raw response returned by the camera, kept for audit / debugging.",
    )
    camera_id = fields.Many2one(
        comodel_name='cctv.camera',
        required=True,
        ondelete='cascade',
        index=True,
        help="Camera this command targets. If the camera is deleted, queued commands cascade-delete with it.",
    )
    retry_count = fields.Integer(
        string="Retry Count",
        default=0,
        tracking=True,
        help="How many times this command has been retried. Capped at 5 — beyond that the command stays in Error state and must be re-sent manually.",
    )
    state = fields.Selection(
        [
            ('new', "New"),
            ('in_progress', "In Progress"),
            ('done', "Done"),
            ('error', "Error"),
        ],
        string="State", default='new', tracking=True,
        help="Lifecycle of the command — New: queued, not yet sent. In Progress: handler is currently delivering. Done: camera acknowledged. Error: delivery failed (see Response Data). Use the Restart Sending server action to requeue an Error command.",
    )

    @api.constrains('retry_count')
    def _check_retry_count(self):
        for rec in self:
            if rec.retry_count > 5:
                raise UserError(_("Retry count cannot exceed 5."))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get('no_hardware_commands'):
            # Defence in depth. queue_send registers a postcommit hook, and a
            # postcommit hook SURVIVES a savepoint rollback: rollback() calls
            # cr.clear() (sql_db.py:137-140) and clear() only drops precommit
            # callbacks (sql_db.py:188-193). Guarding just the callers would
            # still let a rolled-back import phase fire at the hardware.
            return records
        # Ensure that no other command is in progress for the same camera.
        for vals in vals_list:
            camera_id = vals.get('camera_id')
            existing = False
            if camera_id:
                existing = self.search([
                    ('camera_id', '=', camera_id),
                    ('state', 'in', ['in_progress'])
                ])
            if camera_id and not existing:
                records.filtered(lambda r: r.camera_id.id == camera_id).queue_send()
        return records

    def queue_send(self):
        if getattr(threading.current_thread(), 'testing', False):
            self.action_execute()
            return

        cmd_ids = self.ids
        dbname = self.env.cr.dbname
        _context = self.env.context

        @self.env.cr.postcommit.add
        def send_commands_with_new_cursor():
            db_registry = Registry(dbname)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, _context)
                env['cctv.camera.command'].sudo().browse(cmd_ids).action_execute()

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

    #: How many identical consecutive refusals from one camera stop the rest
    #: of its plate commands in the same batch. Reloading a 1394-plate list
    #: against a camera that rejects the very MECHANISM produced 1394
    #: identical ERROR lines - the operator read one failure a thousand
    #: times over, and the camera absorbed a thousand pointless requests.
    PLATE_FAILURE_STREAK_LIMIT = 3

    def action_execute(self):
        """
        Изпълнява командата. Методът променя състоянието на командата на 'in_progress',
        записва времето на изпълнение и извиква съответния API метод според command_type.
        При успех, състоянието се задава на 'done', в противен случай - 'error'.
        """
        streaks = {}       # camera_id -> [last_error, count]
        stopped = {}       # camera_id -> the error that repeated
        plate_types = ('add_plate', 'remove_plate')
        for rec in self:
            if rec.state != 'new':
                continue
            if rec.command_type in plate_types and rec.camera_id.id in stopped:
                # The camera is refusing the mechanism itself, not this
                # particular plate - hammering it with the rest of the batch
                # would repeat the same refusal per record.
                rec.state = 'error'
                rec.response_data = _(
                    "Not sent: the camera refused %(limit)s identical plate "
                    "commands in a row, so the rest of this batch was stopped. "
                    "First answer: %(error)s",
                    limit=self.PLATE_FAILURE_STREAK_LIMIT,
                    error=stopped[rec.camera_id.id])
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
                shape = result.get("shape_used") if isinstance(result, dict) else None
                if shape and shape != rec.camera_id.lp_record_shape:
                    # The ladder discovered what this firmware accepts; keep it
                    # on the camera so the rest of the plates go straight
                    # through instead of re-earning the same refusals.
                    rec.camera_id.lp_record_shape = shape
                    rec.camera_id.message_post(body=_(
                        "The camera refused part of the plate record and the "
                        "record was sent again without it. From now on plates "
                        "go to this camera as: %(shape)s. Entry and exit "
                        "decisions are unaffected.",
                        shape=dict(rec.camera_id._fields['lp_record_shape']
                                   .get_description(rec.env)['selection'])[shape]))
            except Exception as e:
                rec.response_data = str(e)
                rec.state = "error"
                _logger.error("Error executing command %s: %s", rec.name, e)
            if rec.command_type in plate_types:
                cam_id = rec.camera_id.id
                if rec.state == 'error':
                    error_text = rec.response_data or ''
                    streak = streaks.setdefault(cam_id, [None, 0])
                    streak[1] = streak[1] + 1 if streak[0] == error_text else 1
                    streak[0] = error_text
                    if streak[1] >= self.PLATE_FAILURE_STREAK_LIMIT:
                        stopped[cam_id] = error_text[:300]
                        _logger.error(
                            "Camera %s refuses its plate commands with the same "
                            "answer %s time(s) in a row; stopping the rest of "
                            "this batch. Answer: %s",
                            rec.camera_id.display_name, streak[1], streak[0])
                else:
                    streaks.pop(cam_id, None)
        return True
