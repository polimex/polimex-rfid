# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Attendance',
    'version': '19.0.1.0.1',
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
        'data/attendance_autoclose_cron.xml',
        'views/hr_attendance.xml',
        'views/hr_rfid_webstack_views.xml',
        'views/hr_employee.xml',
        'wizards/hr_recalc_attendance_wizard.xml',
    ],

    'demo': [ ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'installable': True,
    'auto_install': False,
}
