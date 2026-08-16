# -*- coding: utf-8 -*-
{
    'name': 'RFID Odoo Data Import',
    'version': '19.0.2.14.0',
    'category': 'HR',
    'summary': 'Import RFID access control data from older Odoo instances (v14-v18)',
    'author': 'Polimex Dev Team',
    'license': 'AGPL-3',

    'website': 'https://polimex.co',

    'depends': ['hr_rfid'],

    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/import_wizard_views.xml',
        'views/import_run_views.xml',
    ],

    'assets': {
        'web.assets_tests': [
            'hr_rfid_odoo_import/static/tests/tours/**/*.js',
        ],
    },

    'installable': True,
    'application': False,
    'auto_install': False,
}
