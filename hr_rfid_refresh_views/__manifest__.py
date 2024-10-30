# -*- coding: utf-8 -*-
{
    'name': "RFID Refresh Views",

    'summary': """
        Refresh RFID views
    """,

    'description': """
         The module refreshes the views of the models that inherit from it. Current supported views check refresh_mixin.
    """,

    'author': "Polimex Team <software@polimex.co>",
    'website': "https://polimex.co",

    # for the full list
    'category': 'Administration',
    'version': '1.0',
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['hr_rfid','refresh_mixin'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/hr_rfid_ctrl_alarm.xml',
        'views/hr_rfid_command.xml',
        'views/hr_rfid_event_system.xml',
        'views/hr_rfid_event_user.xml',
        'views/res_company.xml',
    ],
    # only loaded in demonstration mode
    'assets': {
        # 'web.assets_backend': [
        #     'refresh_mixin/static/src/js/*',
        # ],
    },

    'application': False,
    'auto_install': True
}
