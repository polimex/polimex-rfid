# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from datetime import datetime, time


@tagged('post_install', '-at_install', 'hr_attendance_late')
class TestAttendanceLateCommon(TransactionCase):
    """Common test class for hr_attendance_late module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company Attendance Late',
        })
        
        # Create test department with tolerance settings
        cls.department = cls.env['hr.department'].create({
            'name': 'Test Department',
            'company_id': cls.company.id,
            'ignore_early_come_time': 10/60,  # 10 minutes
            'ignore_late_time': 5/60,  # 5 minutes
            'ignore_early_leave_time': 0,
            'ignore_overtime': 15/60,  # 15 minutes
            'ignore_extra_time': 10/60,  # 10 minutes
        })
        
        # Create resource calendar (work schedule)
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Test Calendar 40h/week',
            'company_id': cls.company.id,
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {
                    'name': 'Monday Morning',
                    'dayofweek': '0',
                    'hour_from': 8,
                    'hour_to': 12,
                    'day_period': 'morning'
                }),
                (0, 0, {
                    'name': 'Monday Afternoon',
                    'dayofweek': '0',
                    'hour_from': 13,
                    'hour_to': 17,
                    'day_period': 'afternoon'
                }),
                (0, 0, {
                    'name': 'Tuesday Morning',
                    'dayofweek': '1',
                    'hour_from': 8,
                    'hour_to': 12,
                    'day_period': 'morning'
                }),
                (0, 0, {
                    'name': 'Tuesday Afternoon',
                    'dayofweek': '1',
                    'hour_from': 13,
                    'hour_to': 17,
                    'day_period': 'afternoon'
                }),
                (0, 0, {
                    'name': 'Wednesday Morning',
                    'dayofweek': '2',
                    'hour_from': 8,
                    'hour_to': 12,
                    'day_period': 'morning'
                }),
                (0, 0, {
                    'name': 'Wednesday Afternoon',
                    'dayofweek': '2',
                    'hour_from': 13,
                    'hour_to': 17,
                    'day_period': 'afternoon'
                }),
                (0, 0, {
                    'name': 'Thursday Morning',
                    'dayofweek': '3',
                    'hour_from': 8,
                    'hour_to': 12,
                    'day_period': 'morning'
                }),
                (0, 0, {
                    'name': 'Thursday Afternoon',
                    'dayofweek': '3',
                    'hour_from': 13,
                    'hour_to': 17,
                    'day_period': 'afternoon'
                }),
                (0, 0, {
                    'name': 'Friday Morning',
                    'dayofweek': '4',
                    'hour_from': 8,
                    'hour_to': 12,
                    'day_period': 'morning'
                }),
                (0, 0, {
                    'name': 'Friday Afternoon',
                    'dayofweek': '4',
                    'hour_from': 13,
                    'hour_to': 17,
                    'day_period': 'afternoon'
                }),
            ]
        })
        
        # Create test employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': cls.company.id,
            'department_id': cls.department.id,
            'resource_calendar_id': cls.calendar.id,
        })
        
        # Create zone if hr_rfid module is installed
        if 'hr.rfid.zone' in cls.env:
            cls.zone = cls.env['hr.rfid.zone'].create({
                'name': 'Test Zone',
                'company_id': cls.company.id,
                'attendance': True,
                'max_time_in_zone': 12.0,  # 12 hours max
                'auto_close_time_for_zone': 8.0,  # Auto-close with 8 hours
            })
        else:
            cls.zone = False
    
    def create_attendance(self, employee, check_in, check_out=None, zone=None):
        """Helper method to create attendance records"""
        vals = {
            'employee_id': employee.id,
            'check_in': check_in,
        }
        if check_out:
            vals['check_out'] = check_out
        if zone and 'in_zone_id' in self.env['hr.attendance']._fields:
            vals['in_zone_id'] = zone.id
        return self.env['hr.attendance'].create(vals)