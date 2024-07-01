import logging

from odoo import fields, models, api, _, SUPERUSER_ID

_logger = logging.getLogger(__name__)


class HrRfidCtrlAlarm(models.Model):
    _name = 'hr.rfid.ctrl.alarm'
    _inherit = ['mail.thread', 'balloon.mixin']
    _description = 'Controller Alarm Lines'
    _order = 'controller_id, line_number'

    name = fields.Char(required=True, help="Friendly name for this line")

    line_number = fields.Integer(help="Line number in the controller")

    state = fields.Selection([
        ('unknown', 'Unknown'),
        ('disabled', 'Disabled'),
        ('short', 'Short'),
        ('normal', 'Normal'),
        ('s1', 'Sensor 1'),
        ('s2', 'Sensor 2'),
        ('s12', 'Sensor 1 and 2'),
        ('open', 'Open'),
      ],
        compute='_compute_states',
        tracking=True,
        compute_sudo=True,
        help="Alarm line state",
    )

    armed = fields.Selection([
        ('no_alarm', 'No Alarm functionality'),  # 64 ON
        ('arm', 'Armed'),  # 64 ON
        ('disarm', 'Disarmed'),  # 64 OFF
        ], compute='_compute_armed', compute_sudo=True, store=True)

    siren_state = fields.Boolean(
        help='Alarm Siren state',
        related='controller_id.siren_state'
    )

    controller_id = fields.Many2one(
        comodel_name='hr.rfid.ctrl',
        string='Controller',
        help='Controller that manages the alarm line',
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    control_output = fields.Integer()

    door_id = fields.Many2one(
        comodel_name='hr.rfid.door',
        help='Door related to this alarm line'
    )

    user_event_count = fields.Integer(
        compute='_compute_counters'
    )
    system_event_count = fields.Integer(
        compute='_compute_counters'
    )

    alarm_group_id = fields.Many2one(
        comodel_name='hr.rfid.ctrl.alarm.group'
    )

    def _compute_counters(self):
        for l in self:
            l.user_event_count = self.env['hr.rfid.event.user'].search_count([('alarm_line_id', '=', l.id)])
            l.system_event_count = self.env['hr.rfid.event.system'].search_count([('alarm_line_id', '=', l.id)])

    @api.depends('controller_id.alarm_line_states')
    def _compute_states(self):
        for l in self:
            armed, state = l.controller_id._get_alarm_line_state(l.line_number)
            # _logger.info('%d line in armed:%s and state:%s', l.line_number, armed, state)
            # if state == 'disabled':
            #     l.armed = 'no_alarm'
            # else:
            #     l.armed = armed
            l.state = state
    @api.depends('controller_id.alarm_line_states')
    def _compute_armed(self):
        for l in self:
            armed, state = l.controller_id._get_alarm_line_state(l.line_number)
            # _logger.info('%d line in armed:%s and state:%s', l.line_number, armed, state)
            if state == 'disabled':
                l.armed = 'no_alarm'
            else:
                l.armed = armed
            # l.state = state

    def return_action_to_open(self):
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        dom = self.env.context.get('dom')
        key = self.env.context.get('key')
        op = self.env.context.get('op')
        if dom:
            domain = dom
        elif key and op:
            domain = [(key, op, self.id)]
        else:
            domain = [('alarm_line_id', '=', self.id)]
        model = 'hr_rfid'
        if xml_id:
            res = self.env['ir.actions.act_window']._for_xml_id(f"{model}.{xml_id}_action")
            res.update(
                context=dict(self.env.context, default_alarm_line_id=self.id, group_by=False),
                domain=domain
            )
            return res
        return False


    # Commands to lines

    def disarm(self):
        for l in self:
            cmd_id = l.controller_id.change_output_state(l.control_output, 0, 99)

        return self.balloon_success(
            title=_('Disarm command success'),
            message=_('Success Line(s) Disarm')
        )

    def arm(self):
        for l in self:
            cmd_id = l.controller_id.change_output_state(l.control_output, 1, 99)

        return self.balloon_success(
            title=_('Arm command success'),
            message=_('Success Line(s) Arm')
        )

    def siren_off(self):
        for s in self:
            s.controller_id.with_user(SUPERUSER_ID).siren_state = False
        return self.balloon_success(
            title=_('Siren Control'),
            message=_('Siren turned Off successful')
        )

    def siren_on(self):
        for s in self:
            s.controller_id.with_user(SUPERUSER_ID).siren_state = True
        return self.balloon_success(
            title=_('Siren Control'),
            message=_('Siren turned On successful')
        )
