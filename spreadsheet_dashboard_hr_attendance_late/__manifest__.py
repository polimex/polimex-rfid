# -*- coding: utf-8 -*-
{
    'name': "Working Time Dashboard",
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Dashboard',
    'summary': "Ready-made Dashboards KPI board for RFID working time",
    'author': 'Polimex Dev Team',
    'website': 'https://polimex.co',
    'license': 'AGPL-3',
    'depends': ['spreadsheet_dashboard', 'hr_attendance_late'],
    'data': [
        'data/dashboards.xml',
    ],
    'auto_install': ['hr_attendance_late'],
    'installable': True,
    'application': False,
}
