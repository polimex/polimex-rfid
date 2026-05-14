from odoo.addons.hr_rfid.controllers import polimex
from odoo import fields, models, api, _, exceptions


class HrRfidCtrlIoTableRow(models.TransientModel):
    _name = 'hr.rfid.ctrl.io.table.row'
    _description = 'Controller IO Table row'

    event_codes = [
        ('1', "Duress"),
        ('2', "Duress Error"),
        ('3', "Reader #1 Card OK"),
        ('4', "Reader #1 Card Error"),
        ('5', "Reader #1 TS Error"),
        ('6', "Reader #1 APB Error"),
        ('7', "Reader #2 Card OK"),
        ('8', "Reader #2 Card Error"),
        ('9', "Reader #2 TS Error"),
        ('10', "Reader #2 APB Error"),
        ('11', "Reader #3 Card OK"),
        ('12', "Reader #3 Card Error"),
        ('13', "Reader #3 TS Error"),
        ('14', "Reader #3 APB Error"),
        ('15', "Reader #4 Card OK"),
        ('16', "Reader #4 Card Error"),
        ('17', "Reader #4 TS Error"),
        ('18', "Reader #4 APB Error"),
        ('19', "Emergency Input"),
        ('20', "Arm On Siren"),
        ('21', "Exit Button 1"),
        ('22', "Exit Button 2"),
        ('23', "Exit Button 3"),
        ('24', "Exit Button 4"),
        ('25', "Door Overtime"),
        ('26', "Door Forced Open"),
        ('27', "On Delay"),
        ('28', "Off Delay"),
    ]

    event_number = fields.Selection(
        selection=event_codes,
        string='Event Number',
        help='What the outs are set to when this event occurs',
        required=True,
        readonly=True,
    )

    # Range is from 00 to 99
    out8 = fields.Integer(
        string='Out8', required=True,
        help="Output #8 setting for this event (0-99). Bound to a relay / output by the controller's wiring.",
    )
    out7 = fields.Integer(
        string='Out7', required=True,
        help="Output #7 setting for this event (0-99).",
    )
    out6 = fields.Integer(
        string='Out6', required=True,
        help="Output #6 setting for this event (0-99).",
    )
    out5 = fields.Integer(
        string='Out5', required=True,
        help="Output #5 setting for this event (0-99).",
    )
    out4 = fields.Integer(
        string='Out4', required=True,
        help="Output #4 setting for this event (0-99).",
    )
    out3 = fields.Integer(
        string='Out3', required=True,
        help="Output #3 setting for this event (0-99).",
    )
    out2 = fields.Integer(
        string='Out2', required=True,
        help="Output #2 setting for this event (0-99).",
    )
    out1 = fields.Integer(
        string='Out1', required=True,
        help="Output #1 setting for this event (0-99).",
    )


class HrRfidCtrlIoTableWiz(models.TransientModel):
    _name = 'hr.rfid.ctrl.io.table.wiz'
    _description = 'Controller IO Table Wizard'

    def _default_ctrl(self):
        return self.env['hr.rfid.ctrl'].browse(self.env.context.get('active_ids'))

    def _generate_io_table(self, default=False):
        rows_env = self.env['hr.rfid.ctrl.io.table.row'].sudo()
        row_len = 8 * 2  # 8 outs, 2 symbols each to display the number
        ctrl = self._default_ctrl()

        if not ctrl.io_table or len(ctrl.io_table) % row_len != 0 or default:
            # fix if the module can't read io table we use default io table
            io_table = polimex.get_default_io_table(ctrl.hw_version, ctrl.mode)
            # raise exceptions.ValidationError('Controller does now have an input/output table loaded!')
        else:
            io_table = ctrl.io_table
        rows = rows_env

        for i in range(0, len(ctrl.io_table), row_len):
            creation_dict = {'event_number': str(int(i / row_len) + 1)}
            for j in range(8, 0, -1):
                index = i + ((8 - j) * 2)
                creation_dict['out' + str(j)] = int(io_table[index:index + 2], 16)
            rows += rows_env.create(creation_dict)

        return rows

    def _default_outs(self):
        ctrl = self._default_ctrl()
        if ctrl.is_relay_ctrl(): # Relay controllers
            return 4
        return self._default_ctrl().outputs

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        default=_default_ctrl,
        required=True,
        help="Controller being edited. Set automatically from the active record when the wizard opens.",
    )

    io_row_ids = fields.Many2many(
        'hr.rfid.ctrl.io.table.row',
        string='IO Table',
        default=_generate_io_table,
        help="One row per event code (Duress, Card OK, etc.) with the values written to each of the 8 outputs when that event fires.",
    )

    outs = fields.Integer(
        default=_default_outs,
        help="Number of output columns shown in the table (4 for relay controllers, otherwise inherited from the controller's hardware capabilities).",
    )

    def load_system_defaults(self):
        self.io_row_ids = self._generate_io_table(default=True)
        act_id = self.env.ref('hr_rfid.hr_rfid_controller_io_table_wiz_action').sudo().read()[0]
        act_id['res_id'] = self.id
        return act_id

    def save_table(self):
        self.ensure_one()

        new_io_table = ''

        for row in self.io_row_ids:
            outs = [row.out8, row.out7, row.out6, row.out5, row.out4, row.out3, row.out2, row.out1]
            for out in outs:
                if out < 0 or out > 99:
                    raise exceptions.ValidationError(
                        _('%d is not a valid number for the io table. Valid values range from 0 to 99') % out
                    )
                new_io_table += '%02X' % out

        self.controller_id.change_io_table(new_io_table)