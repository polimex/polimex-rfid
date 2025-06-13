{
    'name': "Services ZPL Labels",

    'summary': """
        ZPL wristband printing for RFID services with direct network printing
    """,

    'description': """
RFID Service ZPL Label Printing
===============================

Extends the RFID Service Base module with professional ZPL wristband printing capabilities,
enabling direct network printing to Zebra label printers.

Key Features
------------
* **Dual Template System**: Choose between QR Code or traditional CODE-128 barcode formats
* **Direct Network Printing**: Send ZPL commands directly to printer via TCP socket
* **Web-Based Preview**: Preview labels in browser before printing
* **Multi-Company Support**: Company-specific printer settings
* **Test Printing**: Verify printer connectivity with test labels
* **Customizable Templates**: Modify label layout and content

Quick Start Guide
-----------------
1. **Configure Printer** (Settings → Technical → System Parameters):
   - `rfid.label.printer.ip`: Your Zebra printer IP address
   - `rfid.label.printer.port`: Printer port (default: 9100)

2. **Select Label Template** (RFID Services → Services → Your Service):
   - Choose between "Customer Wristband - QR Code (ZPL)" for 2D QR codes
   - Or "Customer Wristband - CODE-128 (ZPL)" for 1D barcodes

3. **Print Labels**:
   - From Service Sale: Click "Print Label Direct" or "Preview Label"
   - From Wizard: Click "Print Label" after creating service sale
   - Test connection: Use "Test Label Printer" in service form

Label Information
-----------------
Wristbands include:
* Company name
* Service name  
* Customer/visitor name
* QR code or barcode with card number
* Service validity dates

Technical Details
-----------------
* **Label Size**: 1×11 inch (25×279mm) wristband format
* **Resolution**: 203 DPI (8 dots/mm)
* **Protocols**: Raw TCP socket on port 9100
* **Templates**: QWeb-based ZPL generation
* **Barcode Types**: QR Code (2D) or CODE-128 (1D)

Troubleshooting
---------------
* **Connection Timeout**: Check printer IP and network connectivity
* **Blank Labels**: Verify ZPL template syntax and printer compatibility
* **Wrong Size**: Ensure printer is configured for 1×11 inch labels

For CUPS printing support, install `rfid_service_zpl_labels_cups` module.
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
