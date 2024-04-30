from odoo import fields, models, api, _, exceptions
from odoo.exceptions import ValidationError
import math

DEFAULT_TS_LINE = '''01
                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00
                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00 
                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00
                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00
                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00
                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00
                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00
                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00 00
                '''.replace(' ', '').replace('\n', '')


class HrRfidTimeSchedule(models.Model):
    _name = 'hr.rfid.time.schedule'
    _inherit = ['mail.thread']
    _description = 'Time Schedule'

    name = fields.Char(
        string='Name',
        help='Label for the time schedule',
        required=True,
        tracking=True,
    )

    number = fields.Integer(
        string='TS Number',
        required=True,
        readonly=True,
    )

    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)

    is_empty = fields.Boolean(
        compute='_compute_is_empty'
    )

    ts_data = fields.Char(
        default=DEFAULT_TS_LINE
    )

    access_group_door_ids = fields.One2many(
        'hr.rfid.access.group.door.rel',
        'time_schedule_id',
        string='Access Group/Door Combinations',
        help='Which doors use this time schedule in which access group',
    )

    controller_ids = fields.Many2many(
        comodel_name='hr.rfid.ctrl',
        # compute='_compute_controllers_ids'
    )

    # @api.depends('access_group_door_ids')
    # def _compute_controllers_ids(self):
    #     for ts in self:
    #         ctrl_ids = ts.access_group_door_ids.mapped(lambda rel: rel.door_id.controller_id)
    #         ts.sudo().write({'controller_ids': [(6, 0, ctrl_ids.mapped('id'))]})

    @api.depends('ts_data')
    def _compute_is_empty(self):
        for ts in self:
            ts.is_empty = len(ts.ts_data[2:].replace('0', '')) == 0

    def _get_day(self, day=None):
        self.ensure_one()
        if day and day > 7:
            raise exceptions.ValidationError(_('The requested day is not in the range!'))
        if day is None:
            return self.ts_data.replace(' ', '').replace('\n', '')[2:]
        else:
            return self.ts_data.replace(' ', '').replace('\n', '')[2 + day * 32:1 + day * 32 + 32]

    def _get_interval_from_day_str(self, day: int, number: int):
        self.ensure_one()
        return self._get_day(day)[number * 8: number * 8 + 8]

    def _get_interval_from_day_tuple(self, day: int, number: int):
        self.ensure_one()
        interval = self._get_interval_from_day_str(day, number)
        return (int(interval[:2]) + int(interval[2:4]) / 60, int(interval[4:6]) + int(interval[6:8]) / 60)

    def reset_ts_data(self):
        for ts in self:
            ts.ts_data = '%02X' % ts.number + DEFAULT_TS_LINE[2:]
            ts.controller_ids.write_ts(ts.ts_data)

    # ORM
    def unlink(self):
        raise exceptions.ValidationError(_('Cannot delete time schedules!'))

    # Installation helpers

    @api.model
    def set_company_ts(self):
        # .with_context(force_company=vals['company_id'])
        for company_id in self.env['res.company'].sudo().search([]):
            if self.env['hr.rfid.time.schedule'].sudo().search_count([('company_id', '=', company_id.id)]) == 0:
                self.env['hr.rfid.time.schedule'].sudo().create(
                    [{
                        'name': i and "TS %02d" % (i) or _("Not using TS"),
                        'number': i,
                        'company_id': company_id.id
                    } for i in range(16)]
                )


