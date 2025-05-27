{
    'name': "RFID Service system ZPL labels",

    'summary': """
        RFID Service system ZPL labels
    """,

    'description': """
        RFID Service system ZPL labels
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': "Generic Modules/Property Management System",
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['rfid_service_base','base_report_to_label_printer'],

    # always loaded
    'data': [
        'reports/report_wristband.xml',
    ],
    "application": False,
}
# -*- coding: utf-8 -*-
