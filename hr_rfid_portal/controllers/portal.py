import json
from collections import OrderedDict
from operator import itemgetter
from markupsafe import Markup
from werkzeug.exceptions import NotFound

from odoo import conf, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, content_disposition
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class RFIDCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'barcode_count' in counters:
            values['barcode_count'] = request.env['hr.rfid.card'].search_count(
                [('card_type', '=', request.env.ref('hr_rfid.hr_rfid_card_type_barcode').id)]) \
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

    @http.route(['/my/webcards'], type='http', auth="user", website=True)
    def portal_my_webcards(self, **kw):
        user_id = request.env.user
        if not user_id:
            return request.redirect('/my')
        domain = [('card_type', '=', request.env.ref('hr_rfid.hr_rfid_card_type_barcode').id)]
        if user_id.partner_id.is_employee:
            domain.append(('employee_id', '=', user_id.partner_id.employee_ids[0].id))
        else:
            domain.append(('contact_id', '=', user_id.partner_id.id))
        user_barcode_cards = request.env['hr.rfid.card'].sudo().search(domain)
        values = {
            'page_name': 'webcards',
            'cards': user_barcode_cards,
        }
        return request.render("hr_rfid_portal.portal_barcode_table", values)

    @http.route(['/my/webcard/<int:card_id>'], type='http', auth="public", website=True)
    def portal_my_webcard(self, card_id, access_token=None, **kw):
        try:
            card_sudo = self._document_check_access('hr.rfid.card', card_id, access_token)
        except (AccessError, MissingError):
            raise NotFound
        if not card_sudo:
            raise NotFound
        if kw.get('report_type',False) == 'pdf':
            report_name = 'Foldable Badge - %s' % (card_sudo.get_owner().display_name or 'Access Badge').replace('/','')
            pdf = \
                request.env['ir.actions.report'].sudo()._render_qweb_pdf(
                    'hr_rfid.action_report_hr_rfid_card_foldable_badge', [card_id])[0]
            pdfhttpheaders = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf)),
                ('Content-Disposition', content_disposition(f'{report_name}.pdf')),
            ]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            values = self._card_get_page_view_values(card_sudo, access_token, **kw)
            return request.render("hr_rfid_portal.portal_my_barcode", values)
    @http.route(['/my/events'], type='http', auth="user", website=True)
    def portal_my_events(self, **kw):
        user_id = request.env.user
        if not user_id:
            return request.redirect('/my')
        domain = []
        if user_id.partner_id.is_employee:
            domain.append(('employee_id', '=', user_id.partner_id.employee_ids[0].id))
        else:
            domain.append(('contact_id', '=', user_id.partner_id.id))
        user_events = request.env['hr.rfid.event.user'].sudo().search(domain, limit=30)
        values = {
            'page_name': 'events',
            'events': user_events,
        }
        return request.render("hr_rfid_portal.portal_user_event_table", values)
