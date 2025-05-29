# RFID Services ZPL Labels

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.0.1.0-green.svg)](https://apps.odoo.com)

ZPL (Zebra Programming Language) wristband printing extension for RFID Services.

## 🎯 Overview

RFID Services ZPL Labels extends the RFID service system with professional wristband printing capabilities. It generates ZPL-formatted output for Zebra label printers, enabling high-quality wristband printing for visitors, patients, event attendees, and temporary access cards.

## ✨ Key Features

### Wristband Generation
- **ZPL II Format**: Native Zebra Programming Language output
- **Barcode Integration**: Automatic CODE-128 barcode generation
- **Custom Layouts**: Configurable wristband templates
- **Multi-format Support**: Various wristband sizes (1×11 inch standard)

### Print Capabilities
- **Direct ZPL Output**: Raw ZPL code for Zebra printers
- **Company Branding**: Logo and company name on wristbands
- **Service Information**: Service type and validity dates
- **Visitor Details**: Name and access information

### Integration Features
- **Service Integration**: Seamless with rfid_service_base
- **Batch Printing**: Print multiple wristbands at once
- **Email Support**: Send wristband data electronically
- **Portal Compatible**: Works with service portal

## 📋 Requirements

- Odoo 18.0+
- rfid_service_base module
- Zebra ZPL-compatible printer
- Python 3.8+

### Printing Options
- **Odoo IoT Box**: For direct network printing
- **File Export**: Save ZPL and send to printer
- **Third-party Modules**: OCA printer_zpl2 or similar
- **CUPS Integration**: Direct printing on Linux

## 🛠️ Installation

1. Install rfid_service_base module first

2. Install this module:
```bash
./odoo-bin -d your_database -i rfid_service_zpl_labels
```

3. Configure your Zebra printer connection method

## 🔧 Configuration

### Printer Setup

1. **Zebra Printer Configuration**
   - Set printer to accept ZPL commands
   - Configure network settings if using network printer
   - Test with sample ZPL code

2. **Odoo Configuration**
   - No special configuration needed in module
   - Report outputs raw ZPL text
   - Configure printing method separately

### Wristband Template

The module includes a standard wristband template:
- **Size**: 1×11 inches (25×279mm)
- **DPI**: 203 dpi standard
- **Format**: Portrait orientation
- **Content**: Company, service, visitor, dates, barcode

### Company Logo Setup

To add your company logo to wristbands:

1. Convert logo to ZPL GRF format
2. Upload to printer memory as `COMPLOGO.GRF`
3. Logo will appear on all wristbands

## 📖 Usage

### Printing Wristbands

1. **From Service Sale**
   - Complete service sale
   - Click "Print Wristband"
   - ZPL code is generated

2. **Batch Printing**
   - Select multiple sales
   - Action → Print Wristbands
   - One ZPL block per wristband

3. **Sending ZPL to Printer**

#### Via File:
```bash
# Save ZPL output to file
# Send to printer using lpr (Linux)
lpr -P zebra_printer wristband.zpl

# Or copy to printer share (Windows)
copy wristband.zpl \\computer\zebra_printer
```

#### Via Network:
```python
# Send directly to network printer
import socket
printer_ip = "192.168.1.100"
printer_port = 9100

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((printer_ip, printer_port))
sock.send(zpl_data.encode())
sock.close()
```

## 🏷️ ZPL Format

### Sample Output
```zpl
^XA^CI28
^PW812 ^LL203 ^LH0,0
^FO20,20
^A0N,36,36^FDPolimex Company^FS
^FO20,60
^A0N,28,28^FDVisitor Pass^FS
^FO160,60
^A0N,28,28^FDJohn Doe^FS
^FO20,95
^A0N,28,28^FDValid:^FS
^FO160,95
^A0N,28,28^FD01.01.2024 - 31.01.2024^FS
^FO20,130^GB770,2,2^FS
^FO20,140^BY2,2,80
^BCN,80,Y,N,N
^FD0123456789^FS
^FO680,10^XGR:COMPLOGO.GRF,1,1^FS
^XZ
```

### Template Customization

Edit the QWeb template in `reports/report_wristband.xml`:
- Adjust positions with `^FO` commands
- Change fonts with `^A` commands
- Modify barcode with `^BC` parameters

## 🔌 API Reference

### Report Generation
```python
# Generate wristband for a service sale
sale = self.env['rfid.service.sale'].browse(sale_id)
report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
zpl_data = report._render_qweb_text(sale.ids)
```

### Custom Fields
```python
# Add custom fields to wristband
class RfidServiceSale(models.Model):
    _inherit = 'rfid.service.sale'
    
    wristband_color = fields.Selection([
        ('red', 'Red'),
        ('blue', 'Blue'),
        ('green', 'Green'),
    ])
```

## 🐛 Troubleshooting

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

## ⚙️ Advanced Features

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
^FO20,95
^A0N,28,28^FD<t t-esc="'Valid:' if lang == 'en_US' else 'Валидно:'"/>^FS
```

## 📊 Reports

The module provides:
- Wristband print history
- Service usage by wristband
- Failed print attempts log

## 🤝 Contributing

Contributions welcome:
1. Fork repository
2. Create feature branch
3. Test with real Zebra printer
4. Submit pull request

## 📄 License

This module is licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

## 👥 Credits

### Authors
- Polimex Dev Team

### Contributors
- See [contributors](https://github.com/polimex/odoo-apps/contributors)

### Maintainer
- [Polimex](https://polimex.co)

## 🌐 Links

- [ZPL Programming Guide](https://www.zebra.com/content/dam/zebra/manuals/printers/common/programming/zpl-zbi2-pm-en.pdf)
- [Labelary Online ZPL Viewer](http://labelary.com/viewer.html)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/rfid_service_zpl_labels/)

---

For more information, visit [polimex.co](https://polimex.co)