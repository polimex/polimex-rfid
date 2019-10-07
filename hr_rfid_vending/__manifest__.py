# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Vending Control',
    'version': '0.3',
    'category': 'Vending',
    'summary': 'Manage vending machines',
    'author': 'Polimex',
    'license': 'GPL-3',

    'website': 'http://www.securitybulgaria.com',

    'depends': [ 'base', 'hr_rfid', 'stock' ],

    'data': [
        'data/hr_rfid_vending_cron_jobs.xml',
        'data/hr_rfid_vending_sequence.xml',
        'security/hr_rfid_vending_security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/hr_rfid_views.xml',
    ],

    'demo': [ ],

    'images': [ ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
