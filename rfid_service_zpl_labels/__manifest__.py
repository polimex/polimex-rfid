{
    'name': "Services ZPL Labels",

    'summary': """
        Service system ZPL labels
    """,

    'description': """
        Service ZPL Wristband Label Printing
        ====================================
        
        This module generates ZPL (Zebra Programming Language) formatted wristband labels
        for services. Labels include QR codes, service information, and company branding.
        
        Setup Instructions:
        ------------------
        1. Configure label printer settings in Service form:
           - Label Width (mm) - default: 100
           - Label Height (mm) - default: 50
           - Printer DPI - default: 203 (8 dots/mm)
           - Printer IP & Port for direct socket printing
        
        2. Test printer connection using "Test Label Printer" button
        
        Usage:
        ------
        1. Create Service Sale through the sale wizard
        2. Click "Print Label" to generate and send the wristband label
        3. The label will be sent directly to the configured printer
        
        Features:
        ---------
        - Direct socket printing to Zebra printers
        - QR code with service information
        - Company logo support (converted to ZPL graphics)
        - Customizable label dimensions
        - Test printing functionality
        
        Note: For CUPS printing integration, install the rfid_service_zpl_labels_cups module.
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    'category': "Generic Modules/Property Management System",
    'version': '18.0.0.2.0',

    # any module necessary for this one to work correctly
    'depends': ['rfid_service_base', 'hr_rfid'],

    # always loaded
    'data': [
        'data/system_parameters.xml',
        'data/server_actions.xml',
        'reports/report_wristband.xml',
        'views/rfid_service.xml',
        'views/rfid_service_sale_wiz.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    # 'images': ['static/images/main_screenshot.png'],
    "application": False,
}
