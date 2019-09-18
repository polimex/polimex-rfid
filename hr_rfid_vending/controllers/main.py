# -*- coding: utf-8 -*-
from odoo import http, fields, exceptions
from odoo.http import request

from odoo.addons.hr_rfid.controllers.main import WebRfidController


class HrRfidVending(WebRfidController):
    @http.route(['/hr/rfid/event'], type='json', auth='none', method=['POST'], csrf=False)
    def post_event(self, **post):

        def ret_super():
            return super(HrRfidVending, self).post_event(**post)

        # if 'event' in post:
        #     ret = parse_event()
        # else:
        ret = ret_super()

        return ret

