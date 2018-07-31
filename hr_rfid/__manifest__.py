# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Access Control',
    'version': '0.1',
    'category': 'Human Resources',
    'summary': 'Manage employee access control',
    'author': 'Polimex',
    'license': 'GPL-3',

    'website': 'securitybulgaria.com',

    'depends': [ 'base', 'hr' ],

    'data': [
        'security/hr_rfid_security.xml',
        'security/ir.model.access.csv',
        'data/hr_rfid_actions.xml',
        'data/hr_rfid_card_type_data.xml',
        'data/hr_rfid_cron_jobs.xml',
        'data/hr_rfid_time_schedule_data.xml',
        'views/hr_department_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_rfid_access_group_views.xml',
        'views/hr_rfid_card_views.xml',
        'views/hr_rfid_webstack_views.xml',
    ],

    'demo': [ ],
    
    "images": [
        'static/images/main_screenshot.png',
        'static/images/tut_01.png',
        'static/images/tut_02.png',
        'static/images/tut_03.png',
        'static/images/tut_04.png',
        'static/images/tut_05.png',
        'static/images/tut_06.png',
        'static/images/tut_07.png',
        'static/images/tut_08.png',
        'static/images/tut_09.png',
        'static/images/tut_10.png',
        'static/images/tut_11.png',
        'static/images/tut_12.png',
        'static/images/tut_13.png',
    ],

    'installable': True,
    'auto_install': False,
}
