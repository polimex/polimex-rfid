# RFID Services ZPL Labels

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-875A7B.svg)](https://www.odoo.com/)
[![Module Version](https://img.shields.io/badge/Module_Version-18.0.1.0.0-success.svg)](https://github.com/polimex)

Professional ZPL wristband printing for RFID access control and visitor management systems.

## Overview

The RFID Services ZPL Labels module extends Odoo's RFID service capabilities with enterprise-grade wristband printing functionality. Generate and print professional-quality wristbands directly to Zebra printers using native ZPL (Zebra Programming Language), perfect for visitor management, event registration, healthcare identification, and temporary access control.

### ⚠️ Multi-User Environment Notice

For deployments with **multiple concurrent users**, install the companion module `rfid_service_zpl_labels_cups` to ensure:
- Proper print queue management
- Prevention of print job conflicts
- User-specific printer assignments
- Centralized print job tracking

Single-user installations can utilize the base module's direct socket printing capabilities.

## Key Features

### 🏷️ Wristband Generation
- **Native ZPL II Format** - Direct Zebra Programming Language output
- **Automatic Barcode Generation** - CODE-128 barcodes with service information
- **Flexible Templates** - Customizable wristband layouts via QWeb
- **Multiple Size Support** - Standard 1×11 inch and custom dimensions

### 🖨️ Printing Capabilities
- **Direct Network Printing** - TCP/IP socket communication to Zebra printers
- **Company Branding** - Automatic inclusion of company logos and information
- **Dynamic Content** - Service type, validity dates, and access permissions
- **Visitor Information** - Name, ID, and custom fields support

### 🔗 System Integration
- **RFID Service Integration** - Seamless operation with rfid_service_base
- **Batch Processing** - Print multiple wristbands in a single operation
- **Multi-Company Support** - Company-specific settings and branding
- **Portal Compatibility** - Full integration with service portal features

## Requirements

### System Requirements
- **Odoo**: Version 18.0 or higher
- **Python**: 3.8+
- **Dependencies**: `rfid_service_base`, `hr_rfid`
- **Hardware**: Zebra ZPL-compatible printer

### Printing Infrastructure Options
| Method | Description | Best For |
|--------|-------------|----------|
| **Direct Socket** | TCP/IP communication | Single workstation |
| **CUPS Integration** | Linux print server | Multi-user environments |
| **Odoo IoT Box** | Official hardware solution | Cloud deployments |
| **File Export** | Save ZPL for manual printing | Testing/debugging |
| **OCA Modules** | Community printing solutions | Advanced setups |

## Installation

### Standard Installation

1. **Prerequisites**
   ```bash
   # Ensure rfid_service_base is installed
   ./odoo-bin -d your_database --init=rfid_service_base
   ```

2. **Module Installation**
   ```bash
   # Install the ZPL labels module
   ./odoo-bin -d your_database --init=rfid_service_zpl_labels
   ```

3. **Multi-User Setup** (if applicable)
   ```bash
   # Install CUPS integration for multi-user environments
   ./odoo-bin -d your_database --init=rfid_service_zpl_labels_cups
   ```

## Configuration

### Printer Setup

#### 1. Zebra Printer Configuration
- Enable ZPL command processing on your printer
- Configure network settings for TCP/IP printers
- Set appropriate DPI (203 or 300)
- Test connectivity with sample ZPL commands

#### 2. System Parameters (Odoo)
Navigate to **Settings → Technical → Parameters → System Parameters**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rfid_service.label_width` | 100 | Label width in mm |
| `rfid_service.label_height` | 50 | Label height in mm |
| `rfid_service.printer_dpi` | 203 | Printer resolution |
| `rfid_service.printer_ip` | - | Printer IP address |
| `rfid_service.printer_port` | 9100 | Printer port |

### Wristband Specifications

**Standard Template**:
- **Dimensions**: 1×11 inches (25×279mm)
- **Resolution**: 203 DPI (8 dots/mm)
- **Orientation**: Portrait
- **Layout**: 4-column design with company branding


## Usage

### Printing Wristbands

#### Single Wristband Printing
1. Navigate to **RFID Services → Service Sales**
2. Open the desired service sale record
3. Click **"Print Label"** button
4. The wristband is sent directly to the configured printer

#### Batch Printing
1. Go to **RFID Services → Service Sales**
2. Select multiple service sale records
3. Choose **Action → Print Wristbands**
4. All selected wristbands print sequentially

### Printing Methods

#### Method 1: Direct Socket Printing (Built-in)
The module includes direct socket printing functionality:
```python
# Automatic when clicking "Print Label"
# Sends ZPL directly to printer_ip:printer_port
```

#### Method 2: File Export
```bash
# Linux - Using lpr
lpr -P zebra_printer wristband.zpl

# Windows - Copy to printer share
copy wristband.zpl \\computer\zebra_printer

# macOS - Using lp
lp -d zebra_printer wristband.zpl
```

#### Method 3: Python Script
```python
import socket

def send_zpl_to_printer(zpl_content, printer_ip="192.168.1.100", printer_port=9100):
    """Send ZPL data to network printer"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((printer_ip, printer_port))
        sock.send(zpl_content.encode('utf-8'))
    finally:
        sock.close()
```

## ZPL Format Details

### Sample ZPL Output
```zpl
^XA^CI28
^PW203 ^LL2233 ^LH0,0

; COLUMN 1: Company + Service Information
^FO90,150
^A0R,24,24^FDYour Company Name^FS
^FO60,150
^A0R,22,22^FDService Type^FS

; COLUMN 2: Visitor Name
^FO85,750
^A0R,30,30^FDVisitor Name^FS

; COLUMN 3: Barcode with Service ID
^FO60,1250
^BY2,2,80
^BCR,80,N,N,N
^FDService-ID-Here^FS

; COLUMN 4: Validity Period
^FO85,1800
^A0R,18,18^FDFrom: Date Time^FS
^FO55,1800
^A0R,18,18^FDTo: Date Time^FS

^XZ
```

### Customizing the Template

The wristband layout is defined in `reports/report_wristband.xml` using QWeb syntax:

1. **Position Adjustment**: Modify `^FO` (Field Origin) coordinates
2. **Font Changes**: Adjust `^A` (Font) parameters
3. **Barcode Settings**: Configure `^BC` (Code 128) parameters
4. **Add Custom Fields**: Extend the template with additional data

## API Reference

### Programmatic Label Generation

```python
from odoo import models

class RfidServiceSale(models.Model):
    _inherit = 'rfid.service.sale'
    
    def generate_wristband_zpl(self):
        """Generate ZPL data for wristband"""
        self.ensure_one()
        report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
        zpl_data, _ = report.render_qweb_text(self.ids)
        return zpl_data  # Returns ZPL string
```

### Extending Wristband Data

```python
from odoo import fields, models

class RfidServiceSaleCustom(models.Model):
    _inherit = 'rfid.service.sale'
    
    # Add custom fields that will appear on wristband
    wristband_color = fields.Selection([
        ('red', 'Red - VIP'),
        ('blue', 'Blue - Standard'),
        ('green', 'Green - Staff'),
    ], string='Wristband Color')
    
    emergency_contact = fields.Char('Emergency Contact')
    medical_info = fields.Text('Medical Information')
```

### Direct Printing Method

```python
def print_label_direct(self):
    """Send label directly to configured printer"""
    for rec in self:
        zpl_data = rec.generate_wristband_zpl()
        # Send to printer using the service's print method
        rec.service_id.print_label_direct()
        # Log the printing action
        rec.message_post(body="Wristband printed successfully")
```

## Troubleshooting

### Common Issues

1. **Printer not receiving data**
   - Check printer network settings
   - Verify ZPL mode is enabled
   - Test with simple ZPL command

2. **Barcode not scanning**
   - Verify 10-digit card number
   - Check barcode symbology settings
   - Ensure proper quiet zones

3. **Text cut off**
   - Adjust label width (^PW command)
   - Check printer margins
   - Verify DPI settings

### Debug Mode

Test ZPL output:
1. Print to file instead of printer
2. Use Labelary.com ZPL viewer
3. Check raw ZPL syntax

## Advanced Features

### Multiple Wristband Sizes

Add new paper formats:
```xml
<record id="paperformat_wristband_pediatric" model="report.paperformat">
    <field name="name">Pediatric Wristband</field>
    <field name="page_width">19</field>  <!-- 3/4 inch -->
    <field name="page_height">178</field> <!-- 7 inch -->
</record>
```

### Dynamic Content

Add conditions in template:
```xml
<t t-if="sale.service_id.name == 'VIP Pass'">
    ^FO20,150^A0N,24,24^FDVIP ACCESS^FS
</t>
```

### Multi-language Support

Template supports translations:
```xml
<t t-if="lang == 'en_US'">
    ^FO20,95^A0N,28,28^FDValid:^FS
</t>
<t t-else="">
    ^FO20,95^A0N,28,28^FDВалидно:^FS
</t>
```

## Reports

The module provides:
- Wristband print history
- Service usage by wristband
- Failed print attempts log

## Contributing

Contributions welcome:
1. Fork repository
2. Create feature branch
3. Test with real Zebra printer
4. Submit pull request

## License

This module is licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

## Credits

### Authors
- Polimex Dev Team

### Contributors
- See [contributors](https://github.com/polimex/odoo-apps/contributors)

### Maintainer
- [Polimex](https://polimex.co)

## Links

- [ZPL Programming Guide](https://www.zebra.com/content/dam/zebra/manuals/printers/common/programming/zpl-zbi2-pm-en.pdf)
- [Labelary Online ZPL Viewer](http://labelary.com/viewer.html)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/rfid_service_zpl_labels/)

---

For more information, visit [polimex.co](https://polimex.co)