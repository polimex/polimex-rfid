# -*- coding: utf-8 -*-
{
    'name': "RFID realtime dashboard addon",

    'summary': """
        Add Dashboard with realtime events
    """,

    'description': """
        Add Dashboard with realtime events
    """,

    'author': "Polimex Team <software@polimex.co>",
    'website': "https://polimex.co",

    # for the full list
    'category': 'Administration',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['web_notify_extend', 'hr_rfid', 'board'],

    # always loaded
    'data': [
        'views/dashboard.xml',
        'views/hr_rfid_menus.xml',
    ],
    # only loaded in demonstration mode

    'application': False,
    'auto_install': True
}
