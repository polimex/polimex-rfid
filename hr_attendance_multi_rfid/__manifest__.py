# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Attendance',
    'version': '19.0.1.1.3',
    'category': 'Human Resources',
    'summary': 'Manage employee attendance',
    'author': 'Polimex',
    'license': 'AGPL-3',

    'description': """
       Description
       """,

    'website': 'https://polimex.co',

    'depends': ['hr_rfid', 'hr_attendance'],
    # 'depends': ['hr_rfid', 'hr_attendance', 'hr_attendance_reason', 'hr_attendance_autoclose'],

    'data': [
        'security/ir.model.access.csv',
        'security/resource_calendar_multi_company.xml',
        'security/attendance_recalc_run_rules.xml',
        'data/attendance_recalc_cron.xml',
        'views/hr_attendance.xml',
        'views/hr_rfid_webstack_views.xml',
        'views/hr_employee.xml',
        'views/attendance_recalc_run_views.xml',
        'wizards/hr_recalc_attendance_wizard.xml',
    ],

    'demo': [
        'demo/hr_attendance_multi_rfid_demo_showcase.xml',
    ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'installable': True,
    'auto_install': False,
}
