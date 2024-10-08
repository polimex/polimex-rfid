# -*- coding: utf-8 -*-
# Part of Polimex RFID Pack. See LICENSE file for full copyright and licensing details.

{
    'name': 'HR RFID Vertical Elections',
    'summary': 'HR RFID Vertical Elections',
    'description': 'Organize your elections with RFID',
    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'category': 'Human Resources',
    'version': '1.0',
    'license': 'AGPL-3',
    'depends': ['hr_rfid', 'bus'],
    'data': [
        'security/hr_rfid_voting_security.xml',
        'views/vote_session_views.xml',
        'views/voting_participants_views.xml',
        'views/voting_item_views.xml',
        'views/voting_vote_views.xml',
        'views/voting_display_views.xml',
        'views/vote_menus.xml',
        'reports/voting_session_reports.xml',
        # 'views/voting_display_templates_frontend.xml',
        'views/voting_template_frontend.xml',
        # 'security/ir_rule.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'assets': {
    #     'web.assets_backend': [
        # ],
        'hr_rfid_vertical_elections.assets_display': [
            # 1 Define display variables (takes priority)
            "hr_rfid_vertical_elections/static/src/display/primary_variables.scss",
            "hr_rfid_vertical_elections/static/src/display/bootstrap_overridden.scss",

            #2  # Front-end libraries
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_frontend_helpers'),
            'web/static/lib/jquery/jquery.js',
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap_frontend'),
            ('include', 'web._assets_bootstrap_backend'),
            '/web/static/lib/odoo_ui_icons/*',
            '/web/static/lib/bootstrap/scss/_functions.scss',
            '/web/static/lib/bootstrap/scss/_mixins.scss',
            '/web/static/lib/bootstrap/scss/utilities/_api.scss',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            ('include', 'web._assets_core'),
            'bus/static/src/*.js',
            'bus/static/src/services/**/*.js',
            'web/static/src/views/fields/formatters.js',

            # Display's specific assets
            'hr_rfid_vertical_elections/static/src/display/**/*',
        ],
    },
}
