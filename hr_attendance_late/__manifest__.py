# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'Late Attendance',
    'version': '19.0.1.0.3',
    'category': 'Human Resources',
    'summary': 'Enhances employee attendance tracking with additional work time calculations',
    'author': 'Polimex',
    'license': 'AGPL-3',

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
