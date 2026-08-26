# -*- coding: utf-8 -*-
{
    'name': "Labour Cost Dashboard",
    'version': '19.0.1.0.1',
    'category': 'Human Resources/Dashboard',
    'summary': "Ready-made Dashboards KPI board for RFID labour cost",
    'author': 'Polimex Dev Team',
    'website': 'https://polimex.co',
    'license': 'AGPL-3',
    'depends': ['spreadsheet_dashboard', 'hr_attendace_rfid_hr_hourly_cost'],
    'data': [
        'data/dashboards.xml',
    ],
    'auto_install': ['hr_attendace_rfid_hr_hourly_cost'],
    'installable': True,
    'application': False,
}
