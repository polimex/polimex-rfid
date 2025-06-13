from odoo import models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RfidServiceSaleCups(models.Model):
    _inherit = 'rfid.service.sale'

    def print_label_direct(self):
        """
        Override direct socket printing to use CUPS print queue.
        This method is called when clicking "Print Label" button on service sale form.
        """
        self.ensure_one()
        
        # Check if user has label printer configured
        if not self.env.user.default_label_printer_id:
            raise UserError(_('No label printer configured. Please configure a label printer in your user preferences.'))
        
        if self.env.user.printing_action != 'server':
            raise UserError(_('Your printing action is not set to "Send to Printer". Please go to your user preferences and set the printing action to "Send to Printer".'))
        
        try:
            # Get the report from service configuration or default
            if self.service_id and self.service_id.label_template_id:
                report = self.service_id.label_template_id
            else:
                report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
            
            # Use print_document_client_action for CUPS printing
            result = report.print_document_client_action([self.id])
            _logger.info(f"Wristband for sale {self.name} sent to CUPS printer")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Label Sent to Printer'),
                    'message': _('Wristband label sent to %s successfully.') % self.env.user.default_label_printer_id.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.exception(f"Error printing wristband label through CUPS for sale {self.id}")
            raise UserError(_('CUPS printing error: %s') % str(e))
    
    def print_label_direct_socket(self):
        """
        Fallback method for direct socket printing.
        Uses the original implementation from parent module.
        Can be called if CUPS printing fails or for troubleshooting.
        """
        # Call the original parent implementation
        return super(RfidServiceSaleCups, self).print_label_direct()