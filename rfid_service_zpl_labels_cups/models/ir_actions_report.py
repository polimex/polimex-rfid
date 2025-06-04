from odoo import models, api


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"
    
    def _get_user_default_print_behaviour(self):
        """Override to use label printer when report is marked as label"""
        result = super()._get_user_default_print_behaviour()
        
        # If this is a label report and user has a default label printer, use it
        if self.label and self.env.user.default_label_printer_id:
            result['printer'] = self.env.user.default_label_printer_id
            
        return result