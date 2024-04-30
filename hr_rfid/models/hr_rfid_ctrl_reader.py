from odoo import fields, models, api, _, SUPERUSER_ID, exceptions


class HrRfidReader(models.Model):
    _name = 'hr.rfid.reader'
    _inherit = ['mail.thread']
    _description = 'Reader'

    reader_types = [
        ('0', _('In')),
        ('1', _('Out')),
    ]

    reader_modes = [
        ('00', _('Unknown')),
        ('01', _('Card Only')),
        ('02', _('Card and Pin')),
        ('03', _('Card and Workcode')),
        ('04', _('Card or Pin')),
    ]

    name = fields.Char(
        string='Reader name',
        help='Label to differentiate readers',
        default='Reader',
        tracking=True,
    )

    number = fields.Integer(
        string='Number',
        help='Number of the reader on the controller',
        index=True,
    )

    # TODO Rename to just 'type'
    reader_type = fields.Selection(
        selection=reader_types,
        string='Reader type',
        help='Type of the reader',
        required=True,
        default='00',
    )

    mode = fields.Selection(
        selection=reader_modes,
        string='Reader mode',
        help='Mode of the reader',
        default='01',
        required=True,
    )

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        string='Controller',
        help='Controller that manages the reader',
        required=True,
        ondelete='cascade',
    )
    webstack_id = fields.Many2one(
        comodel_name='hr.rfid.webstack',
        string='Module',
        related='controller_id.webstack_id',
    )
    user_event_ids = fields.One2many(
        'hr.rfid.event.user',
        'reader_id',
        string='Events',
        help='Events concerning this reader',
    )

    door_ids = fields.Many2many(
        'hr.rfid.door',
        'hr_rfid_reader_door_rel',
        'reader_id',
        'door_id',
        string='Doors',
        help='Doors the reader opens',
        ondelete='cascade',
    )

    door_id = fields.Many2one(
        'hr.rfid.door',
        string='Door',
        compute='_compute_reader_door',
        inverse='_inverse_reader_door',
    )

    door_count = fields.Char(compute='_compute_counts')
    user_event_count = fields.Char(compute='_compute_counts')

    @api.depends('door_ids', 'user_event_ids')
    def _compute_counts(self):
        for r in self:
            r.door_count = len(r.door_ids)
            r.user_event_count = len(r.user_event_ids)

    @api.depends('door_id.name')
    def _compute_reader_name(self):
        for record in self:
            record.name = record.door_id.name + ' ' + \
                          self.reader_types[int(record.reader_type)][1] + \
                          ' Reader'

    @api.depends('door_ids')
    def _compute_reader_door(self):
        for reader in self:
            if not reader.controller_id.is_relay_ctrl() and len(reader.door_ids) == 1:
                reader.door_id = reader.door_ids

    def _inverse_reader_door(self):
        for reader in self:
            reader.door_ids = reader.door_id

    def write(self, vals):
        for r in self:
            if ('mode' in vals and r.mode != '00' and vals.get('mode') == '00'):
                raise exceptions.ValidationError(
                    _("You can not change the reader mode to this value!")
                )
        if 'mode' not in vals or ('no_d6_cmd' in vals and vals['no_d6_cmd'] is True):
            if 'no_d6_cmd' in vals:
                vals.pop('no_d6_cmd')
            super(HrRfidReader, self).write(vals)
            return

        for reader in self:
            if 'no_d6_cmd' in vals:
                vals.pop('no_d6_cmd')
            old_mode = reader.mode
            super(HrRfidReader, reader).write(vals)
            new_mode = reader.mode

            if old_mode != new_mode:
                ctrl = reader.controller_id
                cmd_env = self.env['hr.rfid.command'].with_user(SUPERUSER_ID)

                data = ''
                for r in ctrl.reader_ids:
                    data = data + str(r.mode) + '0100'

                cmd_env.create({
                    'webstack_id': ctrl.webstack_id.id,
                    'controller_id': ctrl.id,
                    'cmd': 'D6',
                    'cmd_data': data,
                })

    def button_door_list(self):
        self.ensure_one()
        return {
            'name': _('Doors using {}').format(self.name),
            'view_mode': 'tree,form',
            'res_model': 'hr.rfid.door',
            'domain': [('id', 'in', [d.id for d in self.door_ids])],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }

    def button_event_list(self):
        self.ensure_one()
        return {
            'name': _('Events from {}').format(self.name),
            'view_mode': 'tree,form',
            'res_model': 'hr.rfid.event.user',
            'domain': [('reader_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }
