# TODO Get new version from 17.0!!!
from odoo import conf, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools import groupby as groupbyelem

from odoo.osv.expression import OR, AND

from odoo.addons.web.controllers.main import HomeStaticTemplateHelpers


class ProjectCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'barcode_count' in counters:
            values['barcode_count'] = request.env['hr.rfid.card'].search_count(
                [('card_type', '=', request.env.ref('hr_rfid.hr_rfid_card_type_barcode'))]) \
                if request.env['hr.rfid.card'].check_access_rights('read', raise_exception=False) else 0
        if 'card_count' in counters:
            values['card_count'] = request.env['hr.rfid.card'].search_count([]) \
                if request.env['hr.rfid.card'].check_access_rights('read', raise_exception=False) else 0
        if 'event_count' in counters:
            values['event_count'] = request.env['hr.rfid.event.user'].search_count([]) \
                if request.env['hr.rfid.event.user'].check_access_rights('read', raise_exception=False) else 0
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
