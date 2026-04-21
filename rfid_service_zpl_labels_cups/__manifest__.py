{
    'name': "Services ZPL Labels - CUPS Integration",

    'summary': """
        Replace direct ZPL printing with CUPS queue management
    """,

    'description': """
RFID Service ZPL Labels - CUPS Integration
==========================================

Seamlessly replaces direct network printing with CUPS-managed print queues,
providing better control and monitoring for ZPL wristband printing.

What This Module Does
---------------------
* **Replaces Socket Printing**: Overrides direct TCP printing with CUPS queues
* **User-Specific Printers**: Each user can have their own default label printer
* **Queue Management**: Monitor print jobs, cancel stuck prints, reprint failed jobs
* **Automatic Fallback**: Downloads ZPL file if printer is unavailable
* **Multi-Printer Support**: Different users can print to different printers

Quick Start Guide
-----------------
1. **Install Prerequisites**:
   - Ensure CUPS is installed on your server
   - Install `base_report_to_label_printer` module
   - Configure your Zebra printer in CUPS

2. **Configure User Preferences** (mandatory for each user):
   - Go to: Settings → Users & Companies → Users → Select User
   - In Preferences tab, find Printing section:
     * Default Label Printer: Select your CUPS Zebra printer
     * Printing Action: MUST be "Send to Printer"
   - Save the user

3. **Test Configuration**:
   - Open any RFID Service
   - Click "Test CUPS Printer" button
   - Verify test label prints correctly

How It Works
------------
This module inherits and modifies the behavior of `rfid_service_zpl_labels`:
- `print_label_direct()` → Now sends to CUPS instead of socket
- `_send_zpl_to_printer()` → Redirects to CUPS printing system
- Preview functionality remains unchanged

Benefits Over Direct Printing
-----------------------------
* **Reliability**: CUPS handles printer offline/busy states
* **Multi-User**: No conflicts when multiple users print simultaneously  
* **Monitoring**: View print queue status and history
* **Flexibility**: Easy to change printers without reconfiguration
* **Security**: No need to expose printer ports on network

Troubleshooting
---------------
**Labels download as files instead of printing:**
- User's "Printing Action" must be "Send to Printer" (not "Download")
- User must have a "Default Label Printer" selected
- The printer must be properly configured in CUPS

**"No printer found" errors:**
- Check CUPS service is running: `sudo systemctl status cups`
- Verify printer in CUPS: `lpstat -p`
- Ensure user has printer selected in preferences

**Test print works but regular printing fails:**
- Clear browser cache
- Re-select printer in user preferences
- Check CUPS error log: `/var/log/cups/error_log`

Technical Notes
---------------
* Uses Odoo's printing.printer model for CUPS integration
* ZPL content is sent raw to CUPS with `-o raw` option
* Auto-installs when both dependencies are present
* No additional configuration needed beyond user preferences
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    'category': "Generic Modules/Property Management System",
    'version': '19.0.0.1.3',

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
        'views/rfid_service_sale.xml',
    ],

    # base_report_to_label_printer lives in OCA repo report-print-send and is
    # not bundled in this repository. Keep installable=False so the Odoo Apps
    # validator does not flag an unmet dependency. Flip to True after adding
    # the OCA repo to the addons path.
    'installable': False,
    "application": False,
}