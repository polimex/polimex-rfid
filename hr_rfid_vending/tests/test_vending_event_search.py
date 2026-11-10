# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""A vending operator finds sales by typing in the search box.

The first option of the vending events' search box is the event's name, and
a sale is shown as "product - buyer". An operator who types a product's name
expects that product's sales; one who types a person's name, that person's
purchases. Every other vending event (an error, a cash collection) reads as
an access event does: "person - action @ door".

The name is also what the list shows for each event, so it must not depend
on which other events are shown with it.
"""

from odoo import fields
from odoo.tests.common import HttpCase, TransactionCase, tagged


def vending_machine(env, serial):
    """A coin vending machine on its own module, and the reader of its events."""
    webstack = env["hr.rfid.webstack"].create(
        {
            "name": "Vending Search Stack %s" % serial,
            "serial": serial,
            "company_id": env.company.id,
            "tz": "Europe/Sofia",
            "active": True,
        }
    )
    ctrl = env["hr.rfid.ctrl"].create(
        {
            "name": "Vending Search Machine %s" % serial,
            "ctrl_id": 7,
            "hw_version": "16",
            "webstack_id": webstack.id,
        }
    )
    reader = env["hr.rfid.reader"].create(
        {
            "name": "Vending Search Reader %s" % serial,
            "number": 1,
            "reader_type": "0",
            "controller_id": ctrl.id,
        }
    )
    return ctrl, reader


def vending_event(env, ctrl, reader, action, **values):
    """An event of that machine, now."""
    return env["hr.rfid.vending.event"].create(
        dict(
            {
                "event_action": action,
                "event_time": fields.Datetime.now(),
                "controller_id": ctrl.id,
                "ctrl_addr": ctrl.ctrl_id,
                "reader_id": reader.id,
            },
            **values,
        )
    )


@tagged("post_install", "-at_install", "rfid_vending", "rfid_vending_search")
class TestVendingEventSearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ctrl, reader = vending_machine(cls.env, "VSRCH0001")
        cls.door = cls.env["hr.rfid.door"].create(
            {
                "name": "Canteen Door",
                "number": 9201,
                "controller_id": ctrl.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.cola = cls.env["product.template"].create({"name": "Sparkling Cola"})
        cls.water = cls.env["product.template"].create({"name": "Still Water"})
        # A product name with the separator the sale's name uses.
        cls.juice = cls.env["product.template"].create({"name": "Juice - Orange"})
        cls.petrova = cls.env["hr.employee"].create({"name": "Elena Petrova"})
        cls.kolev = cls.env["hr.employee"].create({"name": "Stoyan Kolev"})

        def event(action, **values):
            return vending_event(cls.env, ctrl, reader, action, **values)

        cls.cola_petrova = event(
            "47", item_sold_id=cls.cola.id, employee_id=cls.petrova.id
        )
        cls.water_kolev = event(
            "47", item_sold_id=cls.water.id, employee_id=cls.kolev.id
        )
        cls.juice_kolev = event(
            "47", item_sold_id=cls.juice.id, employee_id=cls.kolev.id
        )
        # A cash sale from a slot without a product: no product, no buyer.
        cls.cash_sale = event("47")
        cls.error_petrova = event("48", employee_id=cls.petrova.id, door_id=cls.door.id)
        cls.ours = (
            cls.cola_petrova
            | cls.water_kolev
            | cls.juice_kolev
            | cls.cash_sale
            | cls.error_petrova
        )

    def _found(self, domain):
        return self.env["hr.rfid.vending.event"].search(domain) & self.ours

    def test_an_operator_finds_the_sales_of_a_product_by_part_of_its_name(self):
        """Typing part of a product's name finds that product's sales, and only them."""
        self.assertEqual(self._found([("name", "ilike", "cola")]), self.cola_petrova)

    def test_a_buyers_name_finds_the_buyers_purchases(self):
        """Typing a person's name finds what that person bought."""
        self.assertEqual(
            self._found([("name", "ilike", "kolev")]),
            self.water_kolev | self.juice_kolev,
        )

    def test_a_machine_error_is_found_by_the_person_and_the_door(self):
        """An error reads as an access event, so its person and door find it."""
        self.assertEqual(
            self._found([("name", "ilike", "petrova")]),
            self.cola_petrova | self.error_petrova,
        )
        self.assertEqual(
            self._found([("name", "ilike", "canteen")]), self.error_petrova
        )

    def test_a_product_name_does_not_find_other_products_or_errors(self):
        """Negative: a text in no shown name finds none of these events."""
        self.assertFalse(self._found([("name", "ilike", "Lemonade")]))

    def test_leaving_a_product_out_keeps_every_other_event(self):
        """ "Name does not contain" leaves that product's sales out and keeps the rest."""
        self.assertEqual(
            self._found([("name", "not ilike", "cola")]),
            self.ours - self.cola_petrova,
        )

    def test_every_event_keeps_its_own_name_whatever_is_listed_with_it(self):
        """The list shows each event's own name; a list of several events
        does not change it (live: sales read as "person - Purchase Complete"
        and the last other event in the list had no name)."""
        names_one_by_one = {}
        for event in self.ours:
            event.invalidate_recordset(["name"])
            names_one_by_one[event] = event.with_prefetch(event.ids).name
        self.ours.invalidate_recordset(["name"])
        for event in self.ours:
            self.assertEqual(event.name, names_one_by_one[event])
        self.assertEqual(self.cola_petrova.name, "Sparkling Cola - Elena Petrova")
        self.assertEqual(
            self.error_petrova.name,
            "Elena Petrova - %s @ Canteen Door"
            % self.error_petrova.get_event_action_text(),
        )

    def test_a_cash_sale_without_a_product_still_has_a_name_that_finds_it(self):
        """A sale with neither product nor buyer reads as its action and is found by it."""
        label = self.cash_sale.get_event_action_text()
        self.assertEqual(self.cash_sale.name, label)
        self.assertEqual(self._found([("name", "ilike", label)]), self.cash_sale)
        self.assertEqual(self._found([("name", "!=", False)]), self.ours)

    def test_a_custom_filter_on_the_exact_name_finds_that_event(self):
        """ "Add Custom Filter" with Name = the shown name finds that one event,
        a product whose name holds " - " included."""
        for event in self.ours:
            self.assertEqual(
                self._found([("name", "=", event.name)]),
                event,
                "the exact name %r did not find its event" % event.name,
            )
        self.assertFalse(
            self._found([("name", "=", "Sparkling Cola")]),
            "the product alone is not the name of a sale with a buyer",
        )

    def test_the_search_box_with_a_product_still_fills_the_side_panel(self):
        """The side panel counts the event types under a text search: the
        sale of that product, and no machine error."""
        panel = self.env["hr.rfid.vending.event"].search_panel_select_range(
            "event_action",
            search_domain=[("name", "ilike", "Sparkling Cola")],
            enable_counters=True,
        )
        counts = {value["id"]: value["__count"] for value in panel["values"]}
        self.assertGreaterEqual(counts.get("47", 0), 1)
        self.assertFalse(counts.get("48"))


@tagged("post_install", "-at_install", "rfid_vending", "rfid_vending_search")
class TestVendingEventSearchTour(HttpCase):
    """Process: an operator finds the sales of a product by typing its name
    in the vending events' search box and pressing Enter."""

    _registry_readonly_enabled = False

    def test_an_operator_finds_a_products_sales_from_the_search_box(self):
        ctrl, reader = vending_machine(self.env, "VSRCH0002")
        buyer = self.env["hr.employee"].create({"name": "SearchTour Buyer"})
        for product in ("SearchTour Cola", "SearchTour Water"):
            vending_event(
                self.env,
                ctrl,
                reader,
                "47",
                employee_id=buyer.id,
                item_sold_id=self.env["product.template"].create({"name": product}).id,
            )
        self.start_tour(
            "/odoo/action-hr_rfid_vending.hr_rfid_vending_event_action",
            "hr_rfid_vending_event_search_by_product_tour",
            login="admin",
        )
