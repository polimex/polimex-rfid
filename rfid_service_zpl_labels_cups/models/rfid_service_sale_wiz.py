from odoo import models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RfidServiceSaleWizCups(models.TransientModel):
    _inherit = 'rfid.service.sale.wiz'

    def print_label(self):
        """
        Override to force CUPS printing directly.
        This ensures consistent behavior with the test button.
        """
        # Check if user has label printer configured
        if not self.env.user.default_label_printer_id:
            raise UserError(_('No label printer configured. Please configure a label printer in your user preferences.'))
        
        if self.env.user.printing_action != 'server':
            raise UserError(_('Your printing action is not set to "Send to Printer". Please go to your user preferences and set the printing action to "Send to Printer".'))
        
        # First write the card to create the sale record
        sale_record, partner_id, access_group_contact_rel, card_id = self._write_card()
        sale_id = sale_record.id
        
        # Get the report
        report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
        
        # Use print_document_client_action for direct CUPS printing (same as test button)
        try:
            result = report.print_document_client_action([sale_id])
            _logger.info(f"Wristband for sale ID {sale_id} sent to CUPS printer")
            
            # Return a notification instead of closing the wizard
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Wristband sent to printer: %s') % self.env.user.default_label_printer_id.name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error sending wristband to CUPS: {str(e)}")
            raise UserError(_('Error sending to printer: %s') % str(e))

    def print_label_direct_fallback(self):
        """
        Fallback method that uses the original direct socket printing.
        Can be called if CUPS printing fails or is not available.
        """
        # Call the original implementation from parent module
        return super().print_label_direct()