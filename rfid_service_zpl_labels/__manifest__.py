{
    'name': "RFID Services ZPL Labels",

    'summary': """
        RFID Service system ZPL labels
    """,

    'description': """
        RFID Service system ZPL labels
        
        This module generates ZPL (Zebra Programming Language) formatted wristband labels
        for RFID services. The output can be sent to Zebra printers through:
        - Odoo IoT Box
        - Direct file printing
        - Third-party printing modules (OCA printer_zpl2, etc.)
        
        Note: For Odoo 18.0, direct printer integration requires additional modules
        or IoT Box connectivity.
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    'category': "Generic Modules/Property Management System",
    'version': '18.0.0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['rfid_service_base'],

    # always loaded
    'data': [
        'views/rfid_service.xml',
        'views/rfid_service_sale_wiz.xml',
        'reports/report_wristband.xml',
    ],
    # 'images': ['static/images/main_screenshot.png'],
    "application": False,
}
