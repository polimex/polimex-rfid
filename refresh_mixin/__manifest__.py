# -*- coding: utf-8 -*-
{
    'name': "Polimex Refresh Mixin",

    'summary': "Refresh Mixin for Odoo models",

    'author': "Polimex Team <software@polimex.co>",
    'website': "https://polimex.co",

    'category': 'Technical',
    'version': '19.0.1.3.0',
    'license': 'AGPL-3',

    'depends': ['web', 'bus', 'web_hierarchy'],

    'data': [
        'views/res_company_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'refresh_mixin/static/src/js/use_bus_refresh.js',
            'refresh_mixin/static/src/js/list_refresh_view.js',
            'refresh_mixin/static/src/js/kanban_refresh_view.js',
        ],
        'web.assets_backend_lazy': [
            'refresh_mixin/static/src/js/use_bus_refresh.js',
            'refresh_mixin/static/src/js/hierarchy_refresh_view.js',
        ],
        'web.assets_unit_tests': [
            'refresh_mixin/static/tests/**/*.test.js',
        ],
    },

    'application': False,
    'auto_install': False,
}
