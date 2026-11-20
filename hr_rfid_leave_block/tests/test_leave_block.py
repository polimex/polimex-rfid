# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
"""The cards of a person on time off stop while the time off goes on.

They stop when the leave begins - not when it is approved: a leave approved
today for next month leaves the person working until then. They come back
when the leave is over, refused or cancelled. Exactly the cards that were
working are stopped and given back: one the person had switched off before
stays off.
"""

import importlib.util
from datetime import date, timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_path

# Tuesday 1 December 2026, 12:00 in Sofia: a working day in progress.
NOW = "2026-12-01 10:00:00"
TODAY = date(2026, 12, 1)


@tagged("post_install", "-at_install", "rfid_leave_block")
class TestRfidLeaveBlock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Leave Block Guard",
                "company_id": cls.company.id,
                "tz": "Europe/Sofia",
            }
        )
        cls.card_type = cls.env.ref("hr_rfid.hr_rfid_card_type_def")
        # A type without allocation is the simplest to approve in a test.
        cls.leave_type = cls.env["hr.leave.type"].search(
            [("requires_allocation", "=", False)], limit=1
        )
        cls.Card = cls.env["hr.rfid.card"]
        cls.Block = cls.env["hr.rfid.leave.block"]

    def _card(self, number, active=True):
        return self.Card.create(
            {
                "number": number,
                "card_type": self.card_type.id,
                "employee_id": self.employee.id,
                "company_id": self.company.id,
                "active": active,
            }
        )

    def _leave(self, days_from_today=0, length=3):
        start = TODAY + timedelta(days=days_from_today)
        return self.env["hr.leave"].create(
            {
                "employee_id": self.employee.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": start,
                "request_date_to": start + timedelta(days=length),
            }
        )

    def _approve(self, leave):
        leave.write({"state": "validate"})

    @freeze_time(NOW)
    def test_a_leave_next_month_leaves_the_cards_working_today(self):
        card = self._card("0000000071")
        leave = self._leave(days_from_today=30)
        self._approve(leave)

        self.assertTrue(card.active)
        self.assertFalse(leave.rfid_block_ids)
        self.Block._cron_follow_the_leaves()
        self.assertTrue(card.active, "the leave has not begun")

    def test_the_cards_stop_when_the_leave_begins(self):
        card = self._card("0000000072")
        with freeze_time(NOW):
            leave = self._leave(days_from_today=7)
            self._approve(leave)
        with freeze_time(leave.date_from + timedelta(minutes=10)):
            self.Block._cron_follow_the_leaves()

        self.assertFalse(card.active)
        self.assertEqual(leave.rfid_block_ids.state, "active")
        self.assertEqual(leave.rfid_block_ids.blocked_card_ids, card)

    @freeze_time(NOW)
    def test_a_leave_already_begun_stops_the_cards_at_once(self):
        """Headline: 2 working cards and 1 switched off - only the 2 stop."""
        c1 = self._card("0000000001")
        c2 = self._card("0000000002")
        c3 = self._card("0000000003", active=False)
        leave = self._leave()
        self.assertLessEqual(leave.date_from, fields.Datetime.now())
        self._approve(leave)

        block = leave.rfid_block_ids
        self.assertEqual(len(block), 1)
        self.assertEqual(block.state, "active")
        self.assertEqual(block.blocked_card_ids, c1 | c2)
        self.assertFalse(c1.active)
        self.assertFalse(c2.active)
        self.assertFalse(c3.active)

    def test_the_cards_come_back_when_the_leave_is_over(self):
        card = self._card("0000000041")
        with freeze_time(NOW):
            leave = self._leave()
            self._approve(leave)
            self.assertFalse(card.active)
            self.Block._cron_follow_the_leaves()
            self.assertFalse(card.active, "the leave goes on")
        with freeze_time(leave.date_to + timedelta(minutes=10)):
            self.Block._cron_follow_the_leaves()

        self.assertTrue(card.active)
        self.assertEqual(leave.rfid_block_ids.state, "restored")

    @freeze_time(NOW)
    def test_a_leave_approved_after_it_ended_stops_nothing(self):
        card = self._card("0000000042")
        leave = self._leave(days_from_today=-10, length=3)
        self._approve(leave)
        self.Block._cron_follow_the_leaves()

        self.assertTrue(card.active)
        self.assertFalse(leave.rfid_block_ids)

    @freeze_time(NOW)
    def test_refused_gives_back_only_the_cards_it_stopped(self):
        c1 = self._card("0000000011")
        c2 = self._card("0000000012")
        c3 = self._card("0000000013", active=False)
        leave = self._leave()
        self._approve(leave)
        leave.write({"state": "refuse"})

        self.assertEqual(leave.rfid_block_ids.state, "restored")
        self.assertTrue(c1.active)
        self.assertTrue(c2.active)
        self.assertFalse(c3.active)

    @freeze_time(NOW)
    def test_cancel_restores_access(self):
        card = self._card("0000000021")
        leave = self._leave()
        self._approve(leave)
        self.assertFalse(card.active)
        leave.write({"state": "cancel"})
        self.assertTrue(card.active)

    def test_a_leave_cancelled_before_it_began_never_stops_the_cards(self):
        card = self._card("0000000022")
        with freeze_time(NOW):
            leave = self._leave(days_from_today=7)
            self._approve(leave)
            leave.write({"state": "cancel"})
        with freeze_time(leave.date_from + timedelta(minutes=10)):
            self.Block._cron_follow_the_leaves()

        self.assertTrue(card.active)
        self.assertFalse(leave.rfid_block_ids)

    @freeze_time(NOW)
    def test_idempotent_revalidate(self):
        """Approving again does not stop the cards twice."""
        card = self._card("0000000031")
        leave = self._leave()
        self._approve(leave)
        leave.write({"state": "confirm"})
        card.active = True
        self._card("0000000032")
        self._approve(leave)
        self.Block._cron_follow_the_leaves()
        active_blocks = leave.rfid_block_ids.filtered(lambda b: b.state == "active")
        self.assertEqual(len(active_blocks), 1)

    @freeze_time(NOW)
    def test_no_active_cards_no_block(self):
        self._card("0000000051", active=False)
        leave = self._leave()
        self._approve(leave)
        self.assertFalse(leave.rfid_block_ids)

    @freeze_time(NOW)
    def test_cards_stopped_ahead_of_time_are_given_back_on_upgrade(self):
        """Before this version approval stopped the cards at once; the upgrade
        gives back the cards of a leave that has not begun."""
        card = self._card("0000000081")
        leave = self._leave(days_from_today=7)
        self._approve(leave)
        self.Block.create(
            {"leave_id": leave.id, "blocked_card_ids": [(6, 0, card.ids)]}
        )
        card.active = False
        cron = self.env.ref("hr_rfid_leave_block.ir_cron_restore_expired_leave_blocks")
        cron.write(
            {
                "code": "model._cron_restore_expired_blocks()",
                "interval_number": 1,
                "interval_type": "days",
            }
        )
        path = file_path("hr_rfid_leave_block/migrations/19.0.1.0.2/post-migrate.py")
        spec = importlib.util.spec_from_file_location("leave_block_upgrade", path)
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)

        script.migrate(self.env.cr, "19.0.1.0.1")

        self.assertTrue(card.active)
        self.assertEqual(leave.rfid_block_ids.state, "restored")
        self.assertEqual(cron.code, "model._cron_follow_the_leaves()")
        self.assertEqual((cron.interval_number, cron.interval_type), (15, "minutes"))
        self.assertEqual(cron.name, "RFID: Follow time off (stop and give back access)")

    @freeze_time(NOW)
    def test_gc_restored_blocks(self):
        """Autovacuum drops old restored rows, keeps fresh and active ones."""
        self._card("0000000061")
        leave = self._leave()
        self._approve(leave)
        leave.write({"state": "refuse"})
        block = leave.rfid_block_ids
        block.write(
            {"restored_at": fields.Datetime.subtract(fields.Datetime.now(), days=400)}
        )
        done, has_more = self.Block._gc_restored_blocks()
        self.assertGreaterEqual(done, 1)
        self.assertFalse(has_more)
