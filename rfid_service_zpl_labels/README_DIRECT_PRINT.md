# Direct Print Functionality for RFID Service ZPL Labels

This document describes the direct printing capabilities added to the `rfid_service_zpl_labels` module.

## Overview

The module now includes direct printing methods:

1. **Direct Network Print** - Sends ZPL directly to network printer (DEFAULT)
2. **CUPS Integration** - When `rfid_service_zpl_labels_cups` module is installed

### ⚠️ Multi-User Environment Warning

**IMPORTANT**: If multiple users will print from different workstations simultaneously, you MUST install the `rfid_service_zpl_labels_cups` module to:
- Properly manage print queue
- Prevent print job conflicts
- Allow user-specific printer settings
- Track print job status

Without CUPS integration, direct socket printing may cause conflicts when multiple users print at the same time.

## New Methods

### In `rfid.service` Model

#### `test_label_printer_connection()`

Tests connectivity to the configured label printer from any RFID Service record.

**Features:**
- Can be called from form view via button
- Can be called from list view via server action
- Prints service-specific test label
- Shows service name and ID on test label
- Displays printer configuration on label

**Access:**
- Form View: "Test Label Printer" button in header (admin group only)
- List View: Action menu → Test Label Printer
- Programmatic: `service.test_label_printer_connection()`

### In `rfid.service.sale.wiz` Model

#### 1. `print_label_direct()`

Sends ZPL commands directly to a network-enabled Zebra printer via TCP socket.

**Features:**
- Direct socket connection to printer
- Configurable IP address and port
- Error handling with user-friendly messages
- Success notification
- Automatic wizard closure after printing

**Configuration:**
```
Settings → Technical → Parameters → System Parameters
- rfid.label.printer.ip (default: 192.168.1.100)
- rfid.label.printer.port (default: 9100)
```

**Usage:**
```python
# In your custom code
wizard = self.env['rfid.service.sale.wiz'].create({...})
wizard.print_label_direct()
```

### 2. `test_printer_connection()`

Tests connectivity to the configured printer by sending a test label.

**Features:**
- Quick connectivity test
- Sends minimal test pattern
- Shows success/failure notification
- 5-second timeout for fast response

**Test Pattern:**
```
PRINTER TEST
[123456] (barcode)
```

## System Parameters

All printer settings are stored as system parameters for easy configuration:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rfid.label.printer.ip` | 192.168.1.100 | IP address of Zebra printer |
| `rfid.label.printer.port` | 9100 | TCP port (9100 is standard for RAW) |

## Error Handling

The module provides comprehensive error handling:

1. **Connection Timeout** - Clear message if printer doesn't respond
2. **Network Errors** - Detailed socket error information
3. **Invalid Parameters** - Validation of IP and port settings
4. **Printing Errors** - Full exception logging and user notification

## Implementation Notes

### Socket Communication

The direct print method uses Python's socket library:
```python
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10)  # 10 second timeout
sock.connect((printer_ip, printer_port))
sock.send(zpl_content)
sock.close()
```

### Character Encoding

- ZPL content is encoded as UTF-8 before sending
- The report template uses `^CI28` for UTF-8 support
- Special characters are properly handled

### Security Considerations

- System parameters require admin access to modify
- Printer IP/port validation prevents injection
- Socket connections are properly closed
- Timeout prevents hanging connections

## Troubleshooting

### Common Issues

1. **"Connection timeout" error**
   - Check printer IP address is correct
   - Verify printer is powered on and connected to network
   - Test with: `telnet PRINTER_IP 9100`

2. **"Network error: Connection refused"**
   - Verify port 9100 is correct for your printer
   - Check firewall rules allow connection
   - Ensure printer accepts RAW socket connections

3. **Labels print but content is wrong**
   - Verify printer is in ZPL mode (not EPL)
   - Check printer DPI matches template (203 DPI)
   - Test ZPL at labelary.com/viewer.html

### Debug Mode

Enable debug logging to see detailed information:
```python
import logging
logging.getLogger('rfid_service_zpl_labels').setLevel(logging.DEBUG)
```

## Future Enhancements

The following features are prepared but not currently active:

1. **Multiple printer support** - Different printers for different label types
2. **Print queue management** - Batch printing capabilities
3. **Printer status monitoring** - Check printer status before sending
4. **Alternative protocols** - Support for LPR, IPP protocols
5. **Label preview** - Generate PNG preview before printing

## Integration with UI

While the backend methods are ready, UI buttons can be added later:

```xml
<!-- Example button configuration (not included) -->
<button name="print_label_direct" 
        string="Direct Print" 
        type="object" 
        class="btn-primary"
        icon="fa-print"/>

<button name="test_printer_connection" 
        string="Test Printer" 
        type="object" 
        class="btn-secondary"
        icon="fa-plug"/>
```

## License

This functionality is part of the `rfid_service_zpl_labels` module and is licensed under AGPL-3.

---

*Author: Polimex Dev Team*  
*Version: 18.0.0.1.0*