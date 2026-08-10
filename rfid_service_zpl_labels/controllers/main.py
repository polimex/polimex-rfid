from odoo import http
from odoo.http import request
import urllib.parse


class RfidLabelPreviewController(http.Controller):
    
    @http.route('/rfid/label/preview/<int:sale_id>', type='http', auth='user', website=False)
    def preview_label(self, sale_id, **kw):
        """Render the label preview page with Labelary integration."""
        sale = request.env['rfid.service.sale'].browse(sale_id)
        
        if not sale.exists():
            raise request.not_found()
        
        # Check access rights
        try:
            sale.check_access('read')
        except Exception:
            raise request.not_found()
        
        # Generate ZPL content using the sale's centralized method
        # This ensures consistency across all methods
        zpl_content, _ = sale._generate_zpl_content()
        
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
    
    @http.route('/rfid/label/preview/service/<int:service_id>', type='http', auth='user', website=False)
    def preview_service_label(self, service_id, **kw):
        """Render the label preview page for a service without sale data."""
        service = request.env['rfid.service'].browse(service_id)
        
        if not service.exists():
            raise request.not_found()
        
        # Check access rights
        try:
            service.check_access('read')
        except Exception:
            raise request.not_found()
        
        # Get the service's configured template or default
        if service.label_template_id:
            report = service.label_template_id
        else:
            report = request.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
        
        # Generate ZPL using the template with empty data (will use failsafe values)
        zpl_content, _format = report._render_qweb_text(report.report_name, [])
        
        # Ensure content is string
        if isinstance(zpl_content, bytes):
            zpl_content = zpl_content.decode('utf-8')
        
        # URL encode for Labelary
        encoded_zpl = urllib.parse.quote(zpl_content)
        
        # Labelary URL for 1" x 11" wristband at 8dpmm
        labelary_url = f"https://api.labelary.com/v1/printers/8dpmm/labels/1x11/0/{encoded_zpl}"
        
        # Render the preview template with service info
        values = {
            'service': service,
            'sale': None,  # No sale data for service preview
            'zpl_content': zpl_content,
            'labelary_url': labelary_url,
        }
        
        return request.render('rfid_service_zpl_labels.label_preview_template', values)