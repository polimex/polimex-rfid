from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class RfidServiceCups(models.Model):
    _inherit = 'rfid.service'

    def _delete_test_sale(self, sale_id):
        """Delete test sale record after report generation"""
        try:
            with self.pool.cursor() as new_cr:
                new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                test_sale = new_env['rfid.service.sale'].browse(sale_id)
                if test_sale.exists():
                    test_sale.sudo().unlink()
                    _logger.info(f"Test sale {sale_id} deleted successfully")
        except Exception as e:
            _logger.warning(f"Failed to delete test sale {sale_id}: {e}")

    def test_label_printer_cups(self):
        """
        Test CUPS label printer by generating a test sale and printing through CUPS.
        This method creates a temporary test sale record and prints it using the 
        CUPS integration with base_report_to_label_printer.
        
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
            # Create a test sale record with minimal data using sudo to bypass access rights
            test_sale = self.env['rfid.service.sale'].sudo().create({
                'service_id': self.id,
                'partner_id': self.env.user.partner_id.id,
                'company_id': self.company_id.id or self.env.company.id,
                'start_date': fields.Datetime.now(),
                'end_date': fields.Datetime.now() + timedelta(days=1),
                'card_number': f'TEST{self.id:06d}',
                'name': f'CUPS TEST - {self.name}',
            })
            
            # Important: Commit to ensure the record exists for the report
            self.env.cr.commit()
            
            # Get the report
            report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
            
            # Log for debugging
            _logger.info(f"CUPS test print initiated for service '{self.name}' with sale ID {test_sale.id}")
            
            # Use print_document_client_action for direct printing to CUPS
            try:
                result = report.print_document_client_action([test_sale.id])
                _logger.info(f"Print document result: {result}")
                
                # Mark the test sale for deletion
                test_sale.sudo().write({'name': f'[TO DELETE] {test_sale.name}'})
                
                # Return success notification
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Test label sent to printer: %s') % self.env.user.default_label_printer_id.name,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            except Exception as print_error:
                # Mark for deletion even if print fails
                test_sale.sudo().write({'name': f'[TO DELETE] {test_sale.name}'})
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