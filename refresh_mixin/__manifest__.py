# -*- coding: utf-8 -*-
{
    'name': "Polimex Refresh Mixin",

    'summary': """
        Refresh Mixin for Odoo models
    """,

    'description': """
         The module refreshes the views of the models that inherit from it. Current supported views are Kanban, List.
         Require js_class=hr_rfid_list_refresh_view for List view and js_class=hr_rfid_kanban_refresh_view for Kanban view.
    """,

    'author': "Polimex Team <software@polimex.co>",
    'website': "https://polimex.co",

    # for the full list
    'category': 'Administration',
    'version': '18.0.1.0.0',
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['web','bus','web_hierarchy'],

    # always loaded
    'data': [
    ],
    # 'images': ['static/images/main_screenshot.png'],
    # only loaded in demonstration mode
    'assets': {
        'web.assets_backend': [
            'refresh_mixin/static/src/js/*',
            'web_hierarchy/static/src/*',
        ],
    },

    'application': False,
    'auto_install': False
}
