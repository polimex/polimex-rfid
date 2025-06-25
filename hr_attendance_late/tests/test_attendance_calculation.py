# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, time
from freezegun import freeze_time
from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
import logging

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestAttendanceCalculation(TransactionCase):
    """Test attendance extra calculation with various edge cases"""
    
    def setUp(self):
        super(TestAttendanceCalculation, self).setUp()
        
        # Create test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
        })
        
        # Create test department with tolerance settings
        self.department = self.env['hr.department'].create({
            'name': 'Test Department',
            'company_id': self.company.id,
            'ignore_early_come_time': 10/60,  # 10 minutes
            'ignore_late_time': 5/60,  # 5 minutes
            'ignore_early_leave_time': 0,
            'ignore_overtime': 15/60,  # 15 minutes
            'ignore_extra_time': 10/60,  # 10 minutes
        })
        
        # Create resource calendar (work schedule)
        self.calendar = self.env['resource.calendar'].create({
            'name': 'Test Calendar 40h/week',
            'company_id': self.company.id,
            'tz': 'Europe/Sofia',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ]
        })
        
        # Create employee
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': self.company.id,
            'department_id': self.department.id,
            'resource_calendar_id': self.calendar.id,
        })
        
        # Create zone with auto-close settings (only if hr_rfid module is installed)
        if 'hr.rfid.zone' in self.env:
            self.zone = self.env['hr.rfid.zone'].create({
                'name': 'Test Zone',
                'company_id': self.company.id,
                'attendance': True,
                'max_time_in_zone': 12.0,  # 12 hours max
                'auto_close_time_for_zone': 8.0,  # Auto-close with 8 hours
            })
        else:
            self.zone = False
    
    def test_normal_attendance(self):
        """Test normal attendance calculation"""
        # Create attendance for Monday
        test_date = fields.Date.from_string('2023-11-20')  # Monday
        attendance_vals = {
            'employee_id': self.employee.id,
            'check_in': datetime.combine(test_date, time(8, 0)),
            'check_out': datetime.combine(test_date, time(17, 0)),
        }
        if self.zone:
            attendance_vals['in_zone_id'] = self.zone.id
        self.env['hr.attendance'].create(attendance_vals)
        
        # Calculate attendance extras
        self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)
        
        # Check results
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])
        
        self.assertTrue(attendance_extra)
        self.assertAlmostEqual(attendance_extra.theoretical_work_time, 8.0, 2)
        self.assertAlmostEqual(attendance_extra.actual_work_time, 8.0, 2)
        self.assertAlmostEqual(attendance_extra.late_time, 0.0, 2)
        self.assertAlmostEqual(attendance_extra.early_leave_time, 0.0, 2)
    
    def test_missing_checkout_within_max_time(self):
        """Test attendance with missing check-out within max zone time"""
        test_date = fields.Date.from_string('2023-11-20')  # Monday
        
        # Create attendance without check_out
        with freeze_time(datetime.combine(test_date, time(10, 0))):
            self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': datetime.combine(test_date, time(8, 0)),
                'check_out': False,
                'in_zone_id': self.zone.id,
            })
            
            # Calculate - should use current time (10:00)
            self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)
        
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])
        
        self.assertTrue(attendance_extra)
        # 2 hours worked (8:00 to 10:00)
        self.assertAlmostEqual(attendance_extra.actual_work_time, 2.0, 2)
    
    def test_missing_checkout_exceeds_max_time(self):
        """Test attendance with missing check-out exceeding max zone time"""
        test_date = fields.Date.from_string('2023-11-20')  # Monday
        
        # Create attendance without check_out
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime.combine(test_date, time(8, 0)),
            'check_out': False,
            'in_zone_id': self.zone.id,
        })
        
        # Calculate 15 hours later - should auto-close
        with freeze_time(datetime.combine(test_date, time(23, 0))):
            self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)
        
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])
        
        self.assertTrue(attendance_extra)
        # Should be auto-closed at 8 hours
        self.assertAlmostEqual(attendance_extra.actual_work_time, 8.0, 2)
    
    def test_late_arrival_within_tolerance(self):
        """Test late arrival within department tolerance"""
        test_date = fields.Date.from_string('2023-11-20')  # Monday
        
        # Create attendance - 3 minutes late
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime.combine(test_date, time(8, 3)),
            'check_out': datetime.combine(test_date, time(17, 0)),
            'in_zone_id': self.zone.id,
        })
        
        self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)
        
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])
        
        # Late time should be ignored (less than 5 minutes tolerance)
        self.assertAlmostEqual(attendance_extra.late_time, 0.0, 2)
    
    def test_multi_day_attendance(self):
        """Test attendance spanning multiple days (night shift)"""
        test_date = fields.Date.from_string('2023-11-20')  # Monday
        next_date = fields.Date.from_string('2023-11-21')  # Tuesday
        
        # Create night shift attendance
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime.combine(test_date, time(22, 0)),
            'check_out': datetime.combine(next_date, time(6, 0)),
            'in_zone_id': self.zone.id,
        })
        
        # Calculate for both days
        self.employee.update_extra_attendance_data(test_date, next_date, overwrite_existing=True)
        
        # Check Monday (should have 2 hours: 22:00-24:00)
        monday_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])
        self.assertTrue(monday_extra)
        self.assertAlmostEqual(monday_extra.actual_work_time, 2.0, 2)
        self.assertAlmostEqual(monday_extra.actual_work_time_night, 2.0, 2)
        
        # Check Tuesday (should have 6 hours: 00:00-06:00)
        tuesday_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', next_date),
        ])
        self.assertTrue(tuesday_extra)
        self.assertAlmostEqual(tuesday_extra.actual_work_time, 6.0, 2)
        self.assertAlmostEqual(tuesday_extra.actual_work_time_day, 6.0, 2)
    
    def test_overtime_calculation(self):
        """Test overtime calculation"""
        test_date = fields.Date.from_string('2023-11-20')  # Monday
        
        # Create attendance with overtime
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime.combine(test_date, time(8, 0)),
            'check_out': datetime.combine(test_date, time(19, 0)),  # 2 hours overtime
            'in_zone_id': self.zone.id,
        })
        
        self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)
        
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])
        
        self.assertAlmostEqual(attendance_extra.overtime, 2.0, 2)
    
    def test_out_of_order_event_handling(self):
        """Test automatic recalculation when attendance is updated"""
        test_date = fields.Date.from_string('2023-11-20')  # Monday
        
        # Create initial attendance
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime.combine(test_date, time(8, 0)),
            'check_out': datetime.combine(test_date, time(12, 0)),
            'in_zone_id': self.zone.id,
        })
        
        # First calculation
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])
        self.assertAlmostEqual(attendance_extra.actual_work_time, 4.0, 2)
        
        # Update attendance (simulating out-of-order event)
        attendance.write({'check_out': datetime.combine(test_date, time(17, 0))})
        
        # Should automatically recalculate
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])
        self.assertAlmostEqual(attendance_extra.actual_work_time, 8.0, 2)
    
    def test_error_handling_with_invalid_data(self):
        """Test error handling continues processing"""
        test_date = fields.Date.from_string('2023-11-20')  # Monday
        
        # Create invalid attendance that would cause calculation error
        # This is artificial since Odoo constraints prevent real invalid data
        with self.assertLogs('odoo.addons.hr_attendance_late.models.hr_employee', level='ERROR') as cm:
            # Try to calculate with no calendar (will cause error)
            self.employee.resource_calendar_id = False
            self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)
        
        # Should log error but continue
        self.assertTrue(any('ERROR in Attendance extra calculation' in msg for msg in cm.output))