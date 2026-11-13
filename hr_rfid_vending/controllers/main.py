# -*- coding: utf-8 -*-
from odoo import http, fields, exceptions
from odoo.http import request
from functools import reduce
from odoo.addons.hr_rfid.controllers.main import WebRfidController, BadTimeException

import operator
import datetime
import traceback
import json
import psycopg2
import logging
import time

_logger = logging.getLogger(__name__)


class HrRfidVending(WebRfidController):

    @http.route(['/hr/rfid/event'], type='json2', auth='none', methods=['POST'], cors='*', csrf=False,
                save_session=False, sitemap=False, readonly=False)
    def post_event(self, **post):
        post_data = self._decode_post(post)

        # A raw/barcode device POST has no 'convertor'; this override otherwise
        # shadows the base handler's raw-data path, so delegate to it.
        if 'convertor' not in post_data:
            return super().post_event(**post)

        # SECURITY: validate the module key (constant-time) before processing
        # any vending event. The base /hr/rfid/event handler authenticates the
        # webstack, but this override short-circuits it for vending hardware;
        # without this gate a forged event for a known serial could drive a
        # vending grant (DB2) with no key.
        webstack_id, auth_error = self._authenticate_webstack(post_data)
        if auth_error is not None:
            return auth_error

        cmd_env = request.env['hr.rfid.command'].sudo()
        ev_env = request.env['hr.rfid.vending.event'].sudo()
        sys_ev_env = request.env['hr.rfid.event.system'].sudo()

        status_code = 200

        item_missing_err_str = request.env._('Item number %d missing from vending machine configuration')
        item_cost_diff_err_str = request.env._('Item %s has the cost of %f but vending reported it costs %f!')
        def ret_super():
            return super(HrRfidVending, self).post_event(**post)
        def ret_local_no_command(controller, ev=None):
            return ret_local(controller.webstack_id.check_for_unsent_cmd(status_code, ev))
        def ret_local(data):
            if not post and 'cmd' in data:
                return {'cmd': data['cmd']}
            return data

        def vending_sys_ev(controller, description):
            """A system event that says which machine event, card and time it
            is about - the way the core reports a refused card."""
            event = post_data['event']
            card = event.get('card')
            return controller.report_sys_ev(description, post_data=post_data, sys_ev_dict={
                'event_action': str(event['event_n']),
                'card_number': card if card and card != '0000000000' else False,
            })

        def create_ev(controller, event, card, ev_num, item_sold_id=None, transaction_price=None,
                      item_number=None):
            ev = {
                'event_action': ev_num,
                'event_time': controller.webstack_id.get_ws_time_str(post_data=event),
                'controller_id': controller.id,
                'ctrl_addr': controller.ctrl_id,
                'reader_id': controller.reader_ids.filtered(lambda r: r.number == event['reader']).id,
                'input_js': json.dumps(post_data),
            }
            if len(card) > 0:
                ev['card_id'] = card.id
                ev['employee_id'] = card.employee_id.id
            if item_sold_id is not None and len(item_sold_id) > 0:
                ev['item_sold_id'] = item_sold_id.id
            if transaction_price is not None:
                ev['transaction_price'] = transaction_price
            if item_number is not None:
                ev['item_sold'] = item_number
            return ev_env.create(ev)

        def get_item_price(controller, item, event, err_msg):
            """
            Gets an item's balance. If item does not exist, returns 0 and creates a system event with '
            err_msg' as error_description
            :param controller: Controller singleton
            :param item: Item singleton or empty set
            :param event: Event dictionary
            :param err_msg: Error message to be used in the system
                            event in case of the need to create a system event
            :return: 0 if item does not exist, else the cost of the item in human money
            """
            if len(item) == 0:
                vending_sys_ev(controller, err_msg)
                return -1
            return item.list_price

        def calc_balance(controller, event, second=False):
            if not second:
                received_balance = int(event['dt'][6:8], 16) * 0x10 + int(event['dt'][8:10], 16)
                return (received_balance * controller.scale_factor) / 100
            else:
                received_balance = int(event['dt'][10:12], 16) * 0x10 + int(event['dt'][12:14], 16)
                return (received_balance * controller.scale_factor) / 100

        def parse_event():
            controller = webstack_id.controllers.filtered(lambda r: r.ctrl_id == post_data['event']['id'])
            event = post_data['event']
            if len(controller) == 0:
                return ret_super()

            # If it's not a vending controller
            if not controller.is_vending_ctrl():
                return ret_super()

            card_env = request.env['hr.rfid.card'].with_company(webstack_id.company_id).sudo()
            _logger.info('Vending event %d on %s, card=%s', event['event_n'], controller.name, event.get('card', '?'))

            # A machine that keeps its own prices (MDB) reports a sale without
            # its price: it gets no credit, and no sale is booked as zero.
            if event['event_n'] == 64 and not controller._vending_has_price_table():
                _logger.info('Vending ev64 on %s refused: the machine keeps its own prices', controller.name)
                vending_sys_ev(controller, request.env._(
                    'This vending machine keeps its own prices, and Odoo cannot record its sales yet, '
                    'so it gets no credit for cards.'))
                return ret_local_no_command(controller)
            if event['event_n'] in (47, 50) and not controller._vending_has_price_table():
                # The machine has already handed out the item or taken the
                # money; the system event is the only trace of it in Odoo.
                _logger.warning('Vending ev%d on %s not recorded: the machine keeps its own prices',
                                event['event_n'], controller.name)
                vending_sys_ev(controller, request.env._(
                    'This vending machine reported a transaction (card %(card)s, item %(item)s, data %(data)s) '
                    'that Odoo does not record, because the machine keeps its own prices. '
                    'Check it on the machine.',
                    card=event.get('card'), item=int(event['dt'][4:6], 16), data=event['dt']))
                return ret_local_no_command(controller)

            # TODO Move into function "deal_with_ev_64"
            if event['event_n'] == 64:
                card = card_env.with_context(active_test=False).search(
                    [('company_id', '=', webstack_id.company_id.id), ('internal_number', '=', event['card'])])

                # A refused card leaves a system event, as in the core: the
                # operator sees which card and why.
                if len(card) == 0:
                    _logger.info('Vending ev64 denied: card=%s not found', event['card'])
                    vending_sys_ev(controller, request.env._('Could not find the card'))
                    return ret_local_no_command(controller, None)
                if not card.active or len(card.employee_id) == 0:
                    _logger.info('Vending ev64 denied: card=%s inactive or without an employee', event['card'])
                    vending_sys_ev(controller, request.env._(
                        'The card is archived or belongs to no employee, so it gets no vending credit.'))
                    return ret_local_no_command(controller, None)

                emp = card.employee_id

                if emp.hr_rfid_vending_in_attendance is True \
                        and emp.attendance_state != 'checked_in':
                    _logger.info('Vending ev64 denied: %s not checked in', emp.name)
                    vending_sys_ev(controller, request.env._(
                        '%(employee)s is not checked in, and gets vending credit only after a check-in.',
                        employee=emp.name))
                    return ret_local_no_command(controller, None)

                date = controller.webstack_id.get_ws_time(event)
                if date + datetime.timedelta(minutes=5) <= fields.Datetime.now():
                    _logger.info('Vending ev64 denied: event too old (%s)', date)
                    ev = create_ev(controller, event, card, '64')
                    return ret_local_no_command(controller, ev)

                if event['bos'] < event['tos']:
                    _logger.info('Vending ev64 denied: bos(%d) < tos(%d)', event['bos'], event['tos'])
                    ev = create_ev(controller, event, card, '64')
                    return ret_local_no_command(controller, ev)

                balance_str, balance = card.employee_id.get_employee_balance(controller)
                card_number = reduce(operator.add, list('0' + str(a) for a in card.internal_number), '')

                ev = create_ev(controller, event, card, '64')
                if balance <= 0:
                    _logger.info('Vending ev64 denied: %s balance=%.2f', emp.name, balance)
                    return ret_local_no_command(controller, ev)
                _logger.info('Vending ev64 granted: %s balance=%.2f, sending DB2', emp.name, balance)
                cmd = cmd_env.create({
                    'webstack_id': webstack_id.id,
                    'controller_id': controller.id,
                    'cmd': 'DB2',
                    'cmd_data': '4000' + card_number + balance_str,
                    # The credit answers the card shown at this moment. Left
                    # without a reply it is closed, never sent again later -
                    # the machine must not be handed credit for somebody who
                    # has already walked away.
                    'single_attempt': True,
                })
                ev.command_id = cmd
                return ret_local(cmd.send_command(status_code))
            # TODO Move into function "deal_with_ev_47"
            elif event['event_n'] == 47:
                card = card_env.with_context(active_test=False).search(
                    [('company_id', '=', webstack_id.company_id.id), ('internal_number', '=', event['card'])])

                if len(card) == 0:
                    if event['card'] != '0000000000':
                        return ret_super()
                # is_card = len(card) == 0

                item_number = int(event['dt'][4:6], 16)  # 00 0019 000c 0000
                shifted_item_number = int(event['dt'][8:10], 16)  # 000000 0003 000a
                item_price = (int(event['dt'][6:8], 16) * 16 + int(event['dt'][8:10],
                                                                   16)) * controller.scale_factor / 100
                change_price = (int(event['dt'][10:12], 16) * 16 + int(event['dt'][12:14],
                                                                   16)) * controller.scale_factor / 100
                # Fix for Leonid shifts!!!
                # if is_card and item_number == 0 and shifted_item_number != 0:
                if item_number == 0 and shifted_item_number != 0 and change_price != 0:
                    item_number = shifted_item_number
                    item_price = change_price
                # Fix for Leonid shifts!!!

                calced_price = calc_balance(controller, event)
                item = None
                purchase_money = calced_price
                item_sold = None
                if item_number != 0:
                    item_sold = item_number
                    row_num = int((item_number - 1) / 4) + 1
                    item_num = item_number - 1
                    item_num %= 4
                    item_num += 1

                    if row_num < 1 or row_num > 18:
                        ev = create_ev(controller, event, card, '-1')
                        return ret_local_no_command(controller, ev)

                    rows_env = request.env['hr.rfid.ctrl.vending.row'].sudo()
                    row = rows_env.search([
                        ('controller_id', '=', controller.id),
                        ('row_num', '=', row_num)
                    ])

                    if len(row) == 0:
                        controller.create_vending_rows()
                        row = rows_env.search([
                            ('controller_id', '=', controller.id),
                            ('row_num', '=', row_num)
                        ])

                    if item_num == 1:
                        item = row.item1
                    elif item_num == 2:
                        item = row.item2
                    elif item_num == 3:
                        item = row.item3
                    else:
                        item = row.item4

                    item_price = get_item_price(controller, item, event, item_missing_err_str % item_number)
                    if item_price >= 0:
                        purchase_money = item_price
                        if item_price != calced_price:
                            vending_sys_ev(
                                controller, item_cost_diff_err_str % (item.name, item.list_price, calced_price))

                    # TODO Reduce item quantity

                if len(card) > 0:
                    ev = create_ev(controller, event, card, '47', item, purchase_money, item_number=item_sold)
                    card.employee_id.hr_rfid_vending_purchase(purchase_money, ev.id)
                else:
                    # The same amount as a card sale: an item missing from the
                    # price table counts at the price the machine reported,
                    # never as the -1 that marks it missing.
                    controller.cash_contained += purchase_money
                    ev = create_ev(controller, event, card, '47', item, purchase_money, item_number=item_sold)

                _logger.info('Vending ev47 purchase: card=%s item=%s price=%.2f',
                             event['card'], item_sold, purchase_money)
                return ret_local_no_command(controller, ev)
            # TODO Move into function "deal_with_err_evs"
            elif event['event_n'] in [48, 49]:
                _logger.info('Vending ev%d from %s: %s', event['event_n'], controller.name, event['dt'])
                vending_sys_ev(controller, controller._vending_problem_text(event['event_n'], event['dt']))
                return ret_local_no_command(controller)
            elif event['event_n'] == 50:
                card = card_env.with_context(active_test=False).search(
                    [('company_id', '=', webstack_id.company_id.id), ('internal_number', '=', event['card'])])

                if len(card) == 0:
                    if event['card'] != '0000000000':
                        return ret_super()

                item_number = int(event['dt'][4:6], 16)  # must be 99 (0x63)
                recharge_balance = calc_balance(controller, event, True)
                if len(card) > 0 and item_number == 99 and recharge_balance > 0:
                    ev = create_ev(controller, event, card, '50', transaction_price=recharge_balance)
                    card.employee_id.hr_rfid_vending_recharge_balance += ev.transaction_price
                    return ret_local_no_command(controller, ev)
            return ret_super()

        try:
            # A savepoint around the work, as in the base handler: a failed
            # report is undone as a whole, and the record of the failure can
            # still be written after an error from the database.
            with request.env.cr.savepoint():
                if 'event' in post_data:
                    _logger.info('Received=%s', post_data)
                    ret = parse_event()
                else:
                    ret = ret_super()

            return self._make_response(ret)
        except (KeyError, exceptions.UserError, exceptions.AccessError, exceptions.AccessDenied,
                exceptions.MissingError, exceptions.ValidationError,
                psycopg2.DataError, ValueError) as e:
            _logger.error('Vending exception from %s/%s: %s\n%s',
                          webstack_id.name, webstack_id.company_id.name, str(e), traceback.format_exc())
            webstack_id.with_context(keep_report=True).report_sys_ev(description=traceback.format_exc(),
                                      post_data=json.dumps(post_data))
            return self._make_response({'status': 500})
        except BadTimeException:
            t = post_data['event']['date'] + ' ' + post_data['event']['time']
            controller = webstack_id.controllers.filtered(lambda r: r.ctrl_id == post_data['event']['id'])
            _logger.error('Vending bad time from %s: %s', controller.name if controller else '?', t)
            controller.with_context(keep_report=True).report_sys_ev(description=f'Controller sent us an invalid date or time: {t}',
                                     post_data=json.dumps(post_data))
            return self._make_response({'status': 200})
