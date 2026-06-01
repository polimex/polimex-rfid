{
    'name': "Services ZPL Labels",

    'summary': """
        ZPL wristband printing for RFID services with direct network printing
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    'category': "Generic Modules/Property Management System",
    'version': '19.0.1.0.2',

    # any module necessary for this one to work correctly
    'depends': ['rfid_service_base', 'hr_rfid'],

    # always loaded
    'data': [
        'data/system_parameters.xml',
        'data/server_actions.xml',
        'reports/report_wristband.xml',
        'views/rfid_service.xml',
        'views/rfid_service_sale.xml',
        'views/rfid_service_sale_wiz.xml',
        'views/res_config_settings_views.xml',
        'views/label_preview_template.xml',
        'views/menu.xml',
    ],
    # 'images': ['static/images/main_screenshot.png'],
    "application": False,
}
