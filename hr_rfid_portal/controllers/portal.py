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
            values['barcode_count'] = request.env['hr.rfid.card'].sudo().search_count([
                ('card_type', '=', request.env.ref('hr_rfid.hr_rfid_card_type_barcode').id),
                ('contact_id', '=', request.env.user.partner_id.id)
            ])
        if 'card_count' in counters:
            values['card_count'] = request.env['hr.rfid.card'].sudo().search_count([
                ('card_type', '!=', request.env.ref('hr_rfid.hr_rfid_card_type_barcode').id),
                ('contact_id', '=', request.env.user.partner_id.id)
            ])
        if 'event_count' in counters:
            values['event_count'] = request.env['hr.rfid.event.user'].sudo().search_count([
                ('contact_id', '=', request.env.user.partner_id.id)
            ])
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

    @http.route(['/my/webcard'], type='http', auth="user", website=True)
    def portal_my_webcards(self, access_token=None, **kw):
        values = self._prepare_portal_layout_values()
        WebCards = request.env['hr.rfid.card'].sudo()
        domain = [
            ('contact_id', '=', request.env.user.partner_id.id),
            ('card_type', '=', request.env.ref('hr_rfid.hr_rfid_card_type_barcode').id),
        ]
        barcode_count = WebCards.search_count(domain)
        webcards = WebCards.search(domain)
        calc_tokens_if_neccessery = [wc._portal_ensure_token() for wc in webcards]

        values.update({
            'webcards': webcards,
            'page_name': 'Web Cards',
            'default_url': '/my/webcard',
        })
        return request.render("hr_rfid_portal.portal_my_webcards", values)

    @http.route(['/my/cards'], type='http', auth="user", website=True)
    def portal_my_cards(self, access_token=None, **kw):
        values = self._prepare_portal_layout_values()
        Cards = request.env['hr.rfid.card'].sudo()
        domain = [
            ('contact_id', '=', request.env.user.partner_id.id),
            ('card_type', '!=', request.env.ref('hr_rfid.hr_rfid_card_type_barcode').id),
        ]
        cards_count = Cards.search_count(domain)
        cards = Cards.search(domain)

        values.update({
            'cards': cards,
            'page_name': 'Cards',
            'default_url': '/my/cards',
        })
        return request.render("hr_rfid_portal.portal_my_cards", values)