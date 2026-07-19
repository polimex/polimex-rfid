# -*- coding: utf-8 -*-
import json
import traceback
import time
import psycopg2

from odoo.addons.hr_rfid.models.hr_rfid_webstack import BadTimeException
from odoo.addons.hr_rfid.models.hr_rfid_event_system import HrRfidSystemEvent
from odoo import http, fields, exceptions, _, SUPERUSER_ID
from odoo.http import request, Response
from odoo.tools import consteq
from odoo.addons.hr_rfid.controllers import polimex
from odoo.addons.hr_rfid.models.hr_rfid_event_system import action_selection as system_action_selection

import logging

_logger = logging.getLogger(__name__)


def _ws_db_update_dict():
    return {
        'last_ip':_get_remote_ip_address() ,
        'updated_at': fields.Datetime.now(),
    }


def _get_remote_ip_address():
    if hasattr(request, 'access_route') and request.access_route:
        return request.access_route[-1]
    # elif 'HTTP_X_FORWARDED_FOR' in request.httprequest.environ:
    #     return request.httprequest.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]
    else:
        return request.httprequest.environ['REMOTE_ADDR']


class WebRfidController(http.Controller):

    def _parse_event(self, post_data: dict, webstack):
        """Thin delegate - the parsing core lives on ``hr.rfid.webstack``
        (``models/hr_rfid_webstack_hw_events.py``) so the websocket ingress
        can reuse it. Kept as a method so route overrides that call it keep
        working unchanged."""
        return webstack._hw_parse_event(post_data)

    def _respond_to_ev_64(self, open_door, controller, reader, card, post_data):
        """Thin delegate - core on hr.rfid.webstack (see _hw_respond_to_ev_64)."""
        return controller.webstack_id._hw_respond_to_ev_64(
            open_door, controller, reader, card, post_data)


    @http.route(['/hr/rfid/barcode'], type='json2', auth='none', methods=['POST'], cors='*', csrf=False,
                save_session=False, sitemap=False, readonly=False)
    def post_barcode(self, **post):
        """
        :param post: Dictionary of parameters sent in the POST request.
        :return: List of dictionaries with barcode data.

        This method is used to handle barcode data sent in a POST request. It receives a dictionary of parameters in the `post` parameter. The method processes the barcode data and returns a list of dictionaries with barcode information.

        The barcode data is expected to be sent in the following format:
        {
            "cmd": {
                "reader": <reader_id>,
                "type": <barcode_type>
            }
        }

        The method logs the received barcode data and returns a response with barcode information for further processing.

        Example usage:
        ```
        import requests

        url = 'http://example.com/hr/rfid/barcode'
        barcode_data = {
            "cmd": {
                "reader": 1,
                "type": 0
            }
        }
        response = requests.post(url, json=barcode_data)
        barcode_info = response.json()
        ```
        """
        # request.session.should_save = False
        return
        _logger.info(request.jsonrequest)
        return [{
            "id": 1,
            "method": "POST",
            "body": {"cmd": {"reader": 1, "type": 0}}
        }]

    def _decode_post(self, post):
        if 'jsonrpc' in post:
            # ESP32 JSON-RPC 2.0 format — unwrap params
            self._is_jsonrpc = True
            self._jsonrpc_id = post.get('id')
            return post.get('params', {})
        self._is_jsonrpc = False
        if not post:
            decoded_string = request.httprequest.data.decode('utf-8')
            return json.loads(decoded_string)
        return post

    def _make_response(self, result):
        """Wrap the result for the wire the module speaks. THREE shapes:

        - JSON-RPC 2.0 (ESP32 100.1, ``enable_json_rpc`` + jsonrpc envelope):
          ``{"jsonrpc":"2.0","id":..,"result":{...}}`` - production default.
        - PLAIN (ESP32 100.1 with ``wire=plain``, owner directive INTEROP
          2026-07-13): the FULL result BARE - ``{"status":..,"cmd":..,"ws":..}``
          with NO envelope, so ``result.ws`` provisioning survives. The caller
          (:meth:`post_event`) sets ``_wire_plain`` from the device SERIAL
          (:meth:`~hr.rfid.webstack._serial_is_100_1`, '4' => 100.1)
          BEFORE auth/parse, so every exit - including auth-failure 400s and
          exception 500/200 - reaches a 100.1 as a parseable full dict. It MUST
          NOT touch the legacy path.
        - Legacy 10.3 (non-jsonrpc, non-100.1): UNCHANGED - empty body when no
          command, else only ``{"cmd":{...}}`` WITHOUT ``status`` (the 10.3
          firmware JSON parser reads tokens[2] for the cmd; a ``status`` key
          shifts positions and raises error 21).
        """
        if isinstance(result, Response):
            return result
        if getattr(self, '_is_jsonrpc', False):
            return Response(
                json.dumps({
                    'jsonrpc': '2.0',
                    'id': self._jsonrpc_id,
                    'result': result,
                }),
                content_type='application/json; charset=utf-8',
            )
        # PLAIN wire - ESP32 (WS-capable) ONLY. Full result bare, envelope-free.
        if getattr(self, '_wire_plain', False):
            if isinstance(result, dict):
                return Response(json.dumps(result),
                                content_type='application/json; charset=utf-8')
            return result
        # Legacy module (10.3): strip "status" key from response - UNCHANGED.
        if isinstance(result, dict):
            if 'cmd' in result:
                body = json.dumps({k: v for k, v in result.items() if k != 'status'})
            else:
                return Response('', status=200)
            return Response(body, content_type='application/json; charset=utf-8')
        return result

    def _authenticate_webstack(self, post_data):
        """Find and authenticate the webstack behind a hardware POST.

        Returns a ``(webstack, error_response)`` tuple. On success
        ``error_response`` is ``None``. On failure the webstack may be empty
        (or a record, kept for the system-event log) and ``error_response`` is
        a ready response the caller must return.

        Shared by the base ``/hr/rfid/event`` handler and the
        ``hr_rfid_vending`` override so that BOTH validate the module key with
        a constant-time compare before any event is processed — a forged event
        for a known serial must not be able to drive a controller without the
        key.
        """
        webstack = request.env['hr.rfid.webstack'].with_user(SUPERUSER_ID).search([
            '|', ('active', '=', True), ('active', '=', False),
            ('serial', '=', str(post_data['convertor'])),
        ])
        if not webstack:
            if request.env['ir.config_parameter'].sudo().get_param(
                    'hr_rfid.save_new_webstacks') in ['true', 'True', '1']:
                Webstack = request.env['hr.rfid.webstack']
                # WS auto-enable (owner 2026-07-14): a 100.1 (serial '4')
                # supports the real-time channel, so turn it on at discovery -
                # no manual "Enable real-time" click needed for WS to come up.
                # The next heartbeat then carries the ws provisioning block
                # (en:1) and the device opens its socket. Opt-out: an admin can
                # still disable it afterwards. Legacy 10.3 (serial not '4')
                # stays HTTP-only.
                ws_on = Webstack._serial_is_100_1(post_data['convertor'])
                webstack = Webstack.sudo().with_context(
                    tz=request.env['res.users'].sudo().browse(2).tz).create({
                        'name': f"Module {post_data['convertor']}",
                        'serial': str(post_data['convertor']),
                        'key': post_data['key'],
                        'last_ip': _get_remote_ip_address(),
                        'updated_at': fields.Datetime.now(),
                        'available': 'a',
                        'company_id': request.env['res.company'].sudo().search([])[0].id,
                        'ws_enabled': ws_on,
                        'ws_provision_pending': ws_on,
                    })
            else:
                _logger.info('Unknown Module. Received=' + str(post_data))
                return webstack, self._make_response({'status': 400})

        key = str(post_data.get('key') or '')
        key_secure = bool(key) and key != '0000'
        if not webstack.key:
            # First contact for a keyless module. Adopt only a real (NON-zero)
            # key - NEVER persist the insecure '0000' placeholder (owner + FW-Q26,
            # 2026-07-19): the firmware mints a non-zero credential.
            if key_secure:
                webstack.key = key
                webstack.available = 'a'
                webstack.message_post(body=_("The Module contacted us and activated."))
            elif webstack.available != 'a':
                # Unprovisioned device (presents '0000'/blank): activate ONCE and
                # keep it keyless + flagged; do NOT re-announce/warn on every
                # heartbeat - _authenticate_webstack runs on every POST, so a
                # per-POST warning + chatter would flood the log and grow
                # mail.message unbounded (idempotency).
                webstack.available = 'a'
                _logger.info(
                    'Module %s contacted us with the insecure key %r - kept '
                    'unprovisioned; it needs a real generated key.',
                    webstack.serial, key)
        elif str(webstack.key) == '0000' and key_secure:
            # G1 heal: a legacy '0000' module now presents a real generated key ->
            # adopt it (replace the insecure placeholder). '0000' is unprovisioned,
            # so this is a provisioning, not a credential override of a real key;
            # the classic channel is TLS in production.
            webstack.key = key
            webstack.message_post(body=_("The Module was re-keyed from the insecure default."))
        elif not consteq(webstack.key, str(post_data['key'])):
            webstack.report_sys_ev('Webstack key and key in json did not match', post_data=post_data)
            _logger.info(
                f'Wrong Module key for {webstack.name}/{webstack.company_id.name}! Received=' + str(post_data))
            return webstack, self._make_response({'status': 400})

        if not webstack.active:
            webstack.write(_ws_db_update_dict())
            webstack.report_sys_ev('Webstack is not active', post_data=post_data)
            return webstack, self._make_response({'status': 400})

        return webstack, None

    @http.route(['/hr/rfid/event'], type='json2', auth='none', methods=['POST'], cors='*', csrf=False,
                save_session=False, sitemap=False, readonly=False)
    def post_event(self, **post):
        """
        This method handles the POST request to the '/hr/rfid/event' route. It processes the received data from the request and performs necessary actions based on the data.

        :param post: A dictionary containing the data from the request. If empty, it retrieves the data from the jsonrequest in the request object.
        :return: A dictionary containing the result of the processing.

        """
        post_data = self._decode_post(post)
        _logger.info('Received=' + str(post_data))

        if 'convertor' not in post_data:
            return self._parse_raw_data(post_data)

        webstack_id = request.env['hr.rfid.webstack']
        # Plain wire (owner directive INTEROP 2026-07-13; serial-gate
        # 2026-07-14): fix the response envelope from the device SERIAL right
        # HERE - before auth and before any parse - so that EVERY exit emits a
        # parseable full-dict ack to a 100.1: the auth-failure 400s raised INSIDE
        # _authenticate_webstack (wrong key / inactive / unknown module), the
        # exception 500/200 in the except blocks below, AND the success path.
        # Deciding it post-parse (the old code) left auth-failure and Odoo-side
        # exceptions on the legacy empty-body branch: a 100.1 then saw an empty
        # body and could not tell "keep the event" (500) from "delete it" (200)
        # - the exact event loss the 500 exists to prevent. '4' => 100.1 is the
        # SSOT rule on hr.rfid.webstack; jsonrpc is unaffected (it always wraps).
        self._wire_plain = (
            not getattr(self, '_is_jsonrpc', False)
            and webstack_id._serial_is_100_1(post_data.get('convertor')))
        try:
            webstack_id, auth_error = self._authenticate_webstack(post_data)
            if auth_error is not None:
                return auth_error

            result = {
                'status': 400
            }

            if 'heartbeat' in post_data:
                _logger.info(f'Heartbeat from {webstack_id.name}/{webstack_id.company_id.name}!')
                result = webstack_id.parse_heartbeat(post_data=post_data)
            elif 'event' in post_data:
                _logger.info(f'Event (%s) from {webstack_id.name}/{webstack_id.company_id.name}' % (
                    ''.join([a[1] for a in system_action_selection if
                             a[0] == str(post_data['event']['event_n'])])
                )
                             )
                result = self._parse_event(post_data=post_data, webstack=webstack_id)
            elif 'response' in post_data:
                _logger.info(f'Command response from {webstack_id.name}/{webstack_id.company_id.name}')
                result = webstack_id.parse_response(post_data=post_data)
            if not post and 'cmd' in result:
                result = {'cmd': result['cmd']}
            result = webstack_id._ws_provision_payload(result)
            webstack_id.write(_ws_db_update_dict())
            return self._make_response(result)
        except (KeyError, exceptions.UserError, exceptions.AccessError, exceptions.AccessDenied,
                exceptions.MissingError, exceptions.ValidationError,
                psycopg2.DataError, ValueError) as e:
            # commented DeferredException ^
            _logger.error(
                f'Caught an exception from {webstack_id.name}/{webstack_id.company_id.name}, returning status=500 and '
                f'creating a system event: %s\n%s',
                str(e),
                traceback.format_exc())

            # _logger.error('Caught an exception, returning status=500 and creating a system event (%s)' % str(e))
            request.env['hr.rfid.event.system'].sudo().create({
                'webstack_id': webstack_id and webstack_id.id,
                'timestamp': fields.Datetime.now(),
                'error_description': traceback.format_exc() or str(e),
                'input_js': json.dumps(post_data),
            })
            return self._make_response({'status': 500})
        except BadTimeException:
            _logger.error(f'Caught a time error from {webstack_id.name}/{webstack_id.company_id.name}, returning '
                          f'status=200 and creating a system event')
            t = post_data['event']['date'] + ' ' + post_data['event']['time']
            ev_num = str(post_data['event']['event_n'])
            controller_id = webstack_id.controllers.filtered(lambda r: r.ctrl_id == post_data['event']['id'])
            sys_ev_dict = {
                'webstack_id': webstack_id.id,
                'controller_id': controller_id.id,
                'timestamp': fields.Datetime.now(),
                'event_action': ev_num,
                'error_description': 'Controller sent us an invalid date or time: ' + t,
                'input_js': json.dumps(post_data),
            }
            request.env['hr.rfid.event.system'].sudo().create(sys_ev_dict)
            return self._make_response({'status': 200})
        except Exception as e:
            _logger.error(f'Caught an exception from {webstack_id.name}/{webstack_id.company_id.name}, returning '
                          f'status=500 and creating a system event: %s\n%s', str(e),
                          traceback.format_exc())
            request.env['hr.rfid.event.system'].sudo().create([{
                'webstack_id': webstack_id and webstack_id.id,
                'timestamp': fields.Datetime.now(),
                'error_description': str(e),
                'input_js': json.dumps(post_data),
            }])
            return self._make_response({'status': 500})

    def _parse_raw_data(self, post_data: dict):
        """
        Parses the raw data received from the RFID webstack.

        :param post_data: The raw data received from the RFID webstack.
        :return: If the 'serial', 'security', and 'events' keys are present in the post_data dictionary, it calls the _parse_barcode_device method with the post_data. Otherwise, it returns a dictionary with a 'status' key set to 200.

        :rtype: dict
        """
        if 'serial' in post_data and 'security' in post_data and 'events' in post_data:
            return self._parse_barcode_device(post_data)

        return {'status': 200}

    def _parse_barcode_device(self, post_data: dict):
        """
        :param post_data: A dictionary containing the post data received from the barcode device. It should have the following keys:
            - 'serial': The serial number of the barcode device.
            - 'security': The security key of the barcode device.
        :return: A dictionary containing the parsed data from the barcode device.

        The method creates a new record in the 'hr.rfid.raw.data' table with the provided post data. It sets the 'do_not_save' field to True, the 'identification' field with the serial number, and the 'data' field with the serialized post data.

        After creating the record, it retrieves the 'return_data' field value from the created record. If the 'do_not_save' field was set to True, the record is unlinked, meaning it gets deleted from the database.

        Finally, the method returns the parsed data from the barcode device as a dictionary. The 'return_data' field value is deserialized from JSON to a dictionary using the 'json.loads()' method.
        """
        ret = request.env['hr.rfid.raw.data'].create([{
            'do_not_save': True,
            'identification': post_data['serial'],
            'security': post_data['security'],
            'data': json.dumps(post_data),
        }])

        ret_data = ret.return_data

        if ret.do_not_save is True:
            ret.unlink()

        return json.loads(ret_data)

    def vending_request_for_balance(self):
        raise NotImplementedError('Not implemented')
