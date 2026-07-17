# -*- coding: utf-8 -*-
{
    'name': "Access Control Dashboard - Sites",
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Dashboard',
    'summary': "Adds a Site filter to the access-control dashboards",
    'author': 'Polimex Dev Team',
    'website': 'https://polimex.co',
    'license': 'AGPL-3',
    'depends': ['spreadsheet_dashboard_hr_rfid', 'hr_rfid_site_manager'],
    'data': [
        'data/dashboards.xml',
    ],
    'auto_install': True,
    'installable': True,
    'application': False,
}
