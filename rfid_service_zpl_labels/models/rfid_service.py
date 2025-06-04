from random import randint

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import socket

import logging

_logger = logging.getLogger(__name__)


class BaseRFIDService(models.Model):
    _inherit = 'rfid.service'

    label_template_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Label Template",
        domain=[("model", "=", "rfid.service.sale")],
        required=True,
        help="Select the label template to use for printing labels/wristbands. ",
    )
    
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'label_template_id' in fields_list:
            try:
                defaults['label_template_id'] = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband').id
            except ValueError:
                pass
        return defaults

    def test_label_printer_connection(self):
        """
        Test the connection to the configured label printer.
        Sends a simple ZPL test pattern to verify connectivity.
        
        This method can be called from rfid.service records to test
        if the label printer is properly configured and accessible.
        
        :return: Notification action with connection status
        """
        self.ensure_one()
        
        # Get printer settings from service's company or current company
        company = self.company_id or self.env.company
        printer_ip = company.rfid_label_printer_ip or '192.168.1.100'
        printer_port = company.rfid_label_printer_port or 9100
        
        # Simple test ZPL that prints service name and test message
        test_zpl = f"""^XA
^FO50,50^ADN,36,20^FDPRINTER TEST - {self.name}^FS
^FO50,100^ADN,24,16^FDService: {self.name}^FS
^FO50,150^BY3^BCN,100,Y,N,N^FD{self.id:06d}^FS
^FO50,270^ADN,24,16^FDPrinter IP: {printer_ip}:{printer_port}^FS
^XZ""".encode('utf-8')
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            _logger.info(f"Testing printer connection for service '{self.name}' at {printer_ip}:{printer_port}")
            
            sock.connect((printer_ip, printer_port))
            sock.send(test_zpl)
            sock.close()
            
            _logger.info(f"Test label sent successfully for service '{self.name}'")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Printer Test Successful'),
                    'message': _('Test label sent successfully to %s:%s\nA test label with service "%s" should print now.', printer_ip, printer_port, self.name),
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

