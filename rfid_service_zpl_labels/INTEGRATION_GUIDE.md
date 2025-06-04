# Integration Guide for RFID Service ZPL Labels

This guide explains how to integrate the `rfid_service_zpl_labels` module with various printing solutions in Odoo 18.

## Overview

The `rfid_service_zpl_labels` module generates ZPL (Zebra Programming Language) formatted wristband labels for RFID services. The module outputs raw ZPL commands that can be sent to Zebra label printers through various methods.

## Prerequisites

- Odoo 18.0
- `rfid_service_base` module installed
- Zebra ZPL-compatible label printer
- Network or USB connection to the printer

## Integration Options

### Option 1: Using OCA's base_report_to_label_printer (Recommended)

This approach provides the best integration with Odoo's printing system.

#### Installation

1. Install the OCA printing modules:
```bash
# Install base printing modules first
./odoo-bin -d your_database --init=base_report_to_printer,base_report_to_label_printer -p 8018

# Then install the RFID module
./odoo-bin -d your_database --init=rfid_service_zpl_labels -p 8018
```

2. Configure CUPS on your server:
```bash
# Install CUPS if not already installed
sudo apt-get install cups cups-client

# Add your Zebra printer as a RAW printer
sudo lpadmin -p zebra_wristband -v socket://PRINTER_IP:9100 -E -m raw
# Or for USB printer:
sudo lpadmin -p zebra_wristband -v usb://Zebra/MODEL -E -m raw
```

#### Configuration in Odoo

1. **Set up Print Server:**
   - Navigate to Settings → Technical → Printing → Servers
   - Create a new server:
     - Name: Local CUPS Server
     - Address: localhost (or your CUPS server IP)
     - Port: 631

2. **Add Printers:**
   - Go to Settings → Technical → Printing → Printers
   - Click "Update Printers from Server"
   - Select your Zebra printer

3. **Mark Report as Label Report:**
   - Go to Settings → Technical → Actions → Reports
   - Find "Patient Wristband (ZPL)"
   - Check the "Label" checkbox

4. **Configure User Preferences:**
   - Each user should set their default label printer in their preferences

### Option 2: Direct Network Printing

For direct printing without additional modules, you can extend the sale wizard:

```python
import socket

class RfidServiceSaleWiz(models.TransientModel):
    _inherit = 'rfid.service.sale.wiz'
    
    def print_label_direct(self):
        """Direct print to network printer"""
        # Generate the report
        report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
        zpl_content, _ = report._render([self.id])
        
        # Send to printer
        printer_ip = self.env['ir.config_parameter'].sudo().get_param('rfid.label.printer.ip', '192.168.1.100')
        printer_port = int(self.env['ir.config_parameter'].sudo().get_param('rfid.label.printer.port', '9100'))
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((printer_ip, printer_port))
        sock.send(zpl_content.encode())
        sock.close()
        
        return {'type': 'ir.actions.act_window_close'}
```

### Option 3: File Export and Manual Printing

The simplest approach - save ZPL and print manually:

```python
import tempfile
import os

class RfidServiceSaleWiz(models.TransientModel):
    _inherit = 'rfid.service.sale.wiz'
    
    def export_zpl_file(self):
        """Export ZPL to file for manual printing"""
        report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
        zpl_content, _ = report._render([self.id])
        
        # Create temporary file
        fd, path = tempfile.mkstemp(suffix='.zpl', prefix='wristband_')
        with os.fdopen(fd, 'w') as tmp:
            tmp.write(zpl_content.decode() if isinstance(zpl_content, bytes) else zpl_content)
        
        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=rfid.service.sale.wiz&id={self.id}&filename=wristband.zpl&field=zpl_file&download=true',
            'target': 'self',
        }
```

### Option 4: Using Odoo IoT Box

If you have an Odoo IoT Box:

1. Connect the Zebra printer to the IoT Box
2. The printer will appear automatically in Odoo
3. Print directly from the report action

## System Parameters

You can configure the following system parameters for the module:

```python
# In Settings → Technical → Parameters → System Parameters

# For direct network printing
rfid.label.printer.ip = 192.168.1.100
rfid.label.printer.port = 9100

# For file export location
rfid.label.export.path = /tmp/rfid_labels
```

## Troubleshooting

### ZPL Not Printing Correctly

1. **Check ZPL Syntax:**
   - Save the generated ZPL to a file
   - Test with Zebra's ZPL viewer or labelary.com
   - Ensure all coordinates fit within 812×203 dots (1×11 inch at 203 DPI)

2. **Printer Configuration:**
   - Ensure printer is set to ZPL mode (not EPL)
   - Check printer DPI matches report (203 DPI)
   - Verify label size is correctly set

3. **Network Issues:**
   - Test printer connectivity: `telnet PRINTER_IP 9100`
   - Check firewall rules
   - Verify printer accepts RAW socket connections

### Logo Not Displaying

1. Upload company logo to printer memory as `COMPLOGO.GRF`
2. Or remove logo line from the ZPL template if not needed

### Barcode Issues

- Ensure card numbers are numeric
- The system pads numbers to 10 digits with leading zeros
- CODE-128 requires specific character sets

## Extending the Module

### Adding Custom Fields to Labels

Edit `reports/report_wristband.xml`:

```xml
<!-- Add custom field after patient name -->
^FO20,120
^A0N,24,24^FD<t t-out="sale.custom_field"/>^FS
```

### Changing Label Size

Modify the paper format in `reports/report_wristband.xml`:

```xml
<record id="paperformat_wristband_custom" model="report.paperformat">
    <field name="name">Custom Wristband</field>
    <field name="page_width">50</field>  <!-- mm -->
    <field name="page_height">100</field> <!-- mm -->
</record>
```

### Adding Print Options

Extend the wizard to add print options:

```python
class RfidServiceSaleWiz(models.TransientModel):
    _inherit = 'rfid.service.sale.wiz'
    
    print_copies = fields.Integer('Copies', default=1)
    print_darkness = fields.Integer('Darkness', default=15, help='0-30')
    
    def print_label(self):
        # Add darkness setting to ZPL
        # ^SD15 sets darkness to 15
        return super().print_label()
```

## Best Practices

1. **Always test** ZPL output with a viewer before sending to printer
2. **Keep backups** of working ZPL templates
3. **Document** any custom printer settings
4. **Monitor** printer status and paper levels
5. **Use system parameters** for configuration instead of hardcoding

## Support

For issues specific to:
- RFID functionality: Check `rfid_service_base` documentation
- ZPL syntax: Refer to Zebra Programming Guide
- Printing problems: Review CUPS/printer logs
- Odoo integration: Check Odoo printing framework documentation