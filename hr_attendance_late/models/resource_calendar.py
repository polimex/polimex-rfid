from odoo import api, fields, models

class ResourceCalendar(models.Model):
    _name = 'resource.calendar'
    _inherit = 'resource.calendar'

    daily_ranges_are_shifts = fields.Boolean(
        default=False,
        string="Daily Ranges Are Shifts",
        help="""Treat each daily time range as a separate shift for attendance calculations.
        
        • When enabled: Each time range (e.g., 9-12, 13-17) is considered a separate shift
        • When disabled: All time ranges for a day are treated as one continuous work period
        • Effect: Affects overtime and break calculations
        
        Note: Enable this for companies with formal shift systems or split work schedules.""")
