# -*- coding: utf-8 -*-

import time
from datetime import datetime, timedelta, time as datetime_time

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAttendanceCalculationSimple(TransactionCase):
    """Test attendance extra calculation following Odoo 15 patterns"""
    
    def setUp(self):
        super(TestAttendanceCalculationSimple, self).setUp()
        
        # Use existing company
        self.company = self.env.company
        
        # Create minimal test data
        self.department = self.env['hr.department'].create({
            'name': 'Test Department',
        })
        
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'department_id': self.department.id,
        })
        
        # Set up work schedule if not exists
        if not self.employee.resource_calendar_id:
            self.calendar = self.env['resource.calendar'].create({
                'name': 'Test Calendar',
                'attendance_ids': [
                    (0, 0, {'name': 'Monday', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 17}),
                    (0, 0, {'name': 'Tuesday', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 17}),
                ]
            })
            self.employee.resource_calendar_id = self.calendar
    
    def test_01_normal_attendance(self):
        """Test normal 8-17 attendance creates correct attendance extra"""
        # Use string format like Odoo core tests
        check_in = time.strftime('%Y-%m-10 08:00')
        check_out = time.strftime('%Y-%m-10 17:00')
        
        # Create attendance
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })
        
        # Check attendance extra was created
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', time.strftime('%Y-%m-10')),
        ])
        
        self.assertTrue(attendance_extra, 'Attendance extra should be created')
        self.assertEqual(attendance_extra.theoretical_work_time, 8.0)
        self.assertAlmostEqual(attendance_extra.actual_work_time, 8.0, places=1)
    
    def test_02_late_arrival(self):
        """Test late arrival calculation"""
        check_in = time.strftime('%Y-%m-11 08:30')  # 30 minutes late
        check_out = time.strftime('%Y-%m-11 17:00')
        
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })
        
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', time.strftime('%Y-%m-11')),
        ])
        
        self.assertTrue(attendance_extra)
        self.assertAlmostEqual(attendance_extra.late_time, 0.5, places=1)  # 30 minutes
    
    def test_03_missing_checkout(self):
        """Test attendance without checkout uses current time"""
        check_in = time.strftime('%Y-%m-12 08:00')
        
        # Create open attendance
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
        })
        
        # Force calculation
        test_date = fields.Date.from_string(time.strftime('%Y-%m-12'))
        self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)
        
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])
        
        self.assertTrue(attendance_extra)
        # Should have some actual work time (depends on current time)
        self.assertGreater(attendance_extra.actual_work_time, 0)
    
    def test_04_attendance_update_triggers_recalc(self):
        """Test that updating attendance triggers recalculation"""
        check_in = time.strftime('%Y-%m-13 08:00')
        check_out = time.strftime('%Y-%m-13 12:00')  # Initial 4 hours
        
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })
        
        # Check initial calculation
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', time.strftime('%Y-%m-13')),
        ])
        self.assertAlmostEqual(attendance_extra.actual_work_time, 4.0, places=1)
        
        # Update attendance
        attendance.write({'check_out': time.strftime('%Y-%m-13 17:00')})
        
        # Check recalculated
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', time.strftime('%Y-%m-13')),
        ])
        self.assertAlmostEqual(attendance_extra.actual_work_time, 8.0, places=1)
    
    def test_05_no_attendance_no_extra(self):
        """Test no attendance extra created when no attendance"""
        test_date = fields.Date.from_string(time.strftime('%Y-%m-14'))
        
        # Try to calculate for day with no attendance
        self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)
        
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])
        
        self.assertFalse(attendance_extra, 'No attendance extra should exist for day without attendance')