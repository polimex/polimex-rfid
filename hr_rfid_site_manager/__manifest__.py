# -*- coding: utf-8 -*-
{
    'name': "RFID Site Manager",

    'summary': """
        Add classification of the access control equipment
    """,

    'description': """
         Add classification of the access control equipment for the site management
    """,

    'author': "Polimex Team <software@polimex.co>",
    'website': "https://polimex.co",

    # for the full list
    'category': 'Administration',
    'version': '18.0.1.0.1',
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['hr_rfid','web_hierarchy'],

    # always loaded
    'data': [
        'security/hr_rfid_site_security.xml',
        'security/hr_rfid_multi_company.xml',
        'security/ir.model.access.csv',
        'views/hr_rfid_access_group.xml',
        'views/hr_rfid_ctrl_alarm_line.xml',
        'views/hr_rfid_door.xml',
        'views/hr_rfid_ctrl.xml',
        'views/hr_rfid_webstack.xml',
        'views/hr_rfid_event_user.xml',
        'views/hr_rfid_site.xml',
        'views/res_partner_views.xml',
    ],
    # 'images': ['static/images/main_screenshot.png'],
    # only loaded in demonstration mode
    'demo': [
        'data/hr_rfid_site_demo.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'hr_rfid_site_manager/static/src/**/*',
        ],
    },

    'application': False,
    'auto_install': False
}
