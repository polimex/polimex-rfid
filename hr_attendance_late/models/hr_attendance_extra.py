from collections import defaultdict

from odoo import api, fields, models
from datetime import datetime, timedelta, time

class HrAttendanceExtra(models.Model):
    _name = 'hr.attendance.extra'
    _description = 'Extra work time calculations'
    _order = 'for_date'

    for_date = fields.Date(
        string="Date",
        required=True,
        help="""The specific date for which attendance calculations are performed.

        • Format: YYYY-MM-DD
        • Purpose: Groups all attendance records for a single working day
        • Effect: All time calculations are based on this date's attendance records

        Note: This is the primary date used for reporting and time calculations.""")
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string="Employee",
        required=True,
        ondelete='cascade',
        help="""The employee for whom attendance calculations are performed.
        
        • Required: Must select an employee
        • Effect: All time calculations are specific to this employee
        • Cascade: Record is deleted if employee is deleted
        
        Note: Used to link attendance data with employee work schedules and department settings.""")
    department_id = fields.Many2one(
        related='employee_id.department_id',
        string="Department",
        readonly=True,
        store=True,
        help="""The department of the employee (automatically filled).
        
        • Source: Copied from employee's department
        • Purpose: Used for department-specific attendance reports and calculations
        • Read-only: Updates automatically when employee's department changes
        
        Note: Stored for faster reporting and filtering by department.""")

    actual_work_time = fields.Float(
        digits=(2, 2),
        string="Actual Work Time",
        help="""Total hours actually worked on this date (including day and night time).
        
        • Format: Hours in decimal format (e.g., 8.5 = 8 hours 30 minutes)
        • Calculation: Sum of all work periods between check-in and check-out
        • Includes: Both regular hours and overtime periods
        
        Note: This is the total productive time, excluding breaks and non-work periods.""")
    actual_work_time_day = fields.Float(
        digits=(2, 2),
        string="Actual Day Time",
        help="""Hours worked during standard daytime period.
        
        • Format: Hours in decimal format (e.g., 7.5 = 7 hours 30 minutes)
        • Period: Typically 06:00-22:00 (configurable per company)
        • Purpose: Separate day hours from night hours for different pay rates
        
        Note: Used for calculating regular pay rates vs. night shift premiums.""")
    actual_work_time_night = fields.Float(
        digits=(2, 2),
        string="Actual Night Time",
        help="""Hours worked during night shift period.
        
        • Format: Hours in decimal format (e.g., 1.0 = 1 hour)
        • Period: Typically 22:00-06:00 (configurable per company)
        • Premium: Usually paid at higher rate than day hours
        
        Note: Night hours often qualify for additional compensation per labor agreements.""")
    theoretical_work_time = fields.Float(
        digits=(2, 2),
        string="Theoretical Work Time",
        help="""Expected work hours according to employee's work schedule.
        
        • Source: Based on employee's resource calendar for this date
        • Format: Hours in decimal format (e.g., 8.0 = 8 hours)
        • Purpose: Baseline for calculating overtime, late arrivals, and early departures
        
        Note: This is the scheduled work time, not necessarily what was actually worked.""")
    late_time = fields.Float(
        digits=(2, 2),
        string="Late Arrival Time",
        help="""Hours the employee arrived late to work.
        
        • Calculation: Time between scheduled start and actual first check-in
        • Format: Hours in decimal format (e.g., 0.25 = 15 minutes late)
        • Threshold: Based on department's late arrival tolerance settings
        
        Note: May affect attendance bonuses or result in deductions depending on company policy.""")
    early_leave_time = fields.Float(
        digits=(2, 2),
        string="Early Departure Time",
        help="""Hours the employee left work early.
        
        • Calculation: Time between actual last check-out and scheduled end time
        • Format: Hours in decimal format (e.g., 0.5 = 30 minutes early)
        • Impact: May result in reduced pay or attendance penalties
        
        Note: Early departures without approval may affect performance evaluations.""")
    early_come_time = fields.Float(
        digits=(2, 2),
        string="Early Arrival Time",
        help="""Hours the employee arrived before scheduled start time.
        
        • Calculation: Time between actual first check-in and scheduled start
        • Format: Hours in decimal format (e.g., 0.25 = 15 minutes early)
        • Recognition: Shows employee punctuality and dedication
        
        Note: Early arrivals may qualify for recognition but typically don't count as overtime.""")
    overtime = fields.Float(
        digits=(2, 2),
        string="Overtime Hours",
        help="""Additional hours worked beyond the scheduled work time.
        
        • Calculation: Actual work time minus theoretical work time (when positive)
        • Format: Hours in decimal format (e.g., 2.0 = 2 hours overtime)
        • Compensation: Usually paid at premium rate (1.5x or 2x base rate)
        
        Note: Overtime calculation may vary based on daily vs. weekly limits and labor agreements.""")
    overtime_night = fields.Float(
        digits=(2, 2),
        string="Night Overtime Hours",
        help="""Overtime hours worked during night shift period.
        
        • Period: Night hours (typically 22:00-06:00) that exceed scheduled time
        • Premium: Often paid at highest rate (night premium + overtime premium)
        • Format: Hours in decimal format (e.g., 1.5 = 1 hour 30 minutes)
        
        Note: Double premium may apply - both overtime and night shift bonuses.""")
    extra_time = fields.Float(
        digits=(2, 2),
        string="Extra Time",
        help="""Additional work time that doesn't qualify as standard overtime.
        
        • Difference: Extra time vs. Overtime depends on company policy
        • Examples: Weekend work, holiday work, or special project hours
        • Compensation: May have different pay rate than regular overtime
        
        Note: Classification depends on labor agreements and local regulations.""")
    extra_night = fields.Float(
        digits=(2, 2),
        string="Extra Night Time",
        help="""Extra work time performed during night shift hours.
        
        • Period: Night hours (typically 22:00-06:00) for special assignments
        • Premium: May include both extra time and night shift bonuses
        • Format: Hours in decimal format
        
        Note: Used for weekend night work, holiday night shifts, or emergency calls.""")
    shift_number = fields.Integer(
        group_operator='count_distinct',
        string="Shift Number",
        help="""Identifier for the work shift on this date.
        
        • Purpose: Distinguishes between multiple shifts in a day
        • Aggregation: Counts distinct shifts for reporting
        • Usage: Useful for companies with multiple daily shifts
        
        Note: Helps track shift patterns and identify shift-specific attendance issues.""")

    attendance_count = fields.Char(
        string='Attendance Records',
        compute='_compute_counts',
        help="""Number of check-in/check-out records for this date.
        
        • Computation: Automatically calculated from hr.attendance records
        • Format: Text showing count (e.g., "4 records")
        • Purpose: Quick overview of attendance activity
        
        Note: Multiple records indicate breaks, lunch periods, or multiple shifts.""")

    def _compute_counts(self):
        """Compute attendance count using batch prefetch pattern.

        Optimized to use ONE query instead of N queries when computing for multiple records.
        Pattern: Similar to hr_attendance._update_overtime batch processing.
        """
        if not self:
            return

        # Filter out records without dates and set their count to 0
        valid_records = self.filtered(lambda r: r.for_date and r.employee_id)
        invalid_records = self - valid_records

        for ae in invalid_records:
            ae.attendance_count = 0

        if not valid_records:
            return

        # Batch prefetch - ONE query for all attendances in range
        # Filter out any False values from dates
        dates = [d for d in valid_records.mapped('for_date') if d]

        if not dates:
            return

        min_date = min(dates)
        max_date = max(dates)
        employee_ids = valid_records.mapped('employee_id').ids

        all_attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', employee_ids),
            ('check_in', '>=', datetime.combine(min_date, time(0, 0))),
            ('check_in', '<', datetime.combine(max_date + timedelta(days=1), time(0, 0)))
        ])

        # Group by (employee_id, date) in memory - O(N) complexity
        counts = defaultdict(int)
        for att in all_attendances:
            att_date = att.check_in.date()
            key = (att.employee_id.id, att_date)
            counts[key] += 1

        # Assign counts - O(1) lookup per record
        for ae in valid_records:
            ae.attendance_count = counts.get((ae.employee_id.id, ae.for_date), 0)

    def _compute_display_name(self):
        super()._compute_display_name()
        for rec in self:
            rec.display_name = '%s / %s' % (rec.for_date, rec.employee_id.name)

    def open_attendance_logs(self):
        self.ensure_one()
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', datetime.combine(self.for_date, time(0, 0))),
            ('check_in', '<=', datetime.combine(self.for_date, time(0, 0)) + timedelta(days=1))
        ]
        res = self.env['ir.actions.act_window']._for_xml_id('hr_attendance.hr_attendance_action')
        res.update(
            context=dict(self.env.context, group_by=False),
            domain=domain
        )
        return res

