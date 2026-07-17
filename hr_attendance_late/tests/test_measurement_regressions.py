# -*- coding: utf-8 -*-
"""Regression tests for the measurement layer (hr.attendance.extra).

Covers three behaviours added/fixed together with the Working Time dashboard:

1. ABSENCE ROWS: a scheduled working day with NO attendance produces a
   measurement row with theoretical_work_time > 0 and actual_work_time = 0 -
   the row the "Absence Days" KPI counts. (Previously absent days produced no
   row at all, so absences were invisible to any reporting.)

2. NIGHT OVERTIME: presence past the scheduled end and into the night window
   (after 22:00) yields overtime_night > 0. (Previously the night-overtime
   window opened at the END OF THE ATTENDANCE itself, so the intersection was
   always empty and night overtime was permanently zero - badge out at 23:00
   never produced a night premium.)

3. FIRST IN / LAST OUT: the daily row records the first badge-in and last
   badge-out as local-time hour fractions - the "came at / left at" columns.
"""
from datetime import datetime, timedelta

from odoo import fields
from odoo.tests import tagged

from .common import TestAttendanceLateCommon


def _monday_of_last_week():
    today = fields.Date.today()
    return today - timedelta(days=today.weekday() + 7)


@tagged('post_install', '-at_install', 'hr_attendance_late', 'hr_attendance_late_regressions')
class TestMeasurementRegressions(TestAttendanceLateCommon):

    def _extra_for(self, day):
        return self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', day),
        ])

    def test_absence_creates_measurement_row(self):
        """A scheduled day with no badge at all = an absence row (plan > 0, actual = 0)."""
        monday = _monday_of_last_week()
        self.employee.update_extra_attendance_data(monday, monday, overwrite_existing=True)
        extra = self._extra_for(monday)
        self.assertTrue(extra, "absent scheduled day must produce a measurement row")
        self.assertGreater(extra.theoretical_work_time, 0)
        self.assertEqual(extra.actual_work_time, 0)
        self.assertEqual(extra.late_time, 0)
        self.assertEqual(extra.first_in, 0)

    def test_absence_row_not_created_for_non_working_day(self):
        """A day OFF with no badge stays rowless (weekends are not absences)."""
        sunday = _monday_of_last_week() - timedelta(days=1)
        self.employee.update_extra_attendance_data(sunday, sunday, overwrite_existing=True)
        self.assertFalse(self._extra_for(sunday))

    def test_night_overtime_counted(self):
        """Badge-out well past 22:00 yields overtime_night > 0 (was always 0)."""
        monday = _monday_of_last_week()
        # calendar is UTC 08-12 / 13-17; stay until 23:30 -> 1.5h after 22:00
        self.create_attendance(
            self.employee,
            datetime.combine(monday, datetime.min.time()).replace(hour=8),
            datetime.combine(monday, datetime.min.time()).replace(hour=23, minute=30),
        )
        self.employee.update_extra_attendance_data(monday, monday, overwrite_existing=True)
        extra = self._extra_for(monday)
        self.assertTrue(extra)
        self.assertGreater(extra.overtime, 0, "evening presence is overtime")
        self.assertGreater(extra.overtime_night, 0,
                           "the after-22:00 share of overtime must be counted as night")
        self.assertLess(extra.overtime_night, extra.overtime,
                        "night share is a part of, not more than, total overtime")

    def test_first_in_last_out_recorded(self):
        """The daily row records first badge-in / last badge-out as hour fractions."""
        monday = _monday_of_last_week()
        self.create_attendance(
            self.employee,
            datetime.combine(monday, datetime.min.time()).replace(hour=8, minute=15),
            datetime.combine(monday, datetime.min.time()).replace(hour=17, minute=30),
        )
        self.employee.update_extra_attendance_data(monday, monday, overwrite_existing=True)
        extra = self._extra_for(monday)
        self.assertTrue(extra)
        # calendar tz is UTC, so local == UTC in this fixture
        self.assertAlmostEqual(extra.first_in, 8.25, places=2)
        self.assertAlmostEqual(extra.last_out, 17.5, places=2)
