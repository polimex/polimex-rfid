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

    'website': 'polimex.co',

    'depends': ['hr_rfid', 'hr_attendance', 'hr_attendance_reason', 'hr_attendance_autoclose'],

    'data': [
        'security/ir.model.access.csv',
        'views/hr_attendance.xml',
        'views/hr_rfid_webstack_views.xml',
        'wizards/hr_recalc_attendance_wizard.xml',
    ],

    'demo': [ ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'installable': True,
    'auto_install': False,
}
