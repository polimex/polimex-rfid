from odoo import fields, models, api


class HrRfidCtrlAlarmGroup(models.Model):
    _name = 'hr.rfid.ctrl.alarm.group'
    _description = 'Alarm system groups'
    _inherit = ['mail.thread', 'balloon.mixin']

    name = fields.Char()
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)
    state = fields.Selection([
        ('no_alarm', 'No Alarm functionality'),  # 64 ON
        ('arm', 'Armed'),  # 64 ON
        ('disarm', 'Disarmed'),  # 64 OFF
        ('mixed', 'Partially armed'),  # 64 OFF
    ], compute='_compute_states', tracking=True, store=True)
    parent_id = fields.Many2one(comodel_name='hr.rfid.ctrl.alarm.group')
    child_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.alarm.group',
        inverse_name='parent_id',
        # compute='_compute_children'
    )
    alarm_line_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.alarm',
        inverse_name='alarm_group_id'
    )

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
