# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Attendance calculations',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Enhances employee attendance tracking with additional work time calculations',
    'author': 'Polimex',
    'license': 'LGPL-3',

    'description': """
       The main functionality of this module is to perform extra work time calculations. 
       It calculates various aspects of an employee's work time, such as actual work time, theoretical work time, late time, early leave time, early come time, overtime, and extra time. 
       It also keeps track of the number of shifts.  
       The module provides a method to compute the count of attendance records for a given employee and date. It also provides a method to open attendance logs for a specific employee and date.
       """,

    'website': 'https://polimex.co',

    'depends': ['hr_attendance', 'digest', 'hr_attendance_multi_rfid'],

    'data': [
        'security/ir.model.access.csv',
        'views/hr_department.xml',
        'views/digest_views.xml',
        'wizards/hr_attendance_extra_wizard.xml',
        'views/hr_attendance_extra.xml',
        'views/resource_calendar.xml',
        'security/multi_company.xml',
    ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'installable': True,
    'auto_install': False,
}
