# -*- coding: utf-8 -*-
{
    'name': 'RFID Polimex Old Cloud Import',
    'version': '1.1',
    'category': 'HR',
    'summary': 'Import access control data from my.polimex.online and schoolsafety.online',
    'author': 'Polimex',
    'license': 'AGPL-3',

    'website': 'https://polimex.co',

    'depends': ['hr_rfid'],

    'external_dependencies': {
        # 'python': ['fdb']
    },

    'data': [
        'security/ir.model.access.csv',
        'views/welcome_wizard.xml',
        'views/import_wizard.xml',
    ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
