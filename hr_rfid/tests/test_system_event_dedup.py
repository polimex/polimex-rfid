# -*- coding: utf-8 -*-
"""Regression tests for system-event grouping (_check_duplicate_sys_ev).

The original implementation compared the incoming door/alarm line against the
candidate's CONTROLLER id and matched only the single newest event of the
module with no time limit. Consequences: door-level events (forced/held door)
were never grouped, and a naive field fix would have let a repeat days later
silently vanish into an old row. The fixed behaviour under test:

- identical event repeating within SYS_EV_DEDUP_WINDOW_SECONDS of the row's
  LAST occurrence -> grouped (occurrences += 1, last_occurrence slides);
- different door / after a quiet gap / door vs doorless -> a NEW row.
"""
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models.hr_rfid_event_system import SYS_EV_DEDUP_WINDOW_SECONDS


@tagged('post_install', '-at_install', 'rfid_events', 'rfid_sys_dedup')
class TestSystemEventDedup(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.ref('base.main_company')
        cls.webstack = cls.env['hr.rfid.webstack'].create({
            'name': 'Dedup WS', 'serial': '880001', 'key': '1234',
            'hw_version': '100.1', 'version': '1.44', 'active': True,
            'tz': 'Europe/Sofia', 'company_id': company.id})
        cls.ctrl = cls.env['hr.rfid.ctrl'].create({
            'name': 'Dedup CTRL', 'ctrl_id': 7, 'serial_number': '8801',
            'webstack_id': cls.webstack.id, 'hw_version': '9', 'sw_version': '740',
            'max_cards_count': 100, 'max_events_count': 100, 'readers': 2,
            'mode': 2, 'inputs': 0, 'outputs': 0, 'input_states': 0,
            'output_states': 0, 'alarm_lines': 0, 'io_table_lines': 0,
            'io_table': ''})
        card_type = cls.env.ref('hr_rfid.hr_rfid_card_type_def')
        cls.door1 = cls.env['hr.rfid.door'].create({
            'name': 'Dedup D1', 'number': 1, 'controller_id': cls.ctrl.id,
            'card_type': card_type.id})
        cls.door2 = cls.env['hr.rfid.door'].create({
            'name': 'Dedup D2', 'number': 2, 'controller_id': cls.ctrl.id,
            'card_type': card_type.id})
        cls.now = fields.Datetime.now()

    def _make(self, ts, door=None, action='25'):
        return self.env['hr.rfid.event.system'].create({
            'event_action': action,
            'timestamp': ts,
            'webstack_id': self.webstack.id,
            'controller_id': self.ctrl.id,
            'door_id': door.id if door else False,
        })

    def _count(self, action='25'):
        return self.env['hr.rfid.event.system'].search_count([
            ('webstack_id', '=', self.webstack.id),
            ('event_action', '=', action),
        ])

    def test_same_door_repeat_groups(self):
        """The regression itself: a repeating door event must GROUP (it never
        did - door_id was compared against the controller id)."""
        first = self._make(self.now - timedelta(seconds=120), self.door1)
        self._make(self.now - timedelta(seconds=60), self.door1)
        self.assertEqual(self._count(), 1)
        self.assertEqual(first.occurrences, 2)
        self.assertEqual(first.last_occurrence, self.now - timedelta(seconds=60))

    def test_different_door_new_row(self):
        self._make(self.now - timedelta(seconds=120), self.door1)
        self._make(self.now - timedelta(seconds=60), self.door2)
        self.assertEqual(self._count(), 2)

    def test_after_quiet_gap_new_row(self):
        """A repeat AFTER the window is a new incident - it must never vanish
        into the old row (security visibility)."""
        gap = SYS_EV_DEDUP_WINDOW_SECONDS + 60
        old = self._make(self.now - timedelta(seconds=gap + 60), self.door1)
        self._make(self.now, self.door1)
        self.assertEqual(self._count(), 2)
        self.assertEqual(old.occurrences, 1, "old incident must stay untouched")

    def test_sliding_window_keeps_grouping(self):
        """Repeats each within the window of the PREVIOUS one keep grouping,
        even when the first is older than one window (the window slides)."""
        step = SYS_EV_DEDUP_WINDOW_SECONDS - 60
        first = self._make(self.now - timedelta(seconds=2 * step), self.door1)
        self._make(self.now - timedelta(seconds=step), self.door1)
        self._make(self.now, self.door1)
        self.assertEqual(self._count(), 1)
        self.assertEqual(first.occurrences, 3)
        self.assertEqual(first.last_occurrence, self.now)

    def test_webstack_only_event_groups(self):
        """Module-level events (no controller/door) keep grouping as before."""
        Event = self.env['hr.rfid.event.system']
        first = Event.create({'event_action': '30',
                              'timestamp': self.now - timedelta(seconds=60),
                              'webstack_id': self.webstack.id})
        Event.create({'event_action': '30', 'timestamp': self.now,
                      'webstack_id': self.webstack.id})
        self.assertEqual(self._count('30'), 1)
        self.assertEqual(first.occurrences, 2)

    def test_door_event_not_merged_into_doorless(self):
        """An event WITH a door must not fold into a doorless row (and vice
        versa) - they describe different things."""
        Event = self.env['hr.rfid.event.system']
        Event.create({'event_action': '20',
                      'timestamp': self.now - timedelta(seconds=60),
                      'webstack_id': self.webstack.id,
                      'controller_id': self.ctrl.id})
        self._make(self.now, self.door1, action='20')
        self.assertEqual(self._count('20'), 2)
