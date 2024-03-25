from random import randint

from odoo.addons.resource.models.resource import float_to_time
from odoo import fields, models, api, _
from odoo.addons.base.models.ir_cron import _intervalTypes
from datetime import datetime, timedelta, date, time, timezone
# from pytz import timezone, UTC
import pytz
import logging

_logger = logging.getLogger(__name__)


class BaseRFIDService(models.Model):
    _name = 'rfid.service'
    _description = 'RFID Service'
    _inherit = ['mail.activity.mixin', 'mail.thread']
    # _order = 'number'

    name = fields.Char(
        help='Friendly service name',
        required=True
    )
    active = fields.Boolean(
        default=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    color = fields.Integer(string='Color Index')
    displayed_image_id = fields.Many2one('ir.attachment',
                                         domain="[('res_model', '=', 'rfid.service'), ('res_id', '=', id), ('mimetype', 'ilike', 'image')]",
                                         string='Cover Image')
    tag_ids = fields.Many2many(
        comodel_name='rfid.service.tags',
        domain="[('company_id', '=', company_id)]",
        string='Tags')
    service_type = fields.Selection([
        ('time', 'Time based'),
        ('count', 'Visits based'),
        ('time_count', 'Time and Visits based'),
        ('time_in', 'Time spend in the service area.'),
    ], default='time')
    time_in_payment = fields.Selection([
        ('pre_paid', 'Pre paid service time'),
        ('post_paid', 'Post paid service time'),
    ], default='pre_paid')
    pre_defined_time = fields.Float(
        help='Pre defined time for the service. It is used for time in based services. If 0 the operator can set the '
             'time.',
        default=0
    )
    visits = fields.Integer(
        default=0,
        help='Visits count'
    )
    time_interval_number = fields.Integer(
        default=1,
        help="Repeat every x.")
    time_interval_type = fields.Selection(
        [('minutes', 'Minutes'),
         ('hours', 'Hours'),
         ('days', 'Days'),
         ('weeks', 'Weeks'),
         ('months', 'Months')],
        string='Interval Unit',
        default='months'
    )
    time_interval_start = fields.Float(
        help='Service time to start. Format HH:MM. 00:00 means not use',
        default=0
    )
    time_interval_end = fields.Float(
        help='Service time to end. Format HH:MM. 00:00 means not use',
        default=0
    )
    access_group_id = fields.Many2one(
        comodel_name='hr.rfid.access.group',
        required=True,
    )
    dual_access_group = fields.Boolean(
        default=False,
    )
    access_group_in_id = fields.Many2one(
        comodel_name='hr.rfid.access.group',
    )
    access_group_out_id = fields.Many2one(
        comodel_name='hr.rfid.access.group',
    )

    generate_barcode_card = fields.Boolean(
        default=False,
        help='The card will be generated automatically for barcode reading'
    )

    zone_id = fields.Many2one(
        comodel_name='hr.rfid.zone'
    )
    parent_id = fields.Many2one(
        comodel_name='res.partner',
        help='All partners created from this service will be attached to this partner. It is optional.'
    )
    card_type = fields.Many2one(
        'hr.rfid.card.type',
        string='Card type',
        help='Card type for registered cards from this service',
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_card_type_def').id,
        tracking=True,
    )
    fixed_time = fields.Boolean(
        default=True,
        help='If the time is not fixed, the operator can change the start and end time of the service.'
    )
    activate_on_first_use = fields.Boolean(
        default=False,
        help='Activate your card upon first use. The timing interval begins as soon as the card is used for the first '
             'time.'
    )
    valid_days_for_activation = fields.Integer(
        default=30,
        help='The card will be valid for use till N days since issuing date.'
    )
    example_start_date = fields.Datetime(
        compute='_compute_example_start_end_date',
    )
    example_end_date = fields.Datetime(
        compute='_compute_example_start_end_date',
    )

    @api.depends('time_interval_number', 'time_interval_type', 'time_interval_start', 'time_interval_end')
    def _compute_example_start_end_date(self):
        for r in self:
            r.example_start_date = r.calc_start()
            r.example_end_date = r.calc_end()

    @api.onchange('generate_barcode_card')
    def _onchange_barcode(self):
        self.card_type = self.generate_barcode_card and self.env.ref(
            'hr_rfid.hr_rfid_card_type_barcode').id or self.env.ref('hr_rfid.hr_rfid_card_type_def').id

    def action_new_sale(self):
        ctx = {'default_service_id': self.id}
        if self.generate_barcode_card:
            hex_num, num = self.env['hr.rfid.card'].create_bc_card()
            ctx['default_card_number'] = num
        return {
            'name': _('New Sale - %s', self.name),
            'view_mode': 'form',
            'res_model': 'rfid.service.sale.wiz',
            'views': [(self.env.ref('rfid_service_base.sale_wiz_form').id, 'form')],
            'type': 'ir.actions.act_window',
            # 'res_id': wizard.id,
            'target': 'new',
            'context': ctx,
            # 'context': self.env.context,
        }

    def action_view_sales(self):
        result_action = self.env.ref('rfid_service_base.hr_rfid_service_sale_action').sudo().read()[0]
        result_action['domain'] = [('service_id', '=', self.id)]
        return result_action

    def calc_start(self, start_date=None):
        """
        Calculate the start date of the service
        :param start_date: prefer start date (default is Today)
        :return:
        """
        self.ensure_one()
        start_date = start_date or fields.Date.today()
        dt = datetime.combine(start_date,
                              float_to_time(self.time_interval_start))
        return pytz.timezone(self.env.user.tz).localize(dt).astimezone(pytz.UTC).replace(tzinfo=None)

    def calc_end(self, start_date=None):
        self.ensure_one()
        time_interval_type = self.time_interval_type
        time_interval_number = self.time_interval_number
        time_interval_end = self.time_interval_end
        calc_start_date = self.calc_start(start_date=start_date)

        if self.fixed_time:
            new_date = (calc_start_date or start_date) + _intervalTypes[time_interval_type](time_interval_number)
            new_time = float_to_time(time_interval_end)
            dt = datetime.combine(new_date.date(), new_time)
            user_tz = pytz.timezone(self.env.user.tz)
            dt = user_tz.localize(dt).astimezone(pytz.UTC).replace(tzinfo=None)
            return dt
        else:
            return (calc_start_date or start_date) + _intervalTypes[time_interval_type](time_interval_number)


class ServiceTags(models.Model):
    """ Tags of service's """
    _name = "rfid.service.tags"
    _description = "Service Tags"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Name', required=True)
    color = fields.Integer(string='Color', default=_get_default_color)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]
