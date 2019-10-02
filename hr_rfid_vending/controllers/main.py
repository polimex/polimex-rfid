# -*- coding: utf-8 -*-
from odoo import http, fields, exceptions, _
from odoo.http import request
from functools import reduce
from decimal import Decimal

from odoo.addons.hr_rfid.controllers.main import WebRfidController

import operator
import datetime
import traceback
import json


class HrRfidVending(WebRfidController):
    @http.route(['/hr/rfid/event'], type='json', auth='none', method=['POST'], csrf=False)
    def post_event(self, **post):
        print('post=' + str(post))
        webstacks_env = request.env['hr.rfid.webstack'].sudo()
        cmd_env = request.env['hr.rfid.command'].sudo()
        ev_env = request.env['hr.rfid.vending.event'].sudo()
        sys_ev_env = request.env['hr.rfid.event.system'].sudo()
        webstack = webstacks_env.search([ ('serial', '=', str(post['convertor'])) ])
        status_code = 200

        item_missing_err_str = _('Item number %d missing from vending machine configuration')
        item_cost_diff_err_str = _('Item %s has the cost of %f but vending reported it costs %f!')

        def ret_super():
            return super(HrRfidVending, self).post_event(**post)

        def create_ev(controller, event, card, ev_num, item_sold_id=None, transaction_price=None,
                      item_number=None, sent_balance=None):
            ev = {
                'event_action': ev_num,
                'event_time': event['date'] + ' ' + event['time'],
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
            if sent_balance is not None:
                ev['sent_balance'] = sent_balance
            return ev_env.create(ev)

        def create_sys_ev(controller, event, message):
            sys_ev_env.create({
                'webstack_id': webstack.id,
                'controller_id': controller.id,
                'timestamp': event['date'] + ' ' + event['time'],
                'error_description': message,
            })

        def get_employee_balance(employee, controller):
            balance = employee.hr_rfid_vending_balance
            if employee.hr_rfid_vending_negative_balance is True:
                balance += employee.hr_rfid_vending_limit
            if employee.hr_rfid_vending_in_attendance is True:
                if employee.attendance_state == 'checked_out':
                    return '0000', 0
            balance = Decimal(str(balance))
            balance *= 100
            balance /= controller.scale_factor
            balance = int(balance)
            if balance > 0xFF:
                balance = 0xFF
            b1 = int((balance & 0xF0) / 0x10)
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
                return 0
            return item.list_price

        def calc_balance(controller, event, card):
            last_ev = ev_env.search([
                ('controller_id', '=', controller.id),
                ('event_action', '=', '64'),
                ('card_id', '=', card.id),
            ])
            if len(last_ev) == 0:
                raise exceptions.ValidationError(
                    'Controller knows the balance of a user but we never sent it the balance????'
                )
            # Take the event that was last created
            last_balance = reduce(lambda a, b: a if a.id > b.id else b, last_ev)
            last_balance = last_balance.sent_balance
            if last_balance < -1:
                raise exceptions.ValidationError('???????????????')
            received_balance = int(event['dt'][10:12], 16)*0x10 + int(event['dt'][12:14], 16)
            difference = last_balance - received_balance
            difference *= controller.scale_factor
            difference /= 100
            return difference

        def parse_event():
            controller = webstack.controllers.filtered(lambda r: r.ctrl_id == post['event']['id'])
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

                date = datetime.datetime.strptime(
                    event['date'] + ' ' + event['time'],
                    '%m.%d.%y %H:%M:%S'
                )
                if date + datetime.timedelta(minutes=5) <= datetime.datetime.now():
                    ev = create_ev(controller, event, card, '64')
                    return self._check_for_unsent_cmd(status_code, ev)

                if event['bos'] < event['tos']:
                    ev = create_ev(controller, event, card, '64')
                    return self._check_for_unsent_cmd(status_code, ev)

                balance_str, balance = get_employee_balance(card.employee_id, controller)
                card_number = reduce(operator.add, list('0' + str(a) for a in card.number), '')

                ev = create_ev(controller, event, card, '64', sent_balance=balance)
                cmd = cmd_env.create({
                    'webstack_id': webstack.id,
                    'controller_id': controller.id,
                    'cmd': 'DB',
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
                # TODO Reduce item quantity

                if len(card) > 0:
                    item_price = get_item_price(controller, item, event, item_missing_err_str % item_number)
                    calced_price = calc_balance(controller, event, card)
                    if len(item) > 0:
                        purchase_money = item_price
                        if item_price != calced_price:
                            create_sys_ev(controller, event, item_cost_diff_err_str
                                          % (item.name, item.list_price, calced_price))
                    else:
                        purchase_money = calced_price
                    card.employee_id.hr_rfid_vending_purchase(purchase_money)
                    ev = create_ev(controller, event, card, '47', item, purchase_money, item_number=item_sold)
                else:
                    item_price = get_item_price(controller, item, event, item_missing_err_str % item_number)
                    controller.cash_contained = controller.cash_contained + item_price
                    ev = create_ev(controller, event, card, '47', item, item_price, item_number=item_sold)

                return self._check_for_unsent_cmd(status_code, ev)
            # TODO Move into function "deal_with_err_evs"
            elif event['event_n'] in [48, 49]:
                card = card_env.search([ ('number', '=', event['card']) ])
                ev = create_ev(controller, event, card, str(event['event_n']))
                return self._check_for_unsent_cmd(status_code, ev)

            return ret_super()

        try:
            if 'event' in post:
                ret = parse_event()
            else:
                ret = ret_super()

            print('ret=' + str(ret))
            return ret
        except (KeyError, exceptions.UserError, exceptions.AccessError, exceptions.AccessDenied,
                exceptions.MissingError, exceptions.ValidationError, exceptions.DeferredException) as __:
            request.env['hr.rfid.event.system'].sudo().create({
                'webstack_id': self._webstack.id,
                'timestamp': fields.Datetime.now(),
                'error_description': traceback.format_exc(),
            })
            return { 'status': 500 }

