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
        
        # Generate ZPL content using the report but with sudo to avoid print triggers
        # We'll render the template directly through the template engine
        IrQweb = request.env['ir.qweb'].sudo()
        
        # Import the format_datetime function from Odoo tools
        from odoo.tools import format_datetime
        
        # Prepare the values for the template
        values = {
            'docs': sale,
            'doc_ids': [sale.id],
            'doc_model': 'rfid.service.sale',
            'user': request.env.user,
            'format_datetime': lambda dt, pattern='dd-MMM-yy HH:mm', dt_format='short': 
                format_datetime(request.env, dt, dt_format=pattern) if dt else '',
        }
        
        # Render the template
        zpl_content = IrQweb._render('rfid_service_zpl_labels.wristband_template_view', values)
        
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