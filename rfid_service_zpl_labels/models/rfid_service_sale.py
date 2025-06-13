from odoo import models, _
from odoo.exceptions import UserError
import base64
import io
import socket

import logging

_logger = logging.getLogger(__name__)


class RfidServiceSale(models.Model):
    _inherit = 'rfid.service.sale'

    def preview_label(self):
        """
        Generate and preview the ZPL label for this service sale.
        Opens a new tab with the label preview page.
        """
        self.ensure_one()
        
        # Return action to open the preview page
        return {
            'type': 'ir.actions.act_url',
            'url': f'/rfid/label/preview/{self.id}',
            'target': 'new',
        }
    
    def print_label_direct(self):
        """
        Print the label directly to the configured ZPL printer.
        This method sends the ZPL directly to the printer via socket.
        """
        self.ensure_one()
        
        # Get printer settings from company
        company = self.company_id or self.env.company
        printer_ip = company.rfid_label_printer_ip or '192.168.1.100'
        printer_port = company.rfid_label_printer_port or 9100
        
        try:
            # Generate the ZPL content using the report
            report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
            zpl_content, _format = report._render_qweb_text(report.report_name, [self.id])
            
            # Ensure content is bytes
            if isinstance(zpl_content, str):
                zpl_content = zpl_content.encode('utf-8')
            
            # Send to printer via socket
            _logger.info(f"Sending wristband ZPL for sale {self.name} to printer at {printer_ip}:{printer_port}")
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # 10 second timeout
            
            try:
                sock.connect((printer_ip, printer_port))
                sock.send(zpl_content)
                _logger.info(f"Wristband ZPL for sale {self.name} sent successfully to printer")
            finally:
                sock.close()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Label Printed'),
                    'message': _('Wristband label for %s has been sent to the printer.') % self.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except socket.timeout:
            raise UserError(_('Connection timeout: Unable to connect to printer at %s:%s\n\nPlease check printer settings in Settings → Labels → Label Printer Settings') % (printer_ip, printer_port))
        except socket.error as e:
            raise UserError(_('Network error: %s\n\nPrinter IP: %s:%s\nPlease check printer settings in Settings → Labels → Label Printer Settings') % (str(e), printer_ip, printer_port))
        except Exception as e:
            _logger.exception(f"Error printing wristband label for sale {self.name}")
            raise UserError(_('Printing error: %s') % str(e))