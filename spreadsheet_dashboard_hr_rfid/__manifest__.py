# -*- coding: utf-8 -*-
{
    'name': "Access Control Dashboard",
    'version': '19.0.1.0.1',
    'category': 'Human Resources/Dashboard',
    'summary': "Ready-made Dashboards KPI board for RFID access control",
    'author': 'Polimex Dev Team',
    'website': 'https://polimex.co',
    'license': 'AGPL-3',
    'depends': ['spreadsheet_dashboard', 'hr_rfid'],
    'data': [
        'data/dashboards.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'spreadsheet_dashboard_hr_rfid/static/tests/tours/*.js',
        ],
    },
    'auto_install': ['hr_rfid'],
    'installable': True,
    'application': False,
}
