from odoo.addons.hr_rfid.controllers import polimex
from odoo import fields, models, api, _, exceptions


class HrRfidCtrlIoTableRow(models.TransientModel):
    _name = 'hr.rfid.ctrl.io.table.row'
    _description = 'Controller IO Table row'

    event_codes = [
        ('1', _("Duress")),
        ('2', _("Duress Error")),
        ('3', _("Reader #1 Card OK")),
        ('4', _("Reader #1 Card Error")),
        ('5', _("Reader #1 TS Error")),
        ('6', _("Reader #1 APB Error")),
        ('7', _("Reader #2 Card OK")),
        ('8', _("Reader #2 Card Error")),
        ('9', _("Reader #2 TS Error")),
        ('10', _("Reader #2 APB Error")),
        ('11', _("Reader #3 Card OK")),
        ('12', _("Reader #3 Card Error")),
        ('13', _("Reader #3 TS Error")),
        ('14', _("Reader #3 APB Error")),
        ('15', _("Reader #4 Card OK")),
        ('16', _("Reader #4 Card Error")),
        ('17', _("Reader #4 TS Error")),
        ('18', _("Reader #4 APB Error")),
        ('19', _("Emergency Input")),
        ('20', _("Arm On Siren")),
        ('21', _("Exit Button 1")),
        ('22', _("Exit Button 2")),
        ('23', _("Exit Button 3")),
        ('24', _("Exit Button 4")),
        ('25', _("Door Overtime")),
        ('26', _("Door Forced Open")),
        ('27', _("On Delay")),
        ('28', _("Off Delay")),
    ]

    event_number = fields.Selection(
        selection=event_codes,
        string='Event Number',
        help='What the outs are set to when this event occurs',
        required=True,
        readonly=True,
    )

    # Range is from 00 to 99
    out8 = fields.Integer(string='Out8', required=True)
    out7 = fields.Integer(string='Out7', required=True)
    out6 = fields.Integer(string='Out6', required=True)
    out5 = fields.Integer(string='Out5', required=True)
    out4 = fields.Integer(string='Out4', required=True)
    out3 = fields.Integer(string='Out3', required=True)
    out2 = fields.Integer(string='Out2', required=True)
    out1 = fields.Integer(string='Out1', required=True)


class HrRfidCtrlIoTableWiz(models.TransientModel):
    _name = 'hr.rfid.ctrl.io.table.wiz'
    _description = 'Controller IO Table Wizard'

    def _default_ctrl(self):
        return self.env['hr.rfid.ctrl'].browse(self._context.get('active_ids'))

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
        required=True
    )

    io_row_ids = fields.Many2many(
        'hr.rfid.ctrl.io.table.row',
        string='IO Table',
        default=_generate_io_table,
    )

    outs = fields.Integer(
        default=_default_outs,
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