{
    'name': "RFID Service system Base",

    'summary': """
        RFID Service system Base structures
    """,

    'description': """
        RFID Service system Base structures
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': "Generic Modules/Property Management System",
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['hr_rfid'],

    # always loaded
    'data': [
        'security/rfid_service_base_security.xml',
        'security/ir.model.access.csv',
        'views/rfid_service.xml',
        'views/rfid_service_sale.xml',
        'views/rfid_service_sale_wiz.xml',
        'views/res_partner_views.xml',
        'views/menus.xml',
        'data/data.xml',
        'security/rfid_services_multi_company.xml',
    ],
    "demo": [
        'demo/rfid_service_demo.xml',
    ],
    "application": True,
}
# -*- coding: utf-8 -*-
