from odoo import http, fields, exceptions, _
from odoo.http import request
from enum import Enum

import datetime
import json
import logging

_logger = logging.getLogger(__name__)


class MyController(http.Controller):
    @http.route('/hr_rfid/banner_modules', auth='user', type='json')
    def banner_modules(self):
        """ Returns the `banner` for the sale onboarding panel.
                    It can be empty if the user has closed it or if he doesn't have
                    the permission to see it. """

        company = request.env.company
        if not request.env.is_admin() or \
                company.sale_quotation_onboarding_state == 'closed':
            return {}

        return {
            'html': request.env.ref('sale.sale_quotation_onboarding_panel')._render({
                'company': company,
                'state': company.get_and_update_sale_quotation_onboarding_state()
            })
        }