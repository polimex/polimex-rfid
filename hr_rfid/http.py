# -*- coding: utf-8 -*-
import json

from odoo import http
import logging

from odoo.http import Response
from odoo.tools import date_utils

_logger = logging.getLogger(__name__)


# def _json_response(self, result=None, error=None):
#     response = {
#         'jsonrpc': '2.0',
#         'id': self.jsonrequest.get('id')
#         }
#     if error is not None:
#         response['error'] = error
#     if result is not None:
#         response['result'] = result
#
#     mime = 'application/json'
#     if not self.jsonrequest.get('id', False) and not self.jsonrequest.get('jsonrpc', False) and (result is not None):
#         # Non RPC Request not needed to respond with RPC structure
#         body = json.dumps(result, default=date_utils.json_default)
#         if result.get('status', False) and len(result) == 1:
#             body = ''
#             return Response(
#                 body, status=result.get('status', 200),
#                 headers=[('Content-Type', mime), ('Content-Length', len(body))]
#             )
#     else:
#         body = json.dumps(response, default=date_utils.json_default)
#
#     return Response(
#         body, status=error and error.pop('http_status', 200) or 200,
#         headers=[('Content-Type', mime), ('Content-Length', len(body))]
#     )

def _response(self, result=None, error=None):
    response = {'jsonrpc': '2.0', 'id': self.request_id}
    if error is not None:
        response['error'] = error
    if result is not None:
        response['result'] = result

    if not self.jsonrequest.get('id', False) and not self.jsonrequest.get('jsonrpc', False) and (result is not None):
        # Non RPC Request not needed to respond with RPC structure
        # body = json.dumps(result, default=date_utils.json_default)
        response = result
        if result.get('status', False) and len(result) == 1:
            # response = {}
            return Response('', status=200)

    return self.request.make_json_response(response)


setattr(http.JsonRPCDispatcher, '_response', _response)
