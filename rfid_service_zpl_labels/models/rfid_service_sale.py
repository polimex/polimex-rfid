from odoo import models, _
from odoo.exceptions import UserError
import base64
import io
import socket

import logging

_logger = logging.getLogger(__name__)


class RfidServiceSale(models.Model):
    _name = 'rfid.service.sale'
    _inherit = 'rfid.service.sale'
    
    def _generate_zpl_content(self):
        """
        Generate ZPL content for this service sale using the configured report template.
        This centralizes ZPL generation for all print/preview methods.
        
        :return: tuple (zpl_content, format_type)
        """
        self.ensure_one()
        
        # Get the report from the service configuration
        if self.service_id and self.service_id.label_template_id:
            report = self.service_id.label_template_id
        else:
            # Default to QR code version
            report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
        
        # Generate ZPL content
        zpl_content, format_type = report._render_qweb_text(report.report_name, [self.id])
        
        # Ensure content is string
        if isinstance(zpl_content, bytes):
            zpl_content = zpl_content.decode('utf-8')
            
        return zpl_content, format_type
    
    def _send_zpl_to_printer(self, zpl_content, printer_ip=None, printer_port=None):
        """
        Send ZPL content to printer via socket.
        Centralizes socket printing logic to avoid duplication.
        
        :param zpl_content: ZPL content to send
        :param printer_ip: Override printer IP (optional)
        :param printer_port: Override printer port (optional)
        :return: dict with notification action
        """
        # Get printer settings
        company = self.company_id or self.env.company
        printer_ip = printer_ip or company.rfid_label_printer_ip or '192.168.1.100'
        printer_port = printer_port or company.rfid_label_printer_port or 9100
        
        # Ensure content is bytes
        if isinstance(zpl_content, str):
            zpl_content = zpl_content.encode('utf-8')
        
        # Send to printer
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        try:
            _logger.info(f"Sending ZPL to printer at {printer_ip}:{printer_port}")
            sock.connect((printer_ip, printer_port))
            sock.send(zpl_content)
            _logger.info("ZPL sent successfully")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Label Printed'),
                    'message': _('Wristband label sent to printer successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except socket.timeout:
            raise UserError(_('Connection timeout: Unable to connect to printer at %s:%s\n\nPlease check printer settings.') % (printer_ip, printer_port))
        except socket.error as e:
            raise UserError(_('Network error: %s\n\nPrinter: %s:%s') % (str(e), printer_ip, printer_port))
        finally:
            sock.close()

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
        Uses centralized ZPL generation and socket printing.
        """
        self.ensure_one()
        
        try:
            # Generate ZPL content using centralized method
            zpl_content, _ = self._generate_zpl_content()
            
            # Send to printer using centralized method
            return self._send_zpl_to_printer(zpl_content)
            
        except Exception as e:
            _logger.exception(f"Error printing wristband label for sale {self.id}")
            if isinstance(e, UserError):
                raise
            raise UserError(_('Printing error: %s') % str(e))
    
