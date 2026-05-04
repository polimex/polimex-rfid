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
        help='Give this time schedule a descriptive name that helps identify when it\'s used. '
             'For example: "Regular Working Hours", "Night Shift", "Weekend Access", etc.',
        required=True,
        tracking=True,
    )

    number = fields.Integer(
        string='TS Number',
        help='System-assigned time schedule number (0-15). TS 0 is reserved for "Not using TS" '
             'which means no time restrictions. Each controller can store up to 16 time schedules.',
        required=True,
        readonly=True,
    )

    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 help='The company this time schedule belongs to. Time schedules are '
                                      'company-specific and cannot be shared between companies.',
                                 default=lambda self: self.env.company)

    is_empty = fields.Boolean(
        compute='_compute_is_empty',
        help='Indicates whether this time schedule has any active time periods defined. '
             'Empty time schedules block all access when assigned to doors.'
    )

    ts_data = fields.Char(
        default=DEFAULT_TS_LINE,
        help='Internal representation of the time schedule data in hexadecimal format. '
             'Contains a 7x24 grid plus holiday settings. Do not modify directly - use the '
             'Details button to edit time periods through the wizard.'
    )

    access_group_door_ids = fields.One2many(
        'hr.rfid.access.group.door.rel',
        'time_schedule_id',
        string='Access Group/Door Combinations',
        help='Shows all doors and access groups that use this time schedule. This helps you '
             'understand which areas and employee groups are affected by changes to this schedule.',
    )

    controller_ids = fields.Many2many(
        comodel_name='hr.rfid.ctrl',
        help='RFID controllers that have this time schedule programmed. The schedule is '
             'automatically synchronized to controllers when doors using this schedule are configured.',
        # compute='_compute_controllers_ids'
    )

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

    display_name = fields.Char(
        compute='_compute_display_name',
        help='Display name showing the day and interval number for easy identification.'
    )
    begin = fields.Float(
        help='Start time for this access period. Enter in 24-hour format (e.g., 8.5 for 8:30 AM, '
             '17.25 for 5:15 PM). Leave at 0:00 if this interval is not used.'
    )
    end = fields.Float(
        help='End time for this access period. Enter in 24-hour format (e.g., 17.5 for 5:30 PM, '
             '23.75 for 11:45 PM). Must be after the begin time. Set to 0:00 to disable this interval.'
    )
    number = fields.Integer(
        readonly=True,
        help='Interval number (1-4). Each day can have up to 4 separate access periods. '
             'For example: Interval 1 for morning (8:00-12:00), Interval 2 for afternoon (13:00-17:00).'
    )
    day_number = fields.Integer(
        readonly=True,
        help='Internal day number (0-7) used for data processing.'
    )
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
        help="Day of the week or Holiday. The Holiday setting applies to all dates marked as holidays "
             "in the system, overriding the regular weekday schedule.",
        readonly=True
    )
    week_id = fields.Many2one(
        comodel_name='hr.rfid.ctrl.ts.week.wiz',
        help='Reference to the parent time schedule week wizard.'
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
        default=lambda self: self.env.context.get('active_id', None),
        help='The time schedule being edited. This wizard allows you to configure when access is '
             'allowed for each day of the week and holidays.'
    )

    interval_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.ts.line',
        inverse_name='week_id',
        default=_default_interval_ids,
        help='Define up to 4 time periods per day when access is allowed. The schedule works as a '
             '7x24 grid: 7 days plus holidays, with up to 4 intervals each day. Outside these '
             'periods, access will be denied. Leave intervals at 0:00 - 0:00 to skip them.'
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
