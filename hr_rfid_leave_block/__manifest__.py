# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
{
    'name': 'RFID Access Block on Leave',
    'version': '19.0.1.0.1',
    'category': 'Human Resources',
    'summary': 'Suspend RFID cards while an employee is on approved leave',
    'author': 'Polimex',
    'website': 'https://polimex.co',
    'license': 'AGPL-3',

    'depends': ['hr_rfid', 'hr_holidays'],

    'data': [
        'security/ir.model.access.csv',
        'security/hr_rfid_leave_block_rules.xml',
        'data/ir_cron.xml',
        'views/hr_rfid_leave_block_views.xml',
    ],

    'demo': [
        'demo/hr_rfid_leave_block_demo_showcase.xml',
    ],

    'assets': {
        'web.assets_tests': [
            'hr_rfid_leave_block/static/tests/tours/*.js',
        ],
    },

    'installable': True,
    'auto_install': False,
}
