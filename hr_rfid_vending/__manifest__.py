# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': "hr_rfid_vending",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': [ 'base', 'hr_rfid', 'stock' ],

    'data': [
        'data/hr_rfid_vending_cron_jobs.xml',
        'views/hr_employee_views.xml',
        'views/hr_rfid_views.xml',
        'security/ir.model.access.csv',
    ],
}