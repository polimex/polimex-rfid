# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Attendance',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Manage employee attendance',
    'author': 'Polimex',
    'license': 'AGPL-3',

    'description': """
       Description
       """,

    'website': 'securitybulgaria.com',

    'depends': [ 'base', 'hr', 'hr_rfid', 'hr_attendance',],

    'data': [
        'views/hr_rfid_webstack_views.xml',
        'views/hr_rfid_attendace_settings.xml',
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
