# RFID Services ZPL Labels - CUPS Integration

This module provides seamless integration between RFID Service ZPL labels and the OCA printing framework.

## Overview

When both `rfid_service_zpl_labels` and `base_report_to_label_printer` are installed, this module automatically activates to provide CUPS-based printing instead of direct socket printing.

## Features

1. **Automatic Installation** - Installs automatically when both dependencies are present
2. **CUPS Integration** - Uses proper print queues and spooling
3. **User-based Printer Selection** - Respects each user's default label printer settings
4. **Fallback Support** - Can fall back to direct socket printing if needed
5. **CUPS Test Button** - Test CUPS printer configuration from RFID Service form

## How It Works

### Without This Module
- `rfid_service_zpl_labels` prints directly to printer via TCP socket
- No print queue management
- No user-specific printer settings

### With This Module
- Printing goes through CUPS print server
- Users can configure their own label printer
- Print jobs are queued and managed properly
- ZPL report is marked as "label" type for automatic printer selection

## Configuration

1. **Install Dependencies**
   ```bash
   # Install base modules first
   ./odoo-bin -d your_db --init=base_report_to_printer,base_report_to_label_printer
   
   # Install RFID ZPL labels
   ./odoo-bin -d your_db --init=rfid_service_zpl_labels
   
   # This module will auto-install
   ```

2. **Configure CUPS Server**
   - Settings → Technical → Printing → Servers
   - Add your CUPS server details

3. **Configure Label Printer**
   - Settings → Technical → Printing → Printers
   - Update printers from server
   - Each user sets their default label printer in preferences

## Technical Details

### Method Override

The module overrides the `print_label()` method in the wizard to use report action instead of direct socket printing:

```python
def print_label(self):
    # Create sale record
    sale_id = self._write_card()[0]
    
    # Use report action (will use label printer)
    return self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband').report_action(sale_id)
```

### Report Configuration

The ZPL report is automatically marked as a "label" report:
```xml
<field name="label">True</field>
```

This ensures the report uses the user's configured label printer instead of their default printer.

### CUPS Test Functionality

The module adds a "Test CUPS Printer" button to the RFID Service form:
- Creates a temporary test sale record
- Prints it through CUPS
- Deletes the test record
- Shows success/failure notification

### Fallback Method

If CUPS printing fails, you can call the fallback method:
```python
# From wizard instance
self.print_label_direct_fallback()
```

## Benefits

1. **Print Queue Management** - Jobs are queued and can be monitored
2. **Multi-User Support** - Each user can have their own label printer
3. **Network Resilience** - CUPS handles network interruptions
4. **Print Status** - Can check if print job succeeded
5. **Printer Sharing** - Multiple users can share one printer

## Troubleshooting

### Module Not Auto-Installing

Check that both dependencies are installed:
```python
self.env['ir.module.module'].search([
    ('name', 'in', ['rfid_service_zpl_labels', 'base_report_to_label_printer']),
    ('state', '=', 'installed')
])
```

### Printing Still Goes Direct

1. Verify this module is installed and active
2. Check that the report is marked as label type
3. Ensure user has a default label printer configured

### CUPS Connection Issues

See the base_report_to_printer documentation for CUPS troubleshooting.

## License

AGPL-3

## Author

Polimex Dev Team