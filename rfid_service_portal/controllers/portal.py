from collections import OrderedDict
from operator import itemgetter
from markupsafe import Markup

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
        if 'service_count' in counters:
            values['service_count'] = request.env['rfid.service.sale'].sudo().search_count([
                ('partner_id', '=', request.env.user.partner_id.id)
            ])
        return values

    @http.route(['/my/rfid/service'], type='http', auth="user", website=True)
    def portal_my_rfid_service(self, access_token=None, **kw):
        sudo_rfid_service = request.env['rfid.service.sale'].sudo()
        values = self._prepare_portal_layout_values()
        domain = [('partner_id', '=', request.env.user.partner_id.id)]
        partner_rfid_services = sudo_rfid_service.search(domain)
        values.update({
            'services': partner_rfid_services,
        })
        return request.render("rfid_service_portal.portal_my_rfid_services", values)
