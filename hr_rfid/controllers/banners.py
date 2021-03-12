from odoo import http, fields, exceptions, _
from odoo.http import request
from enum import Enum

import datetime
import json
import logging

_logger = logging.getLogger(__name__)


class MyController(http.Controller):
    # model('crm.lead', "[('type','=', 'lead')]"):model
    @http.route(["/hr_rfid/banner/<string:model>/<string:view_type>"], auth='user', type='json')
    def banner_modules(self, model, view_type: str):
        """ Returns the `banner` for the sale onboarding panel.
                    It can be empty if the user has closed it or if he doesn't have
                    the permission to see it. """
        return {}
        if view_type == 'form':
            return {}
        body = {
            'html': """
            
                        <div class="o_form_statusbar">
                            <h1>hello, world for {} {}</h1>
                        </div> """.format(view_type, model)
        }
        return {
            'html': request.env.ref('hr_rfid.webstack_onboarding_panel')._render({
                'body': body,
            })
        }
