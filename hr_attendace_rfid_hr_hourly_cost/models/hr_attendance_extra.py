from odoo import api, fields, models
from datetime import datetime, timedelta, time

class HrAttendanceExtraCost(models.Model):
    _inherit = ['hr.attendance.extra']

    currency_id = fields.Many2one(
        'res.currency',
        related='employee_id.currency_id',
        readonly=True,
        string='Currency',
        help="""Currency for cost calculations (derived from employee).
        
        • Source: Automatically inherited from employee's currency
        • Purpose: Ensures consistent currency for all cost calculations
        • Read-only: Cannot be changed directly
        
        Note: All monetary fields use this currency for proper formatting and calculations.""")
    hourly_cost = fields.Monetary(
        'Hourly Cost',
        related='employee_id.hourly_cost',
        currency_field='currency_id',
        groups="hr.group_hr_user",
        help="""Employee's hourly cost rate (derived from employee record).
        
        • Source: Copied from employee's hourly cost setting
        • Access: Visible to HR users only
        • Usage: Base rate for calculating actual work time costs
        
        Note: Update the employee's hourly cost to change this value.""")

    actual_work_time_cost = fields.Monetary(
        'Actual Work Time Cost',
        currency_field='currency_id',
        compute='_compute_actual_work_time_cost',
        groups="hr.group_hr_manager",
        store=True,
        help="""Total cost of actual work time (automatically calculated).
        
        • Calculation: Hourly cost × Actual work time hours
        • Access: Visible to HR managers only
        • Auto-update: Recalculated when hourly cost or work time changes
        
        Note: Provides financial overview of actual labor costs per day.""")

    @api.depends('actual_work_time', 'hourly_cost')
    def _compute_actual_work_time_cost(self):
        for ae in self:
            ae.actual_work_time_cost = ae.hourly_cost * ae.actual_work_time
