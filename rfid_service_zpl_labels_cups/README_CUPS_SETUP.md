# RFID Service ZPL Labels - CUPS Setup Guide

## Prerequisites

1. Install and configure CUPS printer on your system
2. Install the `base_report_to_label_printer` module in Odoo
3. Install this module (`rfid_service_zpl_labels_cups`)

## User Configuration

To enable CUPS printing for wristband labels, each user must configure their printing preferences:

### 1. Set Default Label Printer

1. Go to **Settings → Users & Companies → Users**
2. Open your user record
3. Go to the **Preferences** tab
4. In the **Printing** section, set **Default Label Printer** to your CUPS label printer

### 2. Set Printing Action

1. In the same **Printing** section
2. Set **Printing Action** to **"Send to Printer"** (not "Open a PDF" or "Open in Browser")

### 3. Test the Configuration

1. Go to any RFID service record
2. Click **"Test CUPS Printer"** button in the form view
3. The test label should be sent directly to your configured label printer

## Troubleshooting

### Error: "Your printing action is not set to 'Send to Printer'"
- Go to your user preferences
- Change **Printing Action** from "Open a PDF" to "Send to Printer"

### Error: "No label printer configured for your user"
- Go to your user preferences
- Select a printer in the **Default Label Printer** field

### Label downloads instead of printing
- Ensure your **Printing Action** is set to "Send to Printer"
- Check that the printer is online and accessible
- Check CUPS logs for any errors

### Printer not appearing in the list
- Go to **Settings → Technical → Printing → Update Printers**
- Ensure CUPS is running and the printer is configured
- Check that the Odoo user has permissions to access CUPS

## Technical Details

This module integrates with OCA's `base_report_to_label_printer` module to:
- Use the user's configured label printer for wristband reports
- Send ZPL data directly to CUPS instead of browser download
- Support print queue management and status monitoring

The module automatically detects when a report is marked as a label (`label=True`) and uses the user's default label printer instead of the regular printer.