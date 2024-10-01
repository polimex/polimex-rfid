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
    'license': 'AGPL-3',

    # for the full list
    'category': 'Administration',
    'version': '0.2',

    # any module necessary for this one to work correctly
    # 'depends': ['web_notify_extend', 'hr_rfid', 'board'],
    'depends': ['hr_rfid', 'board'],

    # always loaded
    'data': [
        'views/dashboard.xml',
        'views/hr_rfid_menus.xml',
        'views/hr_rfid_user_event.xml',
    ],
    # only loaded in demonstration mode

    "assets": {
        "web.assets_backend": [
            "/hr_rfid_realtime_dashboard/static/src/scss/hr_rfid_dashboard.scss",
        ],
        "web.assets_qweb": [
        ],
    },

    'application': False,
    'installable': False,
    'auto_install': False
}
