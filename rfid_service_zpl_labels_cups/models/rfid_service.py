from odoo import models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RfidServiceCups(models.Model):
    _name = 'rfid.service'
    _inherit = 'rfid.service'

    def test_label_printer_connection(self):
        """
        Override the direct socket test to use CUPS instead.
        This replaces the socket-based test with CUPS-based test.
        """
        return self.test_label_printer_cups()
    
    def test_label_printer_connection_socket(self):
        """
        Fallback method for direct socket testing.
        Uses the original implementation from parent module.
        """
        return super(RfidServiceCups, self).test_label_printer_connection()

    def test_label_printer_cups(self):
        """
        Test CUPS label printer by printing a test label with failsafe values.
        Uses the report template directly without creating test records.
        
        :return: Notification with test result
        """
        self.ensure_one()
        
        # Check if user has a label printer configured
        if not self.env.user.default_label_printer_id:
            raise UserError(_('No label printer configured for your user. Please configure a label printer in your user preferences.'))
        
        # Check if user's printing action is set to server
        if self.env.user.printing_action != 'server':
            raise UserError(_('Your printing action is not set to "Send to Printer". Please go to your user preferences and set the printing action to "Send to Printer".'))
        
        try:
            # Get the report from service configuration or use default
            if self.label_template_id:
                report = self.label_template_id
            else:
                report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
            
            # Log for debugging
            _logger.info(f"CUPS test print initiated for service '{self.name}'")
            
            # Use print_document_client_action with empty recordset
            # The report template has failsafe values and will print test data
            try:
                result = report.print_document_client_action([])
                _logger.info(f"Print document result: {result}")
                
                # Return success notification
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Test label sent to printer: %s\nUsing template: %s') % (
                            self.env.user.default_label_printer_id.name,
                            report.name
                        ),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            except Exception as print_error:
                raise UserError(_('Error sending to printer: %s') % str(print_error))
            
        except Exception as e:
            _logger.exception(f"Error during CUPS test print for service '{self.name}'")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('CUPS Test Failed'),
                    'message': _('Error: %s\nMake sure base_report_to_label_printer is properly configured.') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }