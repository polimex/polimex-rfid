# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Vending Control',
    'version': '1.6',
    'category': 'Vending',
    'summary': 'Manage EXECUTIVE based vending machines',
    'author': 'Polimex',
    'license': 'AGPL-3',

    'website': 'http://www.securitybulgaria.com',

    'depends': [ 'base', 'hr_rfid', 'stock', 'hr_attendance' ],

    'data': [
        'data/hr_rfid_vending_cron_jobs.xml',
        'data/hr_rfid_vending_sequence.xml',
        'security/hr_rfid_vending_security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/hr_rfid_views.xml',
    ],

    'demo': [ ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
