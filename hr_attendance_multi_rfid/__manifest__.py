# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Attendance',
    'version': '0.3',
    'category': 'Human Resources',
    'summary': 'Manage employee attendance',
    'author': 'Polimex',
    'license': 'GPL-3',

    'description': """
       Description
       """,

    'website': 'securitybulgaria.com',

    'depends': [ 'base', 'hr', 'hr_rfid', 'hr_attendance', 'hr_holidays_compute_days' ],

    'data': [
        'reports/hr_attendance_theoretical_time_report_views.xml',
        'security/hr_attendance_report_theoretical_time_security.xml',
        'security/ir.model.access.csv',
        'views/hr_holidays_status_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_rfid_webstack_views.xml',
        'data/hr_attendance_multi_rfid_cron_jobs.xml',
        'data/hr_attendance_multi_rfid_system_parameters.xml',
    ],

    'demo': [ ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'installable': True,
    'auto_install': False,
}
