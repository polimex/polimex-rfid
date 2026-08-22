# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, time

from odoo import fields
from .common import TestAttendanceLateCommon
import logging

_logger = logging.getLogger(__name__)


class TestAttendanceAutoClose(TestAttendanceLateCommon):
    """A forgotten check-out is settled by the zone's own auto-close promise.

    The zone form promises two numbers (hr_attendance_multi_rfid,
    hr.rfid.zone): "Maximum Hours in Zone" decides WHEN a forgotten
    attendance is considered abandoned, and "Auto-close Worked Hours" decides
    HOW MANY hours the person is credited with when it is. The fixture zone
    says max 12h, auto-close 8h.

    The day calculation is driven through the module's own test seam
    (context key attendance_calc_time) instead of mocking the clock.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.zone:
            cls.skipTest(cls, "hr.rfid.zone model not available")

    def test_auto_close_credits_the_zone_auto_close_hours(self):
        """The payroll officer sees the hours the zone promises, not the cap.

        An employee badges in at 08:00 and never badges out. When the day is
        calculated 14 hours later - past the zone's 12-hour abandonment
        limit - the attendance is settled as check-in + 8 worked hours
        (Auto-close Worked Hours), i.e. presence 08:00-16:00. Against the
        08:00-12:00 / 13:00-17:00 schedule that is 7 hours of actual work
        (the lunch break is not work). Had the calculation used the 12-hour
        maximum instead, the presence would have covered the whole schedule
        and shown 8.0 - which must NOT happen.
        """
        test_date = fields.Date.from_string('2026-11-09')  # Monday

        # Badge in at 08:00, never badge out
        self.create_attendance(
            self.employee,
            datetime.combine(test_date, time(8, 0)),
            None,
            self.zone,
        )

        # The day is calculated at 22:00 - 14 hours in the zone, past the max
        calc_time = datetime.combine(test_date, time(22, 0))
        self.employee.with_context(
            attendance_calc_time=calc_time
        ).update_extra_attendance_data(test_date, overwrite_existing=True)

        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])

        self.assertTrue(attendance_extra, "Attendance extra should be created")
        # Presence 08:00-16:00 (check-in + 8h auto-close) against the
        # 08:00-12:00/13:00-17:00 schedule = 7h. A result of 8.0 here would
        # mean the presence ran to 20:00 (max_time_in_zone) - the old bug.
        self.assertAlmostEqual(
            attendance_extra.actual_work_time, 7.0, 1,
            "Auto-close must credit Auto-close Worked Hours (8h presence -> "
            "7h scheduled work), not run the presence to the 12h maximum")

    def test_auto_close_does_not_fire_within_max_time(self):
        """A person still at work is measured up to now, not settled early.

        The same employee badges in at 08:00; the day is calculated at 12:00,
        only 4 hours later - well within the zone's 12-hour limit. Nothing is
        auto-closed: the calculation simply counts the morning worked so far
        (4 hours), and must NOT credit the 8 auto-close hours.
        """
        test_date = fields.Date.from_string('2026-11-09')  # Monday

        self.create_attendance(
            self.employee,
            datetime.combine(test_date, time(8, 0)),
            None,
            self.zone,
        )

        # Calculated at 12:00 - 4 hours in the zone, within the maximum
        calc_time = datetime.combine(test_date, time(12, 0))
        self.employee.with_context(
            attendance_calc_time=calc_time
        ).update_extra_attendance_data(test_date, overwrite_existing=True)

        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])

        self.assertTrue(attendance_extra)
        # 08:00 to 12:00 - the morning worked so far, no auto-close credit
        self.assertAlmostEqual(
            attendance_extra.actual_work_time, 4.0, 1,
            "Within the zone maximum the day is measured up to the "
            "calculation moment, never settled with auto-close hours")

    def test_no_extra_record_without_attendance(self):
        """Test that no hr.attendance.extra is created without real attendance"""
        test_date = fields.Date.from_string('2026-11-09')  # Monday

        # Do NOT create any attendance record

        # Try to calculate attendance extra
        self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)

        # Check that NO attendance_extra was created
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])

        self.assertFalse(attendance_extra,
                         "No attendance.extra should be created without real attendance data")

    def test_no_extra_record_recreated_after_deletion(self):
        """Test that deleted invalid records are not recreated"""
        test_date = fields.Date.from_string('2026-11-09')  # Monday

        # Do NOT create any attendance

        # Try to calculate - should not create anything
        self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)

        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])

        self.assertFalse(attendance_extra, "Should not create extra without attendance")

        # Try again with overwrite=True - should still not create
        self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)

        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])

        self.assertFalse(attendance_extra,
                         "Should not recreate extra records without attendance even with overwrite")
