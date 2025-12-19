from collections import defaultdict

from odoo import api, fields, models


class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _inherit = 'hr.attendance'

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        employee_dates = self._get_employee_dates_for_recalc(res)
        self._batch_update_extra_attendance(employee_dates)
        return res

    def write(self, vals):
        employee_dates_before = self._get_employee_dates_for_recalc(self)
        result = super(HrAttendance, self).write(vals)

        if any(field in vals for field in ['employee_id', 'check_in', 'check_out']):
            employee_dates_after = self._get_employee_dates_for_recalc(self)
            for emp, dates in employee_dates_after.items():
                employee_dates_before[emp] |= dates
            self._batch_update_extra_attendance(employee_dates_before)

        return result

    def unlink(self):
        employee_dates = self._get_employee_dates_for_recalc(self)
        super().unlink()
        self._batch_update_extra_attendance(employee_dates)

    def _get_employee_dates_for_recalc(self, attendances):
        """Group attendances by employee and collect unique dates.

        Returns:
            dict: {employee: set(date1, date2, ...)}

        Pattern: Similar to hr.attendance._get_attendances_dates()
        """
        employee_dates = defaultdict(set)
        for attendance in attendances:
            if attendance.check_in:
                employee_dates[attendance.employee_id].add(attendance.check_in.date())
            if attendance.check_out and attendance.check_out.date() != attendance.check_in.date():
                employee_dates[attendance.employee_id].add(attendance.check_out.date())
        return employee_dates

    def _batch_update_extra_attendance(self, employee_dates):
        """Batch update attendance extra data for multiple employees and dates.

        Args:
            employee_dates (dict): {employee: set(dates)}
        """
        # Skip if we're in a migration context to avoid recursive calls
        if self.env.context.get('migration_mode'):
            return

        for employee, dates in employee_dates.items():
            if not dates:
                continue
            min_date = min(dates)
            max_date = max(dates)
            employee.with_context(migration_mode=True).update_extra_attendance_data(
                from_datetime=min_date,
                to_datetime=max_date,
                overwrite_existing=True
            )
