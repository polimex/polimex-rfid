# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'hr_barcode',
    'version': '1.12',
    'category': 'Human Resources',
    'summary': '',
    'author': 'Polimex',
    'license': 'AGPL-3',

    'website': "http://www.yourcompany.com",

    'depends': [ 'base', 'hr_rfid', 'hr_attendance' ],

    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],

    'qweb': [ ],

    'demo': [ ],

    "images": [
        # 'static/images/main_screenshot.png',
    ],

    'application': True,
    'installable': True,
    'auto_install': False,
}