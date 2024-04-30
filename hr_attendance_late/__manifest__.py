# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Attendance calculations',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Additional calculations for employee attendance',
    'author': 'Polimex',
    'license': 'LGPL-3',

    'description': """
       Description
       """,

    'website': 'https://polimex.co',

    'depends': ['hr_attendance','digest', 'hr_attendance_multi_rfid'],

    'data': [
        'security/ir.model.access.csv',
        'views/hr_department.xml',
        'views/digest_views.xml',
        'wizards/hr_attendance_extra_wizard.xml',
        'views/hr_attendance_extra.xml',
        'views/resource_calendar.xml',
    ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'installable': True,
    'auto_install': False,
}
