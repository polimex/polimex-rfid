# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Vending Control',
    'version': '1.6',
    'category': 'Vending',
    'summary': 'Manage EXECUTIVE based vending machines',
    'author': 'Polimex Dev Team',
    'license': 'AGPL-3',

    'website': 'https://polimex.co',

    'depends': ['hr_rfid', 'product', 'hr_attendance'],

    'data': [
        'data/hr_rfid_vending_cron_jobs.xml',
        'data/hr_rfid_vending_sequence.xml',
        'security/hr_rfid_vending_security.xml',
        'security/hr_rfid_multi_company.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/ctrl_cash_collect_wizard.xml',
        'views/ctrl_cash_collect_log.xml',
        'views/hr_rfid_ctrl.xml',
        'views/hr_rfid_vending_auto_refill.xml',
        'views/hr_rfid_vending_balance_history.xml',
        'views/vending_event.xml',
        'views/vending_menus.xml',
        'views/digest_views.xml',
        # 'views/res_config_setting_view.xml',
        'views/res_company.xml',
    ],

    'demo': [ ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
