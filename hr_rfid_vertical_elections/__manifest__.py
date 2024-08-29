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
    'license': 'LGPL-3',
    'depends': ['hr_rfid'],
    'data': [
        'views/vote_session_views.xml',
        'views/voting_participants_views.xml',
        'views/voting_item_views.xml',
        'views/voting_vote_views.xml',
        'views/voting_display_views.xml',
        'views/vote_menus.xml',
        'views/voting_display_templates_frontend.xml',
        'reports/voting_session_reports.xml',
        # 'data/ir_module_category_data.xml',
        # 'security/ir_rule.xml',
        'security/ir.model.access.csv',
    ],
    # 'demo': [
        # 'demo/room_office.xml',
        # 'demo/room_room.xml',
        # 'demo/room_booking.xml',
    # ],
    'installable': True,
    'application': True,
    'assets': {
    #     'web.assets_backend': [
            # 'room/static/src/room_booking_gantt_view/**/*',
        # ],
        'hr_rfid_vertical_elections.assets_display': [
            # 1 Define room variables (takes priority)
            "hr_rfid_vertical_elections/static/src/display/primary_variables.scss",
            "hr_rfid_vertical_elections/static/src/display/bootstrap_overridden.scss",

            #2 Load variables, Bootstrap and UI icons bundles
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap_backend'),
            "web/static/src/libs/fontawesome/css/font-awesome.css",
            "web/static/lib/odoo_ui_icons/*",
            'web/static/src/legacy/scss/ui.scss',
            'web/static/src/scss/base_frontend.scss',

            # Room's specific assets
            'hr_rfid_vertical_elections/static/src/display/**/*',
        ],
    },
}
