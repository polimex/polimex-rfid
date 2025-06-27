from odoo import fields, models, api


class HrRfidCtrlAlarmGroup(models.Model):
    _name = 'hr.rfid.ctrl.alarm.group'
    _description = 'Alarm system groups'
    _inherit = ['mail.thread', 'balloon.mixin']

    name = fields.Char(
        required=True,
        help="Enter a descriptive name for this alarm group (e.g., 'First Floor Alarms', 'Warehouse Security', 'Office Area'). Groups help you manage multiple alarms together."
    )
    color = fields.Integer(
        'Color Index', 
        default=0,
        help="Choose a color to visually distinguish this group in the hierarchy view. This helps you quickly identify different security zones or areas."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help="The company that owns this alarm group. Used in multi-company setups to separate alarm management by organization."
    )
    state = fields.Selection([
        ('no_alarm', 'No Alarm functionality'),  # 64 ON
        ('arm', 'Armed'),  # 64 ON
        ('disarm', 'Disarmed'),  # 64 OFF
        ('mixed', 'Partially armed'),  # 64 OFF
    ], 
        compute='_compute_states', 
        tracking=True, 
        store=True,
        help="Overall security status of all alarms in this group:\n"
             "• No Alarm functionality - No active alarms in this group\n"
             "• Armed - All alarms are armed and monitoring\n"
             "• Disarmed - All alarms are disarmed\n"
             "• Partially armed - Some alarms are armed, others are disarmed"
    )
    parent_id = fields.Many2one(
        comodel_name='hr.rfid.ctrl.alarm.group',
        help="Parent group for creating hierarchical alarm structures. For example:\n"
             "• Building → Floor → Room\n"
             "• Campus → Building → Department\n"
             "This allows you to arm/disarm entire areas at once."
    )
    child_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.alarm.group',
        inverse_name='parent_id',
        help="Sub-groups under this group. When you arm/disarm this group, all child groups will also be armed/disarmed. Useful for managing large facilities with multiple security zones."
    )
    alarm_line_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.alarm',
        inverse_name='alarm_group_id',
        required=True,
        help="Individual alarm sensors that belong to this group. You can:\n"
             "• Add multiple sensors from different controllers\n"
             "• Arm/disarm all sensors at once\n"
             "• Monitor the combined status of all sensors\n"
             "Example: Group all window sensors in 'Perimeter Security'"
    )

    def create_child(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Alarm Group',
            'res_model': 'hr.rfid.ctrl.alarm.group',
            'view_mode': 'form',
            'context': {'default_parent_id': self.id},
        }

    def open_alarm_line_list_action(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Alarm Lines',
            'res_model': 'hr.rfid.ctrl.alarm',
            'view_mode': 'list,form',
            'domain': [('alarm_group_id', 'in', self.ids)],
            'context': {'create': False},
        }
    # # @api.depends()
    # def _compute_children(self):
    #     for g in self:
    #         result = self.env['hr.rfid.ctrl.alarm.group'].search

    @api.depends('alarm_line_ids.state', 'alarm_line_ids.armed')
    def _compute_states(self):
        for g in self:
            armed = any([l.armed == 'arm' for l in g.alarm_line_ids])
            disarmed = any([l.armed == 'disarm' and l.state != 'disabled' for l in g.alarm_line_ids])
            if armed and disarmed:
                g.state = 'mixed'
            elif armed and not disarmed:
                g.state = 'arm'
            elif not armed and disarmed:
                g.state = 'disarm'
            else:
                g.state = 'no_alarm'

    def disarm(self):
        res = None
        for g in self:
            res = g.alarm_line_ids.disarm()
            g.child_ids.alarm_line_ids.disarm()
        if res:
            return res

    def arm(self):
        res = None
        for g in self:
            res = g.alarm_line_ids.arm()
            g.child_ids.alarm_line_ids.arm()
        if res:
            return res
