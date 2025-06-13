{
    'name': "Services ZPL Labels",

    'summary': """
        Service system ZPL labels
    """,

    'description': """
Service ZPL Wristband Label Printing
====================================

Generate professional ZPL-formatted wristband labels for RFID services with integrated 
barcode scanning and direct printer communication.

Key Features
------------
* **Direct Printer Communication**: Send labels directly to Zebra printers via network socket
* **Barcode Integration**: Automatic CODE-128 barcode generation with service information
* **Customizable Design**: Configure label dimensions, DPI settings, and layout parameters
* **Multi-Company Support**: Company-specific branding and settings
* **Real-time Preview**: Web-based label preview before printing
* **Test Functionality**: Built-in printer connection testing

Configuration
-------------
Navigate to Services → Configuration → Settings to configure:

* Label dimensions (width/height in mm)
* Printer DPI (203/300 dots per inch)
* Network printer IP address and port
* Company logo and branding elements

Usage Workflow
--------------
1. Create a new service sale through the RFID Service Sale wizard
2. Configure service details (dates, visitor information, access permissions)
3. Click "Print Label" to generate the wristband
4. Label is sent directly to the configured Zebra printer

Technical Specifications
------------------------
* **Label Format**: ZPL (Zebra Programming Language)
* **Barcode Type**: CODE-128 automatic subset selection
* **Default Dimensions**: 100mm x 50mm (customizable)
* **Supported Printers**: All Zebra printers with ZPL support
* **Network Protocol**: Direct TCP socket communication

Integration Options
-------------------
* **CUPS Integration**: Install `rfid_service_zpl_labels_cups` for CUPS printing support
* **Multi-User Environments**: CUPS module recommended for concurrent user access
* **API Access**: Programmatic label generation via service model methods

Security & Compliance
---------------------
* Role-based access control for label printing
* Audit trail for all printed labels
* Support for visitor data protection requirements
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    'category': "Generic Modules/Property Management System",
    'version': '18.0.1.0.0',

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
