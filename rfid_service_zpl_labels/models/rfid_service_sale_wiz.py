from odoo import models, _
from odoo.exceptions import UserError
import socket

import logging

_logger = logging.getLogger(__name__)


class RfidServiceBaseSaleWiz(models.TransientModel):
    _inherit = 'rfid.service.sale.wiz'


    def print_label(self):
        """Print label using direct socket printing"""
        # Call the direct print method
        return self.print_label_direct()

    def print_label_direct(self):
        """Print ZPL wristband label directly to printer and close wizard"""
        # Get printer settings from company FIRST
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
            raise UserError('Connection timeout: Unable to connect to printer at %s:%s\n\nCompany: %s\nPlease check printer settings in Settings - Labels - Label Printer Settings' % (
                printer_ip, printer_port, company.name))
        except socket.error as e:
            raise UserError('Network error: %s\n\nPrinter IP: %s:%s\nCompany: %s\nPlease check printer settings in Settings → Labels → Label Printer Settings' % (
                str(e), printer_ip, printer_port, company.name))
        
        # NOW create the sale record after confirming printer is available
        sale_id, partner_id, access_group_contact_rel, card_id = self._write_card()
        
        try:
            # Generate the ZPL content using the report
            report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
            zpl_content, _ = report._render_qweb_text(report.report_name, [sale_id.id])
            
            # Ensure content is bytes
            if isinstance(zpl_content, str):
                zpl_content = zpl_content.encode('utf-8')
            
            # Send to printer via socket
            _logger.info(f"Sending wristband ZPL to printer at {printer_ip}:{printer_port}")
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # 10 second timeout
            
            try:
                sock.connect((printer_ip, printer_port))
                sock.send(zpl_content)
                _logger.info("Wristband ZPL sent successfully to printer")
            finally:
                sock.close()
            
            # Close the wizard
            return {'type': 'ir.actions.act_window_close'}
            
        except (socket.timeout, TimeoutError):
            # raise UserError(_('Connection timeout: Unable to connect to printer at %s:%s\n\nCompany: %s\nPlease check printer settings in Settings → Labels → Label Printer Settings',
            #     printer_ip, printer_port, company.name))
            raise UserError('Connection timeout: Unable to connect to printer at %s:%s\n\nCompany: %s\nPlease check printer settings in Settings - Labels - Label Printer Settings' % (
                printer_ip, printer_port, company.name))
        except socket.error as e:
            raise UserError('Network error: %s\n\nPrinter IP: %s:%s\nCompany: %s\nPlease check printer settings in Settings → Labels → Label Printer Settings' % (
                str(e), printer_ip, printer_port, company.name))
        except Exception as e:
            _logger.exception("Error printing wristband label directly")
            raise UserError('Printing error: %s' % str(e))


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
        
        # Simple test ZPL that prints "TEST" and a small barcode
        test_zpl = b"""^XA
^FO50,50^ADN,36,20^FDPRINTER TEST^FS
^FO50,150^BY3^BCN,100,Y,N,N^FD123456^FS
^XZ"""
        
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
    

