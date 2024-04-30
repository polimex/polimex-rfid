# -*- coding: utf-8 -*-
{
    'name': "HR RFID Events Notifications",

    'summary': """
        Add notification on Doors, Employees, Contacts ...
    """,

    'description': """
        Add notification on Doors, Employees, Contacts ...
    """,

    'author': "Polimex Team <software@polimex.co>",
    'website': "https://polimex.co",

    # for the full list
    'category': 'Administration',
    'version': '0.2',
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['hr_rfid'],

    # always loaded
    'data': [
        'security/hr_rfid_visitor_security.xml',
        'security/ir.model.access.csv',
        'views/hr_rfid_visitor_management_visits.xml',
        'views/hr_rfid_visitor_management.xml',
        'views/hr_rfid_visitor_menus.xml',
    ],
    # only loaded in demonstration mode

    'application': False,
    'auto_install': False
}
