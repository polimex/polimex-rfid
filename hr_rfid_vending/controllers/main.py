# -*- coding: utf-8 -*-
from odoo import http, fields, exceptions, _
from odoo.http import request
from functools import reduce
from decimal import Decimal
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
    def __init__(self, *args, **kwargs):
        self._post = None
        self._webstacks_env = None
        self._webstack = None
        super(HrRfidVending, self).__init__(*args, **kwargs)

    @http.route(['/hr/rfid/event'], type='json', auth='none', method=['POST'], csrf=False)
    def post_event(self, **post):
        self._post = post
        self._webstacks_env = request.env['hr.rfid.webstack'].sudo()
        cmd_env = request.env['hr.rfid.command'].sudo()
        ev_env = request.env['hr.rfid.vending.event'].sudo()
        sys_ev_env = request.env['hr.rfid.event.system'].sudo()

        self._webstack = self._webstacks_env.search([ ('serial', '=', str(post['convertor'])) ])
        status_code = 200

        item_missing_err_str = _('Item number %d missing from vending machine configuration')
        item_cost_diff_err_str = _('Item %s has the cost of %f but vending reported it costs %f!')

        def ret_super():
            return super(HrRfidVending, self).post_event(**post)

        def create_ev(controller, event, card, ev_num, item_sold_id=None, transaction_price=None,
                      item_number=None):
            ev = {
                'event_action': ev_num,
                'event_time': self._get_ws_time_str(),
                'controller_id': controller.id,
                'input_js': json.dumps(post),
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

        # TODO Use self._report_sys_ev instead of this
        def create_sys_ev(controller, event, message):
            sys_ev_env.create({
                'webstack_id': self._webstack.id,
                'controller_id': controller.id,
                'timestamp': self._get_ws_time_str(),
                'event_action': str(self._post['event']['event_n']),
                'error_description': message,
                'input_js': json.dumps(self._post),
            })

        def get_employee_balance(employee, controller):
            balance = employee.hr_rfid_vending_balance
            balance = Decimal(str(balance))
            if employee.hr_rfid_vending_negative_balance is True:
                balance += Decimal(str(abs(employee.hr_rfid_vending_limit)))
            if employee.hr_rfid_vending_in_attendance is True:
                if employee.attendance_state == 'checked_out':
                    return '0000', 0
            if balance <= 0:
                return '0000', 0
            if employee.hr_rfid_vending_daily_limit != 0:
                limit = abs(employee.hr_rfid_vending_daily_limit)
                limit = Decimal(str(limit))
                limit -= Decimal(str(employee.hr_rfid_vending_spent_today))
                if limit < balance:
                    balance = limit
            balance *= 100
            balance /= controller.scale_factor
            balance = int(balance)
            if balance > 0xFF:
                balance = 0xFF
            b1 = (balance & 0xF0) // 0x10
            b2 = balance & 0x0F
            return '%02X%02X' % (b1, b2), balance

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
                create_sys_ev(controller, event, err_msg)
                return -1
            return item.list_price

        def calc_balance(controller, event):
            received_balance = int(event['dt'][6:8], 16)*0x10 + int(event['dt'][8:10], 16)
            return (received_balance * controller.scale_factor) / 100

        def parse_event():
            controller = self._webstack.controllers.filtered(lambda r: r.ctrl_id == post['event']['id'])
            event = post['event']
            if len(controller) == 0:
                return ret_super()

            # If it's not a vending controller
            if controller.hw_version != '16':
                return ret_super()

            card_env = request.env['hr.rfid.card'].sudo()

            # TODO Move into function "deal_with_ev_64"
            if event['event_n'] == 64:
                card = card_env.search([ ('number', '=', event['card']) ])

                if len(card) == 0 or len(card.employee_id) == 0:
                    return ret_super()

                emp = card.employee_id

                if emp.hr_rfid_vending_in_attendance is True \
                        and emp.attendance_state != 'checked_in':
                    return ret_super()

                date = self._get_ws_time()
                if date + datetime.timedelta(minutes=5) <= datetime.datetime.now():
                    ev = create_ev(controller, event, card, '64')
                    return self._check_for_unsent_cmd(status_code, ev)

                if event['bos'] < event['tos']:
                    ev = create_ev(controller, event, card, '64')
                    return self._check_for_unsent_cmd(status_code, ev)

                balance_str, balance = get_employee_balance(card.employee_id, controller)
                card_number = reduce(operator.add, list('0' + str(a) for a in card.number), '')

                ev = create_ev(controller, event, card, '64')
                cmd = cmd_env.create({
                    'webstack_id': self._webstack.id,
                    'controller_id': controller.id,
                    'cmd': 'DB2',
                    'cmd_data': '4000' + card_number + balance_str,
                })
                ev.command_id = cmd
                return self._send_command(cmd, status_code)
            # TODO Move into function "deal_with_ev_47"
            elif event['event_n'] == 47:
                card = card_env.search([ ('number', '=', event['card']) ])

                if len(card) == 0:
                    if event['card'] != '0000000000':
                        return ret_super()
                elif len(card.employee_id) == 0:
                    return ret_super()

                item_number = int(event['dt'][4:6], 16)
                item_price = -1
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
                        return self._check_for_unsent_cmd(status_code, ev)

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
                            create_sys_ev(controller, event, item_cost_diff_err_str
                                          % (item.name, item.list_price, calced_price))

                    # TODO Reduce item quantity

                if len(card) > 0:
                    ev = create_ev(controller, event, card, '47', item, purchase_money, item_number=item_sold)
                    card.employee_id.hr_rfid_vending_purchase(purchase_money, ev.id)
                else:
                    controller.cash_contained = controller.cash_contained + item_price
                    ev = create_ev(controller, event, card, '47', item, item_price, item_number=item_sold)

                return self._check_for_unsent_cmd(status_code, ev)
            # TODO Move into function "deal_with_err_evs"
            elif event['event_n'] in [48, 49]:
                create_sys_ev(controller, event, 'Vending machine sent us an error')
                return self._check_for_unsent_cmd(status_code)

            return ret_super()

        try:
            if 'event' in post:
                t0 = time.time()
                _logger.debug('Vending: Received=' + str(post))
                ret = parse_event()
                t1 = time.time()
                _logger.debug('Took %2.03f time to form response=%s' % ((t1-t0), str(ret)))
            else:
                ret = ret_super()

            return ret
        except (KeyError, exceptions.UserError, exceptions.AccessError, exceptions.AccessDenied,
                exceptions.MissingError, exceptions.ValidationError, exceptions.DeferredException,
                psycopg2.DataError, ValueError) as __:
            request.env['hr.rfid.event.system'].sudo().create({
                'webstack_id': self._webstack.id,
                'timestamp': fields.Datetime.now(),
                'error_description': traceback.format_exc(),
                'input_js': json.dumps(post),
            })
            _logger.debug('Vending: Caught an exception, returning status=500 and creating a system event')
            return { 'status': 500 }
        except BadTimeException:
            t = self._post['event']['date'] + ' ' + self._post['event']['time']
            ev_num = str(self._post['event']['event_n'])
            controller = self._webstack.controllers.filtered(lambda r: r.ctrl_id == self._post['event']['id'])
            sys_ev_dict = {
                'webstack_id': self._webstack.id,
                'controller_id': controller.id,
                'timestamp': fields.Datetime.now(),
                'event_action': ev_num,
                'error_description': 'Controller sent us an invalid date or time: ' + t,
                'input_js': json.dumps(self._post),
            }
            request.env['hr.rfid.event.system'].sudo().create(sys_ev_dict)
            _logger.debug('Caught a time error, returning status=200 and creating a system event')
            return { 'status': 200 }
