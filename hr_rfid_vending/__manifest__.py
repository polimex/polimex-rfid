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
        'security/hr_rfid_multi_company.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/hr_rfid_ctrl.xml',
        'views/hr_rfid_vending_auto_refill.xml',
        'views/hr_rfid_vending_balance_history.xml',
        'views/vending_event.xml',
        'views/vending_menus.xml',
        'views/digest_views.xml',
    ],

    'demo': [ ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
