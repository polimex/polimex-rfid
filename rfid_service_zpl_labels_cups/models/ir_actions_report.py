from odoo import models, api


class IrActionsReport(models.Model):
    _name = "ir.actions.report"
    _inherit = "ir.actions.report"
    
    def _get_user_default_print_behaviour(self):
        """Override to use label printer when report is marked as label"""
        result = super()._get_user_default_print_behaviour()

        # If this is a label report and user has a default label printer, use it
        if self.label and self.env.user.default_label_printer_id:
            result['printer'] = self.env.user.default_label_printer_id

        return result

    def _get_report_default_print_behaviour(self):
        """
        Override to prevent report-level printer from overriding user preferences for labels.

        For label reports, user preferences (default_label_printer_id) should always take
        precedence over report-level printer settings (printing_printer_id).
        This ensures each user can print to their own configured label printer.
        """
        result = super()._get_report_default_print_behaviour()

        # For label reports, ignore report-level printer configuration
        # and rely only on user's default_label_printer_id
        if self.label and 'printer' in result:
            result.pop('printer')

        return result