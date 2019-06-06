# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Attendance',
    'version': '0.2',
    'category': 'Human Resources',
    'summary': 'Manage employee attendance',
    'author': 'Polimex',

    'description': """
       Description
       """,

    'website': 'securitybulgaria.com',

    'depends': [ 'base', 'hr', 'hr_rfid', 'hr_attendance', 'hr_holidays_public' ],

    'data': [ 'views/hr_rfid_webstack_views.xml' ],

    'demo': [ ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'installable': True,
    'auto_install': False,
}
