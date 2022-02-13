import pytz
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api

_intervalTypes = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7*interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}

import math
def _time_float_convert(float_val):
    factor = float_val < 0 and -1 or 1
    val = abs(float_val)
    return (factor * int(math.floor(val)), int(round((val % 1) * 60)))

class ProductAccessGroupRel(models.Model):
    _name = 'rfid.service.product.ag.rel'
    _description = 'Relation between product and Access group'

    product_id = fields.Many2one(
        comodel_name='product.template'
    )
    access_group_id = fields.Many2one(
        comodel_name='hr.rfid.access.group'
    )
    bill_type = fields.Selection([
        ('time', 'On Time base'),
        ('visit', 'On Visits base'),
        ('tandv', 'On Time and Visits base')],
        string='Billing type',
        index=True,
        default='time')
    time_starting_time = fields.Float(
        string='Starting Hour',
        help='The service will start from this time. 0 means not use this parameter',
        default=0
    )
    time_ending_time = fields.Float(
        string='Ending Hour',
        help='The service will end till this time. 0 means not use this parameter',
        default=0
    )
    time_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')], string='Interval Unit', default='months')
    time_interval_number = fields.Integer(
        string='Interval number',
        default=1,
        help="Validity interval"
    )
    visit_count = fields.Integer(
        string='Visits',
        help='Permitted visits before start billing',
        default=0
    )

    def get_start_timestamp(self, activate_on):
        start = activate_on
        if self.time_starting_time != 0:
            start = fields.Datetime.context_timestamp(self, activate_on)
            hour, minutes = _time_float_convert(self.time_starting_time)
            start = start.replace(hour=hour, minute=minutes, second=0)
            start = fields.Datetime.to_datetime(fields.Datetime.to_string(start.astimezone(pytz.UTC)))
        return start

    def get_end_timestamp(self, activate_on):
        start = fields.Datetime.context_timestamp(self, activate_on)
        end = start + _intervalTypes[self['time_interval_type']](self['time_interval_number'])
        if self.time_starting_time != 0:
            hour, minutes = _time_float_convert(self.time_ending_time)
            end = end.replace(hour=hour, minute=minutes, second=0)
        return fields.Datetime.to_datetime(fields.Datetime.to_string(end.astimezone(pytz.UTC)))

    def calculate_activate_expire(self, activate_on):
        """
        Calculate activate and deactivate timestamp based on current record settings

        Returns:
            tuple: activate, expire datetime
        """
        self.ensure_one()
        start = activate_on
        end = activate_on + _intervalTypes[self['time_interval_type']](self['time_interval_number'])
        if self.time_starting_time != 0:
            hour, minutes = _time_float_convert(self.time_starting_time)
            start = activate_on.date() + relativedelta(hours=hour, minutes=minutes)
        if self.time_ending_time != 0:
            hour, minutes = _time_float_convert(self.time_ending_time)
            end = end.date() + relativedelta(hours=hour, minutes=minutes)
        return start, end
