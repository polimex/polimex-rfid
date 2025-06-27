from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


class HrRfidCtrlAlarm(models.Model):
    _name = 'hr.rfid.ctrl.alarm'
    _inherit = ['mail.thread', 'balloon.mixin']
    _description = 'Controller Alarm Lines'
    _order = 'controller_id, line_number'

    name = fields.Char(
        required=True, 
        help="Enter a descriptive name for this alarm sensor (e.g., 'Main Entrance Motion Detector', 'Window Sensor - Office 1'). This name helps you quickly identify which sensor triggered an alarm."
    )

    line_number = fields.Integer(
        help="The physical input number on the controller where this sensor is connected (1-16). Each controller has numbered terminals for connecting alarm sensors."
    )

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
        help="Current status of the alarm sensor:\n"
             "• Unknown - Communication lost with sensor\n"
             "• Disabled - Sensor is turned off\n"
             "• Short - Wiring problem detected (short circuit)\n"
             "• Normal - Everything is OK, no alarm\n"
             "• Sensor 1/2 - Motion or contact detected\n"
             "• Open - Wiring problem detected (open circuit)",
    )

    armed = fields.Selection([
        ('no_alarm', 'No Alarm functionality'),  # 64 ON
        ('arm', 'Armed'),  # 64 ON
        ('disarm', 'Disarmed'),  # 64 OFF
        ], 
        compute='_compute_armed', 
        compute_sudo=True, 
        store=True,
        help="Security status of this alarm line:\n"
             "• No Alarm functionality - This line is not configured for alarm monitoring\n"
             "• Armed - Actively monitoring for intrusions (any sensor trigger will raise an alarm)\n"
             "• Disarmed - Temporarily disabled (sensor triggers will be ignored)"
    )

    enableAC = fields.Boolean(
        string="Integrate with Access control",
        help="When enabled, this alarm line will work together with door access control:\n"
             "• Automatically disarms when authorized person enters\n"
             "• Re-arms after the door is closed\n"
             "• Useful for motion detectors near controlled doors",
        default=False,
        tracking = True
    )
    enableDC = fields.Boolean(
        string="Include Door contact",
        help="Monitor the door's open/closed status as part of this alarm:\n"
             "• When armed, an open door will trigger the alarm\n"
             "• Useful for securing doors outside business hours\n"
             "• Works with magnetic door contacts",
        default=False,
        tracking = True
    )
    enabled = fields.Boolean(
        default=False,
        help="Master switch for this alarm line:\n"
             "• ON - The sensor is active and can trigger alarms\n"
             "• OFF - The sensor is completely disabled\n"
             "Note: Even when enabled, you still need to ARM the line for it to trigger alarms",
        tracking=True
    )

    siren_state = fields.Boolean(
        help="Shows whether the alarm siren is currently sounding:\n"
             "• ON - Siren is active (loud alarm sound)\n"
             "• OFF - Siren is silent\n"
             "The siren automatically activates when an armed sensor is triggered",
        related='controller_id.siren_state'
    )

    controller_id = fields.Many2one(
        comodel_name='hr.rfid.ctrl',
        string='Controller',
        help="The RFID controller device that monitors this alarm sensor. Each controller can manage multiple alarm lines and is usually installed in a secure location.",
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    control_output = fields.Integer(
        help="Technical field: The output number used to arm/disarm this line remotely"
    )

    door_id = fields.Many2one(
        comodel_name='hr.rfid.door',
        help="Link this alarm to a specific door for integrated security:\n"
             "• The alarm can automatically arm/disarm based on door access\n"
             "• Door events and alarm events will be connected\n"
             "• Useful for motion sensors protecting door areas"
    )

    user_event_count = fields.Integer(
        compute='_compute_counters',
        help="Number of alarm events triggered by user actions (e.g., motion detected, door opened while armed)"
    )
    system_event_count = fields.Integer(
        compute='_compute_counters',
        help="Number of technical events for this alarm line (e.g., sensor faults, communication errors, arm/disarm actions)"
    )

    alarm_group_id = fields.Many2one(
        comodel_name='hr.rfid.ctrl.alarm.group',
        help="Assign this alarm to a group for easier management:\n"
             "• Arm/disarm multiple alarms at once\n"
             "• Organize alarms by building area or security zone\n"
             "• Create hierarchical alarm structures (e.g., Floor > Room > Sensor)"
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

    def write(self, vals):
        res = super(HrRfidCtrlAlarm, self).write(vals)
        if not self.env.context.get('from_controller', False) and set(vals).intersection({'enableAC', 'enableDC', 'enabled'}):
            self.controller_id.write_alarm_line_setup()
        for l in self:
            if set(vals).intersection({'enableAC', 'enableDC', 'enabled', 'state', 'armed'}):
                tmp = l.door_id and l.door_id._compute_alarm_state()
                tmp = l.alarm_group_id and l.alarm_group_id._compute_states()
        return res
