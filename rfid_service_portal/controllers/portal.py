from odoo import conf, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class ProjectCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'service_count' in counters:
            values['service_count'] = request.env['rfid.service.sale'].search_count([]) \
                if request.env['rfid.service.sale'].check_access_rights('read', raise_exception=False) else 0
        return values

    def _card_get_page_view_values(self, card, access_token, **kwargs):
        try:
            card_accessible = bool(card and self._document_check_access('hr.rfid.card', card.id))
        except (AccessError, MissingError):
            card_accessible = False
        values = {
            'page_name': _('Web card for %s' % card.get_owner().name),
            'card': card,
            'owner': card.get_owner(),
            'user': request.env.user,
            'card_accessible': card_accessible,
            'company': request.env.company,
        }
        return values

    @http.route(['/my/webcard/<int:card_id>'], type='http', auth="public", website=True)
    def portal_my_webcard(self, card_id, access_token=None, **kw):
        try:
            card_sudo = self._document_check_access('hr.rfid.card', card_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._card_get_page_view_values(card_sudo, access_token, **kw)
        return request.render("hr_rfid_portal.portal_my_barcode", values)
