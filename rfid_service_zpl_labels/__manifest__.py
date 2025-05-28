{
    'name': "RFID Services ZPL Labels",

    'summary': """
        RFID Service system ZPL labels
    """,

    'description': """
        RFID Service system ZPL labels
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    'category': "Generic Modules/Property Management System",
    'version': '18.0.0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['rfid_service_base','base_report_to_label_printer'],

    # always loaded
    'data': [
        'views/rfid_service.xml',
        'views/rfid_service_sale_wiz.xml',
        'reports/report_wristband.xml',
    ],
    # 'images': ['static/images/main_screenshot.png'],
    "application": False,
}
