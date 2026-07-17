from odoo import api, fields, models
from datetime import datetime, time

# Legal-rate codes resolved per worked day from hr.legal.rate (dated).
RATE_OVERTIME_WORKDAY = 'overtime_workday'   # multiplier, e.g. 1.5
RATE_OVERTIME_WEEKEND = 'overtime_weekend'   # multiplier, e.g. 1.75
RATE_OVERTIME_HOLIDAY = 'overtime_holiday'   # multiplier, e.g. 2.0
RATE_NIGHT_SUPPLEMENT = 'night_supplement'   # additive amount per night hour


class HrAttendanceExtraCost(models.Model):
    _name = 'hr.attendance.extra'
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
        help="Total labour cost for the day: regular hours plus overtime and "
             "rest-day/holiday premiums, plus the night-shift supplement. Uses "
             "the legal rates effective on this date, so past days keep their "
             "historical coefficients.")
    cost_regular = fields.Monetary(
        'Regular Cost', currency_field='currency_id',
        compute='_compute_actual_work_time_cost', groups="hr.group_hr_manager",
        store=True,
        help="Cost of hours worked inside the schedule at the base rate "
             "(hourly cost × actual work time).")
    cost_overtime = fields.Monetary(
        'Overtime Cost', currency_field='currency_id',
        compute='_compute_actual_work_time_cost', groups="hr.group_hr_manager",
        store=True,
        help="Cost of overtime worked on a working day, at the КТ чл. 262 "
             "working-day multiplier.")
    cost_extra = fields.Monetary(
        'Rest-day / Holiday Cost', currency_field='currency_id',
        compute='_compute_actual_work_time_cost', groups="hr.group_hr_manager",
        store=True,
        help="Cost of work performed on a rest day or official holiday, at the "
             "КТ чл. 262 rest-day or holiday multiplier (holiday detected from "
             "Public Holidays).")
    cost_night_supplement = fields.Monetary(
        'Night Supplement', currency_field='currency_id',
        compute='_compute_actual_work_time_cost', groups="hr.group_hr_manager",
        store=True,
        help="Additive night-shift supplement (НСОРЗ чл. 8) applied to every "
             "night hour worked — regular, overtime or holiday — on top of the "
             "rates above.")

    def _is_public_holiday(self):
        """True if this day is an official public holiday for the employee.

        Reads global (resource-less) Public Holidays on the employee's working
        calendar — the records the BG localisation seeds. Used to split
        rest-day pay (lower) from official-holiday pay (higher)."""
        self.ensure_one()
        if not self.for_date:
            return False
        calendar = (self.employee_id.resource_calendar_id
                    or self.employee_id.company_id.resource_calendar_id)
        if not calendar:
            return False
        dt_from = datetime.combine(self.for_date, time.min)
        dt_to = datetime.combine(self.for_date, time.max)
        return bool(self.env['resource.calendar.leaves'].search_count([
            ('calendar_id', '=', calendar.id),
            ('resource_id', '=', False),
            ('time_type', '=', 'leave'),
            ('date_from', '<=', dt_to),
            ('date_to', '>=', dt_from),
        ], limit=1))

    @api.depends('actual_work_time', 'actual_work_time_night', 'overtime',
                 'overtime_night', 'extra_time', 'extra_night', 'hourly_cost',
                 'for_date')
    def _compute_actual_work_time_cost(self):
        Rate = self.env['hr.legal.rate']
        for ae in self:
            rate = ae.hourly_cost
            company_id = ae.employee_id.company_id.id
            work_date = ae.for_date

            def _r(code, default=1.0):
                # Missing multiplier → no premium (1.0); for additive supplement
                # callers pass default 0.0.
                val = Rate._get_rate(code, work_date, company_id) if work_date else 0.0
                return val if val else default

            r_workday = _r(RATE_OVERTIME_WORKDAY)
            r_extra = (_r(RATE_OVERTIME_HOLIDAY) if ae._is_public_holiday()
                       else _r(RATE_OVERTIME_WEEKEND))
            night_supp = _r(RATE_NIGHT_SUPPLEMENT, default=0.0)

            # Night hours get the additive supplement regardless of whether they
            # are regular, overtime or holiday hours (НСОРЗ чл. 8 is independent).
            night_hours = (ae.actual_work_time_night + ae.overtime_night
                           + ae.extra_night)

            ae.cost_regular = rate * ae.actual_work_time
            ae.cost_overtime = rate * ae.overtime * r_workday
            ae.cost_extra = rate * ae.extra_time * r_extra
            ae.cost_night_supplement = night_hours * night_supp
            ae.actual_work_time_cost = (
                ae.cost_regular + ae.cost_overtime
                + ae.cost_extra + ae.cost_night_supplement
            )

    @api.model
    def _demo_apply_hourly_costs(self):
        """Give every demo employee with attendance-extra rows an hourly cost.

        The Labour Cost dashboard reads the stored cost columns (cost_regular /
        cost_overtime / cost_extra / cost_night_supplement / actual_work_time_cost),
        which are 0 until the employee has a non-zero hourly cost. The attendance
        volume is generated by hr_attendance_late (installed first), so by the
        time this runs the extra rows already exist - here we just assign a
        deterministic cost to the employees that still have none and force the
        stored cost recompute.

        Naturally idempotent: only employees whose cost is still zero are
        touched, so a demo reload assigns nothing new. Only invoked from the demo
        data <function> hook.
        """
        extras = self.search([])
        to_set = extras.employee_id.filtered(lambda e: not e.hourly_cost)
        for index, emp in enumerate(to_set.sorted('id')):
            # Spread 7.50 .. 13.75 EUR/h so the per-employee / per-department
            # cost breakdown has visible variation.
            emp.hourly_cost = 7.5 + (index % 6) * 1.25
        # Stored cost columns derive from the (now non-zero) hourly cost via the
        # related field; recompute explicitly so a demo reload fills every row
        # regardless of ORM recompute ordering during install.
        extras._compute_actual_work_time_cost()