class HrRfidTimeScheduleWizDayLine(models.TransientModel):
    _name = 'hr.rfid.ctrl.ts.line'
    _description = "Time Schedule line Wizard"
    _order = 'day'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name')
    begin = fields.Float(
        help='The begin time of the interval'
    )
    end = fields.Float(
        help='The end time of the interval'
    )
    number = fields.Integer(
        readonly=True,
        help='Number of the interval in the day'
    )
    day_number = fields.Integer(readonly=True)
    day = fields.Selection(
        selection=[
            ('0', 'Monday'),
            ('1', 'Tuesday'),
            ('2', 'Wednesday'),
            ('3', 'Thursday'),
            ('4', 'Friday'),
            ('5', 'Saturday'),
            ('6', 'Sunday'),
            ('7', 'Holiday')
        ],
        string="Day",
        help="The day for this interval",
        readonly=True
    )
    week_id = fields.Many2one(
        comodel_name='hr.rfid.ctrl.ts.week.wiz'
    )

    @api.constrains('begin', 'end', 'number')
    def _check_description(self):
        for record in self:
            if 0 > record.begin > 24:
                raise ValidationError(_("Begin is not in range"))
            if 0 > record.end > 24:
                raise ValidationError(_("End is not in range"))
            if 0 > record.number > 3:
                raise ValidationError(_("The number is not in range"))
            if record.begin >= record.end != 0:
                raise ValidationError(_("The begin time have to be before end time"))

    @api.depends('day', 'number', )
    def _compute_display_name(self):
        for line in self:
            line.display_name = f"{line.day}-{line.number}"

    @api.model
    def _get_float_to_str(self, f: float):
        frac, whole = math.modf(f)
        return '%02d%02d' % (int(whole), int(frac * 60))

    def get_interval_str(self):
        self.ensure_one()
        return self._get_float_to_str(self.begin) + self._get_float_to_str(self.end)

    def get_set_str(self):
        ordered_self = self.sorted(key=lambda i: i.day + str(i.number))
        return ''.join([i.get_interval_str() for i in ordered_self])


class HrRfidTimeScheduleWizWeek(models.TransientModel):
    _name = 'hr.rfid.ctrl.ts.week.wiz'
    _description = 'Time Schedule Week Wizard'

    @api.model
    def _default_interval_ids(self):
        ts_id = self.env['hr.rfid.time.schedule'].browse(self.env.context.get('active_id', None))[0]
        data = ts_id.ts_data[2:]
        new_lines = self.env['hr.rfid.ctrl.ts.line'].create([{
            'day': str(j),
            'day_number': j,
            'begin': ts_id._get_interval_from_day_tuple(j, i)[0],
            'end': ts_id._get_interval_from_day_tuple(j, i)[1],
            'number': i + 1} for i in range(4) for j in range(8)])
        week = [(6, 0, new_lines.mapped('id'))]
        # week = [(0, 0, {
        #     'day': str(j),
        #     'day_number': j,
        #     'begin': ts_id._get_interval_from_day_tuple(j, i)[0],
        #     'end': ts_id._get_interval_from_day_tuple(j, i)[1],
        #     'number': i + 1}) for i in range(4) for j in range(8)]
        return week

    ts_id = fields.Many2one(
        string='Time Schedule',
        comodel_name='hr.rfid.time.schedule',
        default=lambda self: self.env.context.get('active_id', None)
    )

    interval_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.ts.line',
        inverse_name='week_id',
        default=_default_interval_ids,
    )

    @api.constrains('interval_ids')
    def _check_interval_ids(self):
        for day in range(8):
            record = self.interval_ids.filtered(lambda i: i.day_number == day)
            ranges = [[i.begin, i.end] for i in record]
            # Sort intervals based on start time
            ranges.sort(key=lambda x: x[0])

            # Check for overlap
            for i in range(1, len(ranges)):
                # If the start of the current interval is less than the end of the previous, there's an overlap
                if ranges[i][0] < ranges[i - 1][1]:
                    raise ValidationError(_("The intervals for day %d are overlapping" % day))

    def save_ts(self):
        new_ts_data = '%02X' % self.ts_id.number + self.interval_ids.get_set_str()
        self.sudo().ts_id.ts_data = new_ts_data
        if not self.ts_id.is_empty:
            self.ts_id.controller_ids.write_ts(new_ts_data)
        act_id = self.env.ref('hr_rfid.hr_rfid_time_schedule_action').sudo().read()[0]
        return act_id
