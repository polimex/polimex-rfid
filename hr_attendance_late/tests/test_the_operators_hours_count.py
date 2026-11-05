"""Hours an operator enters on a forgotten badge are the day's hours.

The Forgotten Badge setting tells the company to have the real hours entered by
hand. The payroll clerk reads them from the daily figures, so that is where they
have to arrive.
"""

from datetime import datetime, time, timedelta

from odoo import fields

from .common import TestAttendanceLateCommon


class TestTheOperatorsHoursCount(TestAttendanceLateCommon):
    def _day(self, day):
        self.employee.with_context(
            attendance_calc_time=datetime.combine(day, time(23, 59)),
        ).update_extra_attendance_data(day, overwrite_existing=True)
        return self.env["hr.attendance.extra"].search(
            [("employee_id", "=", self.employee.id), ("for_date", "=", day)]
        )

    def _settled_monday(self):
        monday = fields.Date.from_string("2026-11-09")
        stay = self.create_attendance(
            self.employee, datetime.combine(monday, time(8, 0)), None, self.zone
        )
        stay._at_new_entry(
            datetime.combine(monday + timedelta(days=1), time(8, 0))
        ).autoclose_attendance()
        self.assertTrue(stay.forgotten_badge)
        return monday, stay

    def test_where_nothing_was_credited_the_entered_hours_count(self):
        """Count nothing: the day reads zero until the real hours are entered."""
        self.company.forgotten_badge_policy = "ignore"
        monday, stay = self._settled_monday()
        self.assertAlmostEqual(self._day(monday).actual_work_time, 0.0, 2)

        stay.check_out = datetime.combine(monday, time(17, 0))

        self.assertAlmostEqual(self._day(monday).actual_work_time, 8.0, 2)

    def test_a_later_check_out_than_the_credited_one_counts(self):
        """Credited until five, the person really stayed until seven."""
        monday, stay = self._settled_monday()
        figures = self._day(monday)
        self.assertAlmostEqual(figures.actual_work_time + figures.overtime, 8.0, 2)

        stay.check_out = datetime.combine(monday, time(19, 0))

        figures = self._day(monday)
        self.assertAlmostEqual(figures.actual_work_time + figures.overtime, 10.0, 2)
