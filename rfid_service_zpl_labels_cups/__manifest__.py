{
    'name': "Services ZPL Labels - CUPS Integration",

    'summary': """
        CUPS printer integration for Service ZPL labels
    """,

    'description': """
        CUPS Printer Integration for Service Labels
        ============================================
        
        This module provides CUPS printing integration for Service ZPL wristband labels,
        replacing direct socket printing with managed print queues.
        
        Prerequisites:
        --------------
        - CUPS printer configured on your system
        - base_report_to_label_printer module installed
        - rfid_service_zpl_labels module installed
        
        User Setup (Required for each user):
        ------------------------------------
        1. Go to Settings → Users & Companies → Users → Your User
        2. In Preferences tab, Printing section:
           - Set "Default Label Printer" to your CUPS label printer
           - Set "Printing Action" to "Send to Printer" (NOT "Open a PDF")
        
        Usage:
        ------
        1. After setup, printing works automatically through CUPS
        2. Click "Print Label" in the sale wizard
        3. Labels are sent directly to your configured printer
        4. Test using "Test CUPS Printer" button in Service form
        
        Features:
        ---------
        - Automatic CUPS printer detection
        - Print queue management
        - Print job status monitoring
        - Fallback to download if printer unavailable
        - User-specific printer settings
        
        Troubleshooting:
        ----------------
        If labels download instead of printing:
        - Check that "Printing Action" is set to "Send to Printer"
        - Verify the label printer is selected in user preferences
        - Ensure CUPS service is running
        
        This module auto-installs when both dependencies are present.
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    'category': "Generic Modules/Property Management System",
    'version': '18.0.0.1.2',

    # This module depends on both ZPL labels and CUPS printing
    'depends': [
        'rfid_service_zpl_labels',
        'base_report_to_label_printer',
    ],

    # Auto-install when both dependencies are installed
    'auto_install': True,

    # always loaded
    'data': [
        'data/report_config.xml',
        'data/server_actions.xml',
        'views/rfid_service.xml',
    ],
    
    "application": False,
}