from odoo import http
from odoo.http import request
import urllib.parse


class RfidLabelPreviewController(http.Controller):
    
    @http.route('/rfid/label/preview/<int:sale_id>', type='http', auth='user', website=False)
    def preview_label(self, sale_id, **kw):
        """Render the label preview page with Labelary integration."""
        sale = request.env['rfid.service.sale'].browse(sale_id)
        
        if not sale.exists():
            return request.not_found()
        
        # Check access rights
        try:
            sale.check_access('read')
        except Exception:
            return request.not_found()
        
        # Generate ZPL content using the report action but without printing
        # We use the report's render method which includes all necessary context
        report = request.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
        
        # Use the report's rendering method with all proper context
        zpl_content, _ = report.sudo().with_context(disable_print=True)._render_qweb_text(
            report.report_name, 
            [sale.id],
            data={'disable_print': True}
        )
        
        # Ensure content is string
        if isinstance(zpl_content, bytes):
            zpl_content = zpl_content.decode('utf-8')
        
        # URL encode for Labelary
        encoded_zpl = urllib.parse.quote(zpl_content)
        
        # Labelary URL for 1" x 11" wristband at 8dpmm
        labelary_url = f"https://api.labelary.com/v1/printers/8dpmm/labels/1x11/0/{encoded_zpl}"
        
        # Render the preview template
        values = {
            'sale': sale,
            'zpl_content': zpl_content,
            'labelary_url': labelary_url,
        }
        
        return request.render('rfid_service_zpl_labels.label_preview_template', values)