from random import randint

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import socket

import logging

_logger = logging.getLogger(__name__)


class BaseRFIDService(models.Model):
    _name = 'rfid.service'
    _inherit = 'rfid.service'
    
    label_template_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Label Template",
        domain=[("model", "=", "rfid.service.sale")],
        help="Select the label template to use for printing labels/wristbands.",
        default=lambda self: self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband', raise_if_not_found=False),
    )

    def test_label_printer_connection(self):
        """
        Test the connection to the configured label printer.
        Uses the service's configured label template to generate test ZPL.
        
        This method can be called from rfid.service records to test
        if the label printer is properly configured and accessible.
        
        :return: Notification action with connection status
        """
        self.ensure_one()
        
        # Get printer settings from service's company or current company
        company = self.company_id or self.env.company
        printer_ip = company.rfid_label_printer_ip or '192.168.1.100'
        printer_port = company.rfid_label_printer_port or 9100
        
        # Use the service's configured template or default
        if self.label_template_id:
            report = self.label_template_id
        else:
            report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
        
        # Generate ZPL using the template with empty data (will use failsafe values)
        zpl_content, _format = report._render_qweb_text(report.report_name, [])
        
        # Ensure content is bytes
        if isinstance(zpl_content, str):
            zpl_content = zpl_content.encode('utf-8')
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            _logger.info(f"Testing printer connection for service '{self.name}' at {printer_ip}:{printer_port}")
            
            sock.connect((printer_ip, printer_port))
            sock.send(zpl_content)
            sock.close()
            
            _logger.info(f"Test label sent successfully for service '{self.name}'")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Printer Test Successful'),
                    'message': _('Test label sent successfully to %s:%s\nUsing template: %s', printer_ip, printer_port, report.name),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except socket.timeout:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Timeout'),
                    'message': _('Could not connect to printer at %s:%s - Connection timed out after 5 seconds', printer_ip, printer_port),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        except socket.error as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Failed'),
                    'message': _('Network error: %s\nPlease check printer IP and port in system parameters.', str(e)),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        except Exception as e:
            _logger.exception(f"Unexpected error testing printer for service '{self.name}'")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test Failed'),
                    'message': _('Unexpected error: %s', str(e)),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def preview_label(self):
        """
        Preview the label template configured for this service.
        Opens a new tab with the label preview without any sale data (uses failsafe values).
        """
        self.ensure_one()
        
        # Return action to open the preview page for the service
        return {
            'type': 'ir.actions.act_url',
            'url': f'/rfid/label/preview/service/{self.id}',
            'target': 'new',
        }