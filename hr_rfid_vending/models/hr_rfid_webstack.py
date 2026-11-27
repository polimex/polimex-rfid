# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""What a vending machine reports, and what it is told.

The reports of a vending controller are answered where every report of a
module is read (hr.rfid.webstack._hw_parse_event), so the answer is the same
whichever way the report came: the module's classic connection, its real-time
connection, or the demo that walks the same path. They used to be answered in
a route of their own, in front of the one every other controller goes through,
and a machine on a real-time module got no credit at all.
"""

import datetime
import json
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

# The reports of a vending controller that are this add-on's to answer.
CREDIT_REQUEST = 64
SALE = 47
MACHINE_PROBLEMS = (48, 49)
CASH_ON_CARD = 50
# The item number a machine reports for cash put on a card.
CASH_ON_CARD_ITEM = 99
# A request for credit is answered for the card shown at that moment. A report
# that reaches Odoo later than this is recorded and given nothing: the person
# has walked away from the machine.
CREDIT_REQUEST_ANSWERED_WITHIN = datetime.timedelta(minutes=5)
NO_CARD = "0000000000"
# The rows of a machine's price table, four items to a row.
ITEMS_PER_ROW = 4
PRICE_TABLE_ROWS = 18


class HrRfidWebstack(models.Model):
    _inherit = "hr.rfid.webstack"

    def _hw_parse_event(self, post_data: dict):
        """A vending machine's reports are answered here; all others by the core."""
        controller = self.controllers.filtered(
            lambda c: c.ctrl_id == post_data["event"]["id"]
        )
        if controller and controller.is_vending_ctrl():
            answer = self._hw_vending_event(controller, post_data)
            if answer is not None:
                return answer
        return super()._hw_parse_event(post_data)

    def _hw_vending_event(self, controller, post_data):
        """Answer one report of a vending controller.

        :return: the reply for the module, or None for a report that is not
                 vending's to answer - the core reads it as any controller's
        """
        event = post_data["event"]
        event_n = event["event_n"]
        _logger.info(
            "Vending event %d on %s, card=%s",
            event_n,
            controller.name,
            event.get("card", "?"),
        )

        if (
            event_n in (CREDIT_REQUEST, SALE, CASH_ON_CARD)
            and not controller._vending_has_price_table()
        ):
            # A machine that keeps its own prices (MDB) reports a sale without
            # its price: it gets no credit, and no sale is booked as zero.
            if event_n == CREDIT_REQUEST:
                _logger.info(
                    "Vending ev64 on %s refused: the machine keeps its own prices",
                    controller.name,
                )
                self._hw_vending_sys_ev(
                    controller,
                    post_data,
                    self.env._(
                        "This vending machine keeps its own prices, and Odoo cannot record its sales yet, "
                        "so it gets no credit for cards."
                    ),
                )
                return self.check_for_unsent_cmd(200)
            if event_n in (SALE, CASH_ON_CARD):
                # The machine has already handed out the item or taken the
                # money; the system event is the only trace of it in Odoo.
                _logger.warning(
                    "Vending ev%d on %s not recorded: the machine keeps its own prices",
                    event_n,
                    controller.name,
                )
                self._hw_vending_sys_ev(
                    controller,
                    post_data,
                    self.env._(
                        "This vending machine reported a transaction (card %(card)s, item %(item)s, data %(data)s) "
                        "that Odoo does not record, because the machine keeps its own prices. "
                        "Check it on the machine.",
                        card=event.get("card"),
                        item=int(event["dt"][4:6], 16),
                        data=event["dt"],
                    ),
                )
                return self.check_for_unsent_cmd(200)

        if event_n == CREDIT_REQUEST:
            return self._hw_vending_credit_request(controller, post_data)
        if event_n == SALE:
            return self._hw_vending_money_once(
                controller, post_data, self._hw_vending_sale
            )
        if event_n in MACHINE_PROBLEMS:
            _logger.info(
                "Vending ev%d from %s: %s", event_n, controller.name, event["dt"]
            )
            self._hw_vending_sys_ev(
                controller,
                post_data,
                controller._vending_problem_text(event_n, event["dt"]),
            )
            return self.check_for_unsent_cmd(200)
        if event_n == CASH_ON_CARD:
            return self._hw_vending_money_once(
                controller, post_data, self._hw_vending_cash_on_card
            )
        return None

    def _hw_vending_money_once(self, controller, post_data, book):
        """Book a report that moves money once, however often it is reported.

        A module that does not get the answer to its report sends the report
        again. Over the real-time connection the batch keeps account of what
        it has processed (hr.rfid.ws.dedup, _ws_on_event_batch). The classic
        connection kept none, so a sale reported twice was charged twice. The
        same account is kept here, in the same table and by the same key, so
        a sale that came one way and is repeated the other is known too.

        The claim is taken BEFORE the booking: two reports of one sale that
        arrive together must not both pass the check and both be booked. A
        report that is not accepted gives its claim back, and its repeat is
        booked.

        :param book: the method that books this kind of report
        """
        if self.env.context.get("ws_no_publish"):
            # Inside the real-time batch, which keeps this account itself.
            return book(controller, post_data)
        Dedup = self.env["hr.rfid.ws.dedup"]
        key = (self.sudo(), controller.ctrl_id, *Dedup._event_key(post_data["event"]))
        # Seen first: the usual repeat is answered without a refused INSERT,
        # which the database log would show as an error each time.
        if Dedup._seen(*key) or not Dedup._claim(*key):
            _logger.info(
                "Vending ev%d on %s was reported again; it is recorded already",
                post_data["event"]["event_n"],
                controller.name,
            )
            return self.check_for_unsent_cmd(200)
        answer = book(controller, post_data)
        if not (isinstance(answer, dict) and answer.get("status") == 200):
            Dedup._release(*key)
        return answer

    # ------------------------------------------------------------------
    # What the reports have in common
    # ------------------------------------------------------------------

    def _hw_vending_sys_ev(self, controller, post_data, description):
        """A system event that says which machine event, card and time it is
        about - the way the core reports a refused card."""
        event = post_data["event"]
        card = event.get("card")
        return controller.report_sys_ev(
            description,
            post_data=post_data,
            sys_ev_dict={
                "event_action": str(event["event_n"]),
                "card_number": card if card and card != NO_CARD else False,
            },
        )

    def _hw_vending_card(self, event):
        """The card a report names, archived ones included: a sale on a card
        archived since must still find its owner."""
        return (
            self.env["hr.rfid.card"]
            .with_company(self.company_id)
            .sudo()
            .with_context(
                active_test=False,
            )
            .search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("internal_number", "=", event["card"]),
                ]
            )
        )

    def _hw_vending_record(
        self,
        controller,
        post_data,
        card,
        event_action,
        item=None,
        transaction_price=None,
        item_number=None,
    ):
        """Write one vending event down."""
        event = post_data["event"]
        values = {
            "event_action": event_action,
            "event_time": self.get_ws_time_str(post_data=event),
            "controller_id": controller.id,
            "ctrl_addr": controller.ctrl_id,
            "reader_id": controller.reader_ids.filtered(
                lambda r: r.number == event["reader"]
            ).id,
            # The kept copy is read by the people who watch the events; the
            # key the module proves itself with has no place in it.
            "input_js": self.env["hr.rfid.event.system"]._report_without_key(
                json.dumps(post_data)
            ),
        }
        if card:
            values["card_id"] = card.id
            values["employee_id"] = card.employee_id.id
        if item:
            values["item_sold_id"] = item.id
        if transaction_price is not None:
            values["transaction_price"] = transaction_price
        if item_number is not None:
            values["item_sold"] = item_number
        return self.env["hr.rfid.vending.event"].sudo().create(values)

    @staticmethod
    def _hw_vending_amount(controller, event, second=False):
        """One of the two amounts a report carries, in money.

        :param second: the second amount of the report (change, or the cash
                       put on a card) instead of the first (the price)
        """
        at = 10 if second else 6
        units = int(event["dt"][at : at + 2], 16) * 0x10 + int(
            event["dt"][at + 2 : at + 4], 16
        )
        return (units * controller.scale_factor) / 100

    # ------------------------------------------------------------------
    # A card asks how much credit it has
    # ------------------------------------------------------------------

    def _hw_vending_credit_request(self, controller, post_data):
        event = post_data["event"]
        card = self._hw_vending_card(event)

        # A refused card leaves a system event, as in the core: the operator
        # sees which card and why.
        if not card:
            _logger.info("Vending ev64 denied: card=%s not found", event["card"])
            self._hw_vending_sys_ev(
                controller, post_data, self.env._("Could not find the card")
            )
            return self.check_for_unsent_cmd(200, None)
        if not card.active or not card.employee_id:
            _logger.info(
                "Vending ev64 denied: card=%s inactive or without an employee",
                event["card"],
            )
            self._hw_vending_sys_ev(
                controller,
                post_data,
                self.env._(
                    "The card is archived or belongs to no employee, so it gets no vending credit."
                ),
            )
            return self.check_for_unsent_cmd(200, None)

        employee = card.employee_id
        if (
            employee.hr_rfid_vending_in_attendance is True
            and employee.attendance_state != "checked_in"
        ):
            _logger.info("Vending ev64 denied: %s not checked in", employee.name)
            self._hw_vending_sys_ev(
                controller,
                post_data,
                self.env._(
                    "%(employee)s is not checked in, and gets vending credit only after a check-in.",
                    employee=employee.name,
                ),
            )
            return self.check_for_unsent_cmd(200, None)

        asked_at = self.get_ws_time(event)
        if asked_at + CREDIT_REQUEST_ANSWERED_WITHIN <= fields.Datetime.now():
            _logger.info("Vending ev64 denied: event too old (%s)", asked_at)
            recorded = self._hw_vending_record(controller, post_data, card, "64")
            return self.check_for_unsent_cmd(200, recorded)

        if event["bos"] < event["tos"]:
            _logger.info(
                "Vending ev64 denied: bos(%d) < tos(%d)", event["bos"], event["tos"]
            )
            recorded = self._hw_vending_record(controller, post_data, card, "64")
            return self.check_for_unsent_cmd(200, recorded)

        balance_str, balance = employee.get_employee_balance(controller)
        recorded = self._hw_vending_record(controller, post_data, card, "64")
        if balance <= 0:
            _logger.info("Vending ev64 denied: %s balance=%.2f", employee.name, balance)
            return self.check_for_unsent_cmd(200, recorded)
        _logger.info(
            "Vending ev64 granted: %s balance=%.2f, sending DB2", employee.name, balance
        )
        credit = (
            self.env["hr.rfid.command"]
            .sudo()
            .create(
                {
                    "webstack_id": self.id,
                    "controller_id": controller.id,
                    "cmd": "DB2",
                    "cmd_data": "4000"
                    + "".join("0" + digit for digit in card.internal_number)
                    + balance_str,
                    # The credit answers the card shown at this moment. Left without
                    # a reply it is closed, never sent again later - the machine must
                    # not be handed credit for somebody who has already walked away.
                    "single_attempt": True,
                }
            )
        )
        recorded.command_id = credit
        return credit.send_command(200)

    # ------------------------------------------------------------------
    # A sale is complete
    # ------------------------------------------------------------------

    def _hw_vending_sale(self, controller, post_data):
        event = post_data["event"]
        card = self._hw_vending_card(event)
        if not card and event["card"] != NO_CARD:
            # A card this company does not know: the core reports it.
            return None

        item_number = int(event["dt"][4:6], 16)  # 00 0019 000c 0000
        # A record that arrives shifted by one field (000000 0003 000a): the
        # item number sits where the low digits of the price should be. Where
        # it came from is not known; carried over as it was.
        shifted_item_number = int(event["dt"][8:10], 16)
        reported_price = self._hw_vending_amount(controller, event)
        # Read whole even where it decides nothing: a report cut short is
        # refused as a whole, never booked on the half that could be read.
        second_amount = self._hw_vending_amount(controller, event, second=True)
        if item_number == 0 and shifted_item_number != 0 and second_amount != 0:
            item_number = shifted_item_number

        item = self.env["product.template"]
        purchase_money = reported_price
        item_sold = None
        if item_number != 0:
            item_sold = item_number
            row_num = (item_number - 1) // ITEMS_PER_ROW + 1
            position = (item_number - 1) % ITEMS_PER_ROW + 1
            if row_num < 1 or row_num > PRICE_TABLE_ROWS:
                recorded = self._hw_vending_record(controller, post_data, card, "-1")
                return self.check_for_unsent_cmd(200, recorded)

            rows = self.env["hr.rfid.ctrl.vending.row"].sudo()
            row_domain = [
                ("controller_id", "=", controller.id),
                ("row_num", "=", row_num),
            ]
            row = rows.search(row_domain)
            if not row:
                controller.create_vending_rows()
                row = rows.search(row_domain)
            item = row["item%d" % position]

            if not item:
                self._hw_vending_sys_ev(
                    controller,
                    post_data,
                    self.env._(
                        "Item number %d missing from vending machine configuration",
                        item_number,
                    ),
                )
            elif item.list_price >= 0:
                # The price in the table is what the sale costs; a machine
                # that reports another one is told on in the log.
                purchase_money = item.list_price
                if item.list_price != reported_price:
                    self._hw_vending_sys_ev(
                        controller,
                        post_data,
                        self.env._(
                            "%(item)s costs %(price).2f in Odoo, but the machine "
                            "reported a sale at %(reported).2f. The price in Odoo "
                            "was charged.",
                            item=item.name,
                            price=item.list_price,
                            reported=reported_price,
                        ),
                    )

            # TODO Reduce item quantity

        if card:
            recorded = self._hw_vending_record(
                controller,
                post_data,
                card,
                "47",
                item,
                purchase_money,
                item_number=item_sold,
            )
            card.employee_id.hr_rfid_vending_purchase(purchase_money, recorded.id)
        else:
            # The same amount as a card sale: an item missing from the price
            # table counts at the price the machine reported, never as the
            # mark that it is missing.
            controller.cash_contained += purchase_money
            recorded = self._hw_vending_record(
                controller,
                post_data,
                card,
                "47",
                item,
                purchase_money,
                item_number=item_sold,
            )

        _logger.info(
            "Vending ev47 purchase: card=%s item=%s price=%.2f",
            event["card"],
            item_sold,
            purchase_money,
        )
        return self.check_for_unsent_cmd(200, recorded)

    # ------------------------------------------------------------------
    # Cash put on a card at the machine
    # ------------------------------------------------------------------

    def _hw_vending_cash_on_card(self, controller, post_data):
        event = post_data["event"]
        card = self._hw_vending_card(event)
        if not card and event["card"] != NO_CARD:
            # A card this company does not know: the core reports it.
            return None
        item_number = int(event["dt"][4:6], 16)
        amount = self._hw_vending_amount(controller, event, second=True)
        if card and item_number == CASH_ON_CARD_ITEM and amount > 0:
            recorded = self._hw_vending_record(
                controller, post_data, card, "50", transaction_price=amount
            )
            card.employee_id.hr_rfid_vending_recharge_balance += (
                recorded.transaction_price
            )
            return self.check_for_unsent_cmd(200, recorded)
        return None
