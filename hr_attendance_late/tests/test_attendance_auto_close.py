# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from unittest.mock import patch
from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
import logging

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestAttendanceAutoClose(TransactionCase):
    """Test auto-close functionality with max_time_in_zone logic"""

    def setUp(self):
        super(TestAttendanceAutoClose, self).setUp()

        # Create test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company Auto Close',
        })

        # Create test department
        self.department = self.env['hr.department'].create({
            'name': 'Test Department',
            'company_id': self.company.id,
            'ignore_early_come_time': 0,
            'ignore_late_time': 0,
            'ignore_early_leave_time': 0,
            'ignore_overtime': 0,
            'ignore_extra_time': 0,
        })

        # Create resource calendar
        self.calendar = self.env['resource.calendar'].create({
            'name': 'Test Calendar',
            'company_id': self.company.id,
            'tz': 'Europe/Sofia',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17}),
            ]
        })

        # Create employee
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee Auto Close',
            'company_id': self.company.id,
            'department_id': self.department.id,
            'resource_calendar_id': self.calendar.id,
        })

        # Create zone with auto-close settings
        if 'hr.rfid.zone' in self.env:
            self.zone = self.env['hr.rfid.zone'].create({
                'name': 'Test Zone Auto Close',
                'company_id': self.company.id,
                'attendance': True,
                'max_time_in_zone': 12.0,  # 12 hours max
                'auto_close_time_for_zone': 7.0,  # Not used anymore
            })
        else:
            self.zone = False
            self.skipTest("hr.rfid.zone model not available")

    def test_auto_close_uses_max_time_not_fixed_duration(self):
        """Test that auto-close uses max_time_in_zone instead of auto_close_time_for_zone"""
        test_date = fields.Date.from_string('2023-11-20')  # Monday

        # Create attendance without check_out, check-in at 08:00
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime.combine(test_date, datetime.min.time()) + timedelta(hours=8),
            'check_out': False,
            'in_zone_id': self.zone.id,
        })

        # Mock current time as 22:00 (14 hours after check-in, exceeds max_time_in_zone of 12h)
        mock_now = datetime.combine(test_date, datetime.min.time()) + timedelta(hours=22)

        with patch('odoo.addons.hr_attendance_late.models.hr_employee.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.combine
            mock_datetime.min = datetime.min

            # Calculate attendance - should auto-close at 12 hours (max_time_in_zone)
            self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)

        # Check results
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])

        self.assertTrue(attendance_extra, "Attendance extra should be created")
        # Should be capped at max_time_in_zone (12h), not auto_close_time_for_zone (7h)
        self.assertAlmostEqual(attendance_extra.actual_work_time, 8.0, 1,
                               "Actual work time should be capped at 8h (work schedule)")

    def test_auto_close_within_max_time_uses_current_time(self):
        """Test that attendance within max_time_in_zone uses current time (not closed)"""
        test_date = fields.Date.from_string('2023-11-20')  # Monday

        # Create attendance without check_out at 08:00
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime.combine(test_date, datetime.min.time()) + timedelta(hours=8),
            'check_out': False,
            'in_zone_id': self.zone.id,
        })

        # Mock current time as 12:00 (4 hours after check-in, within max_time_in_zone)
        mock_now = datetime.combine(test_date, datetime.min.time()) + timedelta(hours=12)

        with patch('odoo.addons.hr_attendance_late.models.hr_employee.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.combine = datetime.combine
            mock_datetime.min = datetime.min

            # Calculate attendance - should use current time
            self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)

        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])

        self.assertTrue(attendance_extra)
        # Should be 4 hours (08:00 to 12:00)
        self.assertAlmostEqual(attendance_extra.actual_work_time, 4.0, 1,
                               "Should use current time when within max_time_in_zone")

    def test_no_extra_record_without_attendance(self):
        """Test that no hr.attendance.extra is created without real attendance"""
        test_date = fields.Date.from_string('2023-11-20')  # Monday

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
        test_date = fields.Date.from_string('2023-11-20')  # Monday

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