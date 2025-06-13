from odoo import models, _, fields
from odoo.exceptions import UserError
import socket
from datetime import datetime

import logging

_logger = logging.getLogger(__name__)


class RfidServiceBaseSaleWiz(models.TransientModel):
    _inherit = 'rfid.service.sale.wiz'


    def print_label(self):
        """Print label using the configured method (socket or CUPS if overridden)"""
        # Call the direct print method
        return self.print_label_direct()

    def print_label_direct(self):
        """
        Print ZPL wristband label directly to printer.
        Creates the sale record and uses centralized printing methods.
        """
        # Get printer settings for connection test
        company = self.env.company
        printer_ip = company.rfid_label_printer_ip or '192.168.1.100'
        printer_port = company.rfid_label_printer_port or 9100
        
        # Test printer connection BEFORE creating the sale
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(5)  # Quick test timeout
            test_sock.connect((printer_ip, printer_port))
            test_sock.close()
            _logger.info("Printer connection test successful")
        except (socket.timeout, TimeoutError):
            raise UserError(_('Connection timeout: Unable to connect to printer at %s:%s\n\nPlease check printer settings.') % (printer_ip, printer_port))
        except socket.error as e:
            raise UserError(_('Network error: %s\n\nPrinter: %s:%s') % (str(e), printer_ip, printer_port))
        
        # Create the sale record after confirming printer is available
        sale_record, partner_id, access_group_contact_rel, card_id = self._write_card()
        
        try:
            # Use the sale record's centralized methods
            zpl_content, _ = sale_record._generate_zpl_content()
            sale_record._send_zpl_to_printer(zpl_content)
            
            # Close the wizard
            return {'type': 'ir.actions.act_window_close'}
            
        except Exception as e:
            _logger.exception("Error printing wristband label")
            if isinstance(e, UserError):
                raise
            raise UserError(_('Printing error: %s') % str(e))


    def test_printer_connection(self):
        """
        Test the connection to the configured label printer.
        Sends a simple ZPL test pattern to verify connectivity.
        
        :return: Notification with connection status
        """
        # Get printer settings from company
        company = self.env.company
        printer_ip = company.rfid_label_printer_ip or '192.168.1.100'
        printer_port = company.rfid_label_printer_port or 9100
        
        # Test ZPL with column layout matching production design
        test_zpl = f"""^XA^CI28
^PW203 ^LL2233 ^LH0,0

; COLUMN 1: Now empty

; COLUMN 2: Company, Test info, Printer info in 3 rows with more spacing
^FO110,500
^A0R,44,44^FD{company.name[:25]}^FS
^FO70,500
^A0R,40,40^FDTEST PRINT^FS
^FO30,500
^A0R,48,48^FD{printer_ip}:{printer_port}^FS

; COLUMN 3: QR Code properly centered
^FO35,1250
^BQR,2,8
^FDMA,1234567890^FS

; COLUMN 4: Timestamp
^FO100,1800
^A0R,36,36^FD{fields.Datetime.context_timestamp(self, datetime.now()).strftime('%d-%b-%y %H:%M').upper()}^FS

^XZ""".encode('utf-8')
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((printer_ip, printer_port))
            sock.send(test_zpl)
            sock.close()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful'),
                    'message': _('Test label sent to printer at %s:%s', printer_ip, printer_port),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Failed'),
                    'message': _('Could not connect to printer: %s', str(e)),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    

