{
    'name': "RFID PMS Base system Base",

    'summary': """
        RFID PMS system Base structures
    """,

    'description': """
        RFID PMS system Base structures
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': "Generic Modules/Property Management System",
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['hr_rfid', 'barcodes'],

    # always loaded
    'data': [
        'security/pms_base_security.xml',
        'security/ir.model.access.csv',
        'views/wiz_card_from_room.xml',
        'views/room.xml',
        'views/views.xml',
        'views/menus.xml',
        'data/data.xml',
    ],
    "application": True,
}
# -*- coding: utf-8 -*-
