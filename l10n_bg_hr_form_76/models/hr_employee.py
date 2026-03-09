from odoo import fields, models
from datetime import datetime, timedelta, date, time
import pytz


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    corporate_internal_number = fields.Char()

    def f76_intervals(self, specific_date):
        """Check if a specific date is a non-working day for the employee.

        Returns 'Н' if it's a holiday/weekend, False if it's a working day.
        Note: For batch processing, prefer ReportForm76._get_holiday_map() instead.
        """
        self.ensure_one()
        employee_resource = self.resource_id

        if isinstance(specific_date, str):
            specific_date = datetime.strptime(specific_date, '%Y-%m-%d').date()
        elif not isinstance(specific_date, date):
            raise ValueError("specific_date must be a string 'YYYY-MM-DD' or datetime.date")

        user_tz = pytz.timezone(employee_resource.tz or 'UTC')
        start_dt = user_tz.localize(datetime.combine(specific_date, time.min))
        end_dt = start_dt + timedelta(days=1) - timedelta(seconds=1)

        cal = employee_resource.calendar_id
        intervals = cal._attendance_intervals_batch(start_dt, end_dt)[False]
        global_leaves = cal._leave_intervals_batch(start_dt, end_dt)[False]

        return (global_leaves and 'Н') or (not intervals and 'Н') or False
