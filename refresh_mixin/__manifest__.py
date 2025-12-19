# -*- coding: utf-8 -*-
{
    'name': "Polimex Refresh Mixin",

    'summary': "Refresh Mixin for Odoo models",

    'description': """
The module refreshes the views of models that inherit from it.
Supported views: List, Kanban, Hierarchy.

Usage:
- Inherit from 'refresh.mixin' in your model
- Use js_class="list_refresh_view" for List views
- Use js_class="kanban_refresh_view" for Kanban views
- Use js_class="hierarchy_refresh_view" for Hierarchy views
- Enable "Real-time View Refresh" in Company settings
    """,

    'author': "Polimex Team <software@polimex.co>",
    'website': "https://polimex.co",

    'category': 'Technical',
    'version': '19.0.1.1.0',
    'license': 'AGPL-3',

    'depends': ['web', 'bus', 'web_hierarchy'],

    'data': [
        'views/res_company_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'refresh_mixin/static/src/js/list_refresh_view.js',
            'refresh_mixin/static/src/js/kanban_refresh_view.js',
        ],
        'web.assets_backend_lazy': [
            'refresh_mixin/static/src/js/hierarchy_refresh_view.js',
        ],
    },

    'application': False,
    'auto_install': False,
}
