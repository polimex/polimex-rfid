# -*- coding: utf-8 -*-
{
    'name': 'RFID Odoo Data Import',
    'version': '19.0.1.11.0',
    'category': 'HR',
    'summary': 'Import RFID access control data from older Odoo instances (v14-v18)',
    'author': 'Polimex Dev Team',
    'license': 'AGPL-3',

    'website': 'https://polimex.co',

    'depends': ['hr_rfid'],

    'data': [
        'security/ir.model.access.csv',
        'views/import_wizard_views.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
