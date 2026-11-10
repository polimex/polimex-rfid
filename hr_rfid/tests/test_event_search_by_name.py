# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""A security officer finds access events by typing in the search box.

Live case, 10.11.2026: on a client's system an officer typed a text in the
search box of the user events and pressed Enter. The box's first option is the
event's name, and every such search ended in an error dialog - the name is
worked out when it is shown, and nothing told the database how to search it.
The list without a text, and the other options, kept working, so nobody had
hit it before.

The name reads "person - action @ door". Searching it is searching those
parts: the person (or, without one, the contact), the action as the officer
reads it, and the door.
"""

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid", "rfid_events")
class TestEventSearchByName(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        webstack = cls.env["hr.rfid.webstack"].create(
            {
                "name": "Search Stack",
                "serial": "SRCH00001",
                "company_id": company.id,
                "available": "a",
                "tz": "Europe/Sofia",
                "active": True,
            }
        )
        ctrl = cls.env["hr.rfid.ctrl"].create(
            {
                "name": "Search Controller",
                "ctrl_id": 91,
                "webstack_id": webstack.id,
            }
        )
        cls.front = cls.env["hr.rfid.door"].create(
            {
                "name": "Front Entrance",
                "number": 9101,
                "controller_id": ctrl.id,
                "company_id": company.id,
            }
        )
        cls.store = cls.env["hr.rfid.door"].create(
            {
                "name": "Storeroom",
                "number": 9102,
                "controller_id": ctrl.id,
                "company_id": company.id,
            }
        )
        reader = cls.env["hr.rfid.reader"].create(
            {
                "name": "Search Reader",
                "number": 1,
                "reader_type": "0",
                "controller_id": ctrl.id,
            }
        )
        cls.petrova = cls.env["hr.employee"].create({"name": "Elena Petrova"})
        cls.kolev = cls.env["hr.employee"].create({"name": "Stoyan Kolev"})
        cls.visitor = cls.env["res.partner"].create({"name": "Visiting Auditor"})

        def event(door, action, **owner):
            return cls.env["hr.rfid.event.user"].create(
                dict(
                    {
                        "reader_id": reader.id,
                        "door_id": door.id,
                        "event_action": action,
                        "event_time": fields.Datetime.now(),
                    },
                    **owner,
                )
            )

        cls.ev_petrova = event(cls.front, "1", employee_id=cls.petrova.id)
        cls.ev_kolev = event(cls.store, "2", employee_id=cls.kolev.id)
        cls.ev_visitor = event(cls.store, "1", contact_id=cls.visitor.id)
        cls.ours = cls.ev_petrova | cls.ev_kolev | cls.ev_visitor

    def _found(self, domain):
        return self.env["hr.rfid.event.user"].search(domain) & self.ours

    def test_an_officer_finds_a_persons_events_by_part_of_the_name(self):
        """Typing part of a person's name finds that person's events, and only them."""
        self.assertEqual(self._found([("name", "ilike", "petrov")]), self.ev_petrova)

    def test_a_visitor_without_a_staff_record_is_found_by_the_contact_name(self):
        """An event of a contact, not of an employee, is found by the contact's name."""
        self.assertEqual(self._found([("name", "ilike", "Auditor")]), self.ev_visitor)

    def test_the_door_in_the_name_finds_the_events_at_that_door(self):
        """The name ends with the door; typing the door finds what happened there."""
        self.assertEqual(
            self._found([("name", "ilike", "storeroom")]),
            self.ev_kolev | self.ev_visitor,
        )

    def test_the_action_as_the_officer_reads_it_finds_those_events(self):
        """Typing the action shown in the name ("Denied") finds the refused attempts."""
        self.assertEqual(self._found([("name", "ilike", "denied")]), self.ev_kolev)

    def test_a_text_in_no_name_finds_nothing(self):
        """A text that is not in any of the names finds none of these events."""
        self.assertFalse(self._found([("name", "ilike", "Nobody Of That Name")]))

    def test_leaving_a_person_out_keeps_everyone_else(self):
        """ "Name does not contain" leaves that person's events out and keeps the rest."""
        self.assertEqual(
            self._found([("name", "not ilike", "petrov")]),
            self.ev_kolev | self.ev_visitor,
        )

    def test_a_custom_filter_on_the_exact_name_finds_that_event(self):
        """ "Add Custom Filter" with Name = the shown name finds that one event."""
        for event in (self.ev_petrova, self.ev_visitor):
            self.assertEqual(
                self._found([("name", "=", event.name)]),
                event,
                "the exact name %r did not find its event" % event.name,
            )
        self.assertFalse(
            self._found([("name", "=", "Elena Petrova")]),
            "part of a name is not the name",
        )

    def test_is_set_and_is_not_set_answer_instead_of_failing(self):
        """Every event has a name, so "is set" keeps them all and "is not set" none."""
        self.assertEqual(self._found([("name", "!=", False)]), self.ours)
        self.assertFalse(self._found([("name", "=", False)]))

    def test_not_this_event_by_its_shown_name_answers_instead_of_failing(self):
        """ "Not this event", asked by the shown name, answers and leaves it out.

        Which of the others it keeps is core's rule for a negative name search
        (every searched field must differ, an empty link included), not ours.
        """
        found = self._found([("display_name", "!=", self.ev_kolev.name)])
        self.assertNotIn(self.ev_kolev, found)

    def test_the_search_box_with_a_text_still_fills_the_side_panel(self):
        """The exact call that failed live: the side panel counts under a text search."""
        panel = self.env["hr.rfid.event.user"].search_panel_select_range(
            "event_action",
            search_domain=[("name", "ilike", "petrov")],
            enable_counters=True,
        )
        counts = {value["id"]: value["__count"] for value in panel["values"]}
        self.assertGreaterEqual(
            counts.get("1", 0),
            1,
            "the granted event of the person searched for is not counted",
        )

    def test_an_event_is_found_by_its_name_where_events_are_picked(self):
        """Where an event is picked from a list by typing, its name finds it."""
        found = self.env["hr.rfid.event.user"].name_search("Petrova", limit=None)
        self.assertIn(self.ev_petrova.id, [event_id for event_id, _name in found])
        self.assertNotIn(self.ev_kolev.id, [event_id for event_id, _name in found])
