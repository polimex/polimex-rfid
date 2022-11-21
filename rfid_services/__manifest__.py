# -*- coding: utf-8 -*-
{
    'name': "RFID Services",

    'summary': """
        Module for management RFID services """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",

    'category': 'Sales/Sales',
    'version': '0.1',
    'license': 'LGPL-3',

    'depends': ['hr_rfid', 'product'],

    'data': [
        'security/ir.model.access.csv',
        'security/rfid_services_security.xml',
        'data/seq_rfid_service_sale.xml',
        'views/product_template.xml',
        'views/rfid_service_sale.xml',
        'wizards/rfid_service_sale_wiz.xml',
        'views/menus.xml',
    ],
    'application': True
}
