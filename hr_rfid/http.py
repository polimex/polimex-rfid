# -*- coding: utf-8 -*-


from odoo import http
import logging

_logger = logging.getLogger(__name__)

class CustomRoot(http.Root):

    def get_request(self, httprequest):
        _logger.info('+++++++++++++++Custom root working!!!')
        return super(CustomRoot, self).get_request(httprequest)
        # deduce type of request
        # if httprequest.mimetype in ("application/json", "application/json-rpc"):
        #     return JsonRequest(httprequest)
        # else:
        #     return HttpRequest(httprequest)

http.Root = CustomRoot
http.root = CustomRoot()