from odoo import conf, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ProjectCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'service_count' in counters:
            values['service_count'] = request.env['rfid.service.sale'].sudo().search_count(
                [('partner_id', '=', request.env.user.partner_id.id)])
        return values

    @http.route(['/my/rfid_services'], type='http', auth="public", website=True, sitemap=False)
    def portal_my_services(self, access_token=None, p=1, **kw):
        user_id = request.env.user
        if not user_id:
            return request.redirect('/my')
        user_services = request.env['rfid.service.sale'].sudo().search(
            [('partner_id', '=', user_id.partner_id.id)])
        values = {
            'page_name': 'rfidservices',
            'services': user_services,
        }
        return request.render("rfid_service_portal.portal_rfid_service_sale_table", values)

    @http.route(['/my/rfid_service<int:card_id>'], type='http', auth="public", website=True, sitemap=False)
    def portal_my_service(self, card_id, access_token=None, **kw):
        try:
            card_sudo = self._document_check_access('hr.rfid.card', card_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._card_get_page_view_values(card_sudo, access_token, **kw)
        return request.render("hr_rfid_portal.portal_my_barcode", values)


