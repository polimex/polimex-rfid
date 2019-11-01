# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Access Control Auto Refresh',
    'version': '0.1',
    'category': 'Extra Tools',
    'summary': '',
    'author': 'Polimex',
    'license': 'AGPL-3',

    'website': 'https://www.securitybulgaria.com/',

    'depends': [ 'base', 'hr_rfid', 'muk_web_client_refresh' ],

    'data': [ 'data/auto_refresh_data.xml' ],

    'demo': [ ],

    'application': False,
    'installable': True,
    'auto_install': True,
}