{
    'name': "RFID Service system Base",

    'summary': """
        Base module for visitor management and temporary RFID access control
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': "Generic Modules/Property Management System",
    'version': '19.0.0.11.3',

    'depends': ['hr_rfid', 'onboarding'],
    'data': [
        'security/rfid_service_base_security.xml',
        'security/ir.model.access.csv',
        'views/rfid_service.xml',
        'views/rfid_service_sale.xml',
        'views/rfid_service_sale_wiz.xml',
        'views/res_partner_views.xml',
        'views/menus.xml',
        'data/data.xml',
        'data/onboarding_data.xml',
        'security/rfid_services_multi_company.xml',
    ],
    'demo': [
        'demo/rfid_service_demo.xml',
        'demo/rfid_service_base_demo_showcase.xml',
    ],
    'application': True,
    'installable': True,
    'assets': {
        'web.assets_tests': [
            'rfid_service_base/static/tests/tours/*.js',
        ],
    },
}
