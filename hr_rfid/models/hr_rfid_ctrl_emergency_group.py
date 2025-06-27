from odoo import fields, models, api, _, SUPERUSER_ID


class EmergencyGroup(models.Model):
    _name = 'hr.rfid.ctrl.emergency.group'
    _inherit = ['mail.thread', 'balloon.mixin']
    _description = 'Emergency signal distribution group'

    name = fields.Char(
        default='Emergency Floor 1',
        tracking=True,
        help="Name of the emergency group (e.g., 'Emergency Floor 1', 'Building A Emergency'). "
             "This helps identify which area or set of controllers this group manages."
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        groups='base.group_multi_company',
        default=lambda self: self.env.company,
        help="Company that owns this emergency group. Used to separate emergency groups "
             "between different companies in a multi-company setup."
    )

    controller_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl',
        inverse_name='emergency_group_id',
        tracking=True,
        help="List of controllers that belong to this emergency group. When emergency mode "
             "is activated, all controllers in this group will switch to emergency state together."
    )
    state = fields.Selection([
        ('normal', 'Normal'),
        ('emergency', 'Emergency')
    ],  compute='_compute_state',
        inverse='_inverse_state',
        tracking=True,
        help="Current state of the emergency group:\n"
             "• Normal: All controllers operating normally\n"
             "• Emergency: Emergency mode activated - doors may unlock or follow special rules"
    )

    @api.depends('controller_ids.emergency_state', 'controller_ids.input_states')
    def _compute_state(self):
        for g in self:
            new_state = any([c.emergency_state != 'off' for c in g.controller_ids]) and 'emergency' or 'normal'
            if g.state != new_state:
                g._internal_state_change_call(new_state)
            g.state = new_state

    def _inverse_state(self):
        for g in self:
            if g.state == 'normal':
                ctrl_ids = g.controller_ids.with_user(SUPERUSER_ID).filtered(lambda c: c.emergency_state == 'soft')
                ctrl_ids.emergency_state = 'off'
            if g.state == 'emergency':
                ctrl_ids = g.controller_ids.with_user(SUPERUSER_ID).filtered(lambda c: c.emergency_state == 'off')
                ctrl_ids.emergency_state = 'soft'

    def emergency_on(self):
        for g in self:
            g.state = 'emergency'
        return self.balloon_success(
            title=_("The group turn on Emergency Mode Manually"),
            message=_("This will take time. For more information check controller's commands")
        )

    def emergency_off(self):
        for g in self:
            g.state = 'normal'
        return self.balloon_success(
            title=_("The group turn off Emergency Mode Manually"),
            message=_("This will take time. For more information check controller's commands")
        )

    def _internal_state_change_call(self, state):
        pass