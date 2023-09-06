from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    refill_interval_number = fields.Integer(
        related='company_id.refill_interval_number',
        readonly=False,
        help="Repeat every x.")
    refill_interval_type = fields.Selection(
        [('hours', 'Hours'),
         ('days', 'Days'),
         ('weeks', 'Weeks'),
         ('months', 'Months')],
        related='company_id.refill_interval_type',
        readonly=False,
        string='Interval Unit')
    refill_nextcall = fields.Datetime(
        string='Next Execution Date',
        related='company_id.refill_nextcall',
        readonly=False,
        help="Next planned execution date for this refill.")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        company = self.env.company
        res.update({
            'refill_interval_number': company.event_lifetime,
            'refill_interval_type': company.event_lifetime,
            'refill_nextcall': company.event_lifetime,
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        company = self.env.company
        # Done this way to have all the values written at the same time,
        # to avoid recomputing the overtimes several times with
        # invalid company configurations
        fields_to_check = [
            'refill_interval_number',
            'refill_interval_type',
            'refill_nextcall',
        ]
        if any(self[field] != company[field] for field in fields_to_check):
            company.write({field: self[field] for field in fields_to_check})

