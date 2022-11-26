from odoo import fields, models, api


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    def _get_default_next_call(self):
        return (fields.Datetime.now()).strftime('%Y-%m-%d 00:00:00')

    refill_interval_number = fields.Integer(
        default=1,
        help="Repeat every x.")
    refill_interval_type = fields.Selection(
        [('hours', 'Hours'),
         ('days', 'Days'),
         ('weeks', 'Weeks'),
         ('months', 'Months')],
        string='Interval Unit',
        default='months'
    )
    refill_nextcall = fields.Datetime(
        string='Next Execution Date',
        default=_get_default_next_call,
        help="Next planned execution date for this refill.")
