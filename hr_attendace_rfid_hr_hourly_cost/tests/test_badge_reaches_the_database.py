# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
"""A card swipe must still be recorded on an installation that also prices hours.

This covers the SEAM nothing else covered: the module's own tests never go
through the public route, and hr_rfid's tests never have the Monetary columns,
which arrive only when this module is installed. A swipe that reaches neither
the passage nor the priced day fails here.

WHAT IT DOES NOT COVER, said plainly so nobody reads a green run as proof:
the flush-time failure seen at a customer on 08.09.2026 (ValueError: Expected
singleton: res.users() - a stored Monetary column asking its currency how to
round, in a request environment that has no user) does NOT reproduce here. This
test was written to catch it and passes with the guard removed, so it is not
evidence about that defect. It reproduces only on a database carrying the
customer's own data; what exactly that database has and a clean one does not is
still unknown, and until it is named there is no automated regression for it.
"""
import json

from dateutil.relativedelta import relativedelta

from odoo.addons.hr_rfid.tests.test_functional import RFIDTests
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install', 'rfid_hourly_cost', 'rfid_public_route')
class TestBadgeReachesTheDatabase(RFIDTests, HttpCase):
    """The guard walks past the reader; the passage has to be there afterwards."""

    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The money side of the installation: an employee who costs something.
        # Without an hourly cost the daily row still gets Monetary columns, but
        # this is the shape a real payroll installation has.
        cls.test_employee_id.sudo().write({'hourly_cost': 12.5})

    def _at(self, seconds_ago):
        """The device payload for a moment ``seconds_ago`` before now.

        The three strings come from one datetime so the entry stays strictly
        before the exit - otherwise both swipes carry the same second and the
        stay never closes.
        """
        moment = self.test_now - relativedelta(seconds=seconds_ago)
        return {
            'date': '%02d.%02d.%02d' % (moment.day, moment.month, moment.year - 2000),
            'day': '%d' % moment.weekday(),
            'time': '%02d:%02d:%02d' % (moment.hour, moment.minute, moment.second),
        }

    def test_a_badge_on_an_attendance_zone_is_recorded(self):
        """The passage reaches the database, and the day is priced.

        On the customer site this produced nothing at all: every swipe raised
        at flush and the whole request rolled back, so a full working day left
        zero rows behind while the reader kept beeping green at people.
        """
        # The hardware is provisioned the way the field does it - the module
        # announces itself and the controller answers - because the defect
        # lives in the request, not in the data.
        self._add_iCon130()
        self._change_mode(self.c_130, 2)

        zone = self.env['hr.rfid.zone'].create({
            'name': 'Cost Attendance Zone',
            'company_id': self.test_company_id,
            'attendance': True,
            'door_ids': [(4, self.c_130.door_ids[0].id, 0)],
        })
        self.assertTrue(zone.attendance)

        before = self.env['hr.rfid.event.user'].search_count([
            ('employee_id', '=', self.test_employee_id.id),
        ])

        # The real entry point: the device posts to the public route. BOTH
        # halves matter - the day is priced when the stay CLOSES, so it is the
        # exit swipe that writes the money columns and reaches the flush.
        self._make_event(self.c_130, card=self.test_card_employee.number,
                         reader=1, event_code=3, **self._at(180))
        self._make_event(self.c_130, card=self.test_card_employee.number,
                         reader=4, event_code=15, **self._at(120))

        self.env.invalidate_all()
        after = self.env['hr.rfid.event.user'].search_count([
            ('employee_id', '=', self.test_employee_id.id),
        ])
        self.assertEqual(
            after, before + 2,
            "Both swipes must leave a passage behind. Missing rows mean the "
            "request rolled back - the state the customer was in, with the "
            "reader granting access and the database staying empty.",
        )
        # And the day itself has to exist, priced: that write is what reaches
        # the flush where the customer's installation died.
        extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.test_employee_id.id),
        ])
        self.assertTrue(
            extra, "Closing the stay must leave a daily row behind")

    def test_a_stranger_at_the_open_endpoint_gets_nothing(self):
        """A wrong key writes nothing and is refused - without elevated rights.

        The route is open to the internet by design: a controller proves itself
        with its own key, not with a login. The request is given a user only
        AFTER that key checks out, so anything a stranger posts is parsed and
        refused with no rights at all. This is the half that would go unnoticed
        if the escalation ever drifted back to the top of the handler.
        """
        self._add_iCon130()
        # A PROVISIONED device: its stored key is a real one. Without this the
        # stack still holds the '0000' placeholder, and then a stranger's key
        # is not rejected but ADOPTED - the deliberate first-contact path - so
        # the test would be measuring provisioning, not refusal.
        self.test_webstack_10_3_id.sudo().key = 'A1B2'

        before_events = self.env['hr.rfid.event.user'].search_count([])
        before_stacks = self.env['hr.rfid.webstack'].search_count([])

        response = self.url_open(
            '/hr/rfid/event',
            data=json.dumps({
                'convertor': self.test_webstack_10_3_id.serial,
                'key': 'DEAD',          # not this device's key
                'event': {'id': 1, 'cmd': 'FA', 'bos': 1, 'tos': 1,
                          'event_n': 3, 'card': self.test_card_employee.number,
                          'reader': 1, 'time': '08:00:00', 'day': 1,
                          'date': '01.01.26', 'dt': '0000'},
            }),
            timeout=30, headers={'Content-Type': 'application/json'})

        self.env.invalidate_all()
        self.assertEqual(
            self.env['hr.rfid.event.user'].search_count([]), before_events,
            "A request with the wrong key must not record a passage")
        self.assertEqual(
            self.env['hr.rfid.webstack'].search_count([]), before_stacks,
            "...nor bring a device into the database")
        self.assertNotEqual(
            response.status_code, 500,
            "The refusal must be an answer, not a crash: %s" % response.text[:200])
