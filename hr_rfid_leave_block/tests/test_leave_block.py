# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
from datetime import date, timedelta

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'rfid_leave_block')
class TestRfidLeaveBlock(TransactionCase):
    """Suspend/restore of RFID cards across the leave lifecycle.

    The headline case (the one the user flagged): an employee with 3 cards —
    2 active, 1 already disabled before the leave — must have only the 2 active
    ones suspended and, on restore, only those 2 re-activated. The third stays
    off.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Leave Block Guard', 'company_id': cls.company.id})
        cls.card_type = cls.env.ref('hr_rfid.hr_rfid_card_type_def')
        # Unpaid leave type needs no allocation — simplest to approve in a test.
        cls.leave_type = cls.env['hr.leave.type'].search(
            [('requires_allocation', '=', False)], limit=1)
        cls.Card = cls.env['hr.rfid.card']
        cls.Block = cls.env['hr.rfid.leave.block']

    def _card(self, number, active=True):
        return self.Card.create({
            'number': number, 'card_type': self.card_type.id,
            'employee_id': self.employee.id, 'company_id': self.company.id,
            'active': active,
        })

    def _leave(self, days_from_today=1, length=3):
        start = date.today() + timedelta(days=days_from_today)
        return self.env['hr.leave'].create({
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': start,
            'request_date_to': start + timedelta(days=length),
        })

    def test_validate_blocks_active_cards_only(self):
        """Headline: 2 active + 1 inactive → only the 2 active are suspended."""
        c1 = self._card('0000000001', active=True)
        c2 = self._card('0000000002', active=True)
        c3 = self._card('0000000003', active=False)
        leave = self._leave()
        leave.write({'state': 'validate'})

        block = leave.rfid_block_ids
        self.assertEqual(len(block), 1)
        self.assertEqual(block.state, 'active')
        self.assertEqual(set(block.blocked_card_ids.ids), {c1.id, c2.id})
        self.assertFalse(c1.active)
        self.assertFalse(c2.active)
        self.assertFalse(c3.active)  # was already off, untouched

    def test_restore_reactivates_only_snapshot(self):
        """On restore, only the snapshotted cards come back — not the third."""
        c1 = self._card('0000000011', active=True)
        c2 = self._card('0000000012', active=True)
        c3 = self._card('0000000013', active=False)
        leave = self._leave()
        leave.write({'state': 'validate'})
        leave.write({'state': 'refuse'})

        self.assertEqual(leave.rfid_block_ids.state, 'restored')
        self.assertTrue(c1.active)
        self.assertTrue(c2.active)
        self.assertFalse(c3.active)  # stays off — not in snapshot

    def test_cancel_restores_access(self):
        c1 = self._card('0000000021', active=True)
        leave = self._leave()
        leave.write({'state': 'validate'})
        self.assertFalse(c1.active)
        leave.write({'state': 'cancel'})
        self.assertTrue(c1.active)

    def test_idempotent_revalidate(self):
        """Re-approving must not create a second block or re-snapshot."""
        c1 = self._card('0000000031', active=True)
        leave = self._leave()
        leave.write({'state': 'validate'})
        leave.write({'state': 'confirm'})   # restores
        # manually re-enable + add a card, then re-validate
        c1.active = True
        c2 = self._card('0000000032', active=True)
        leave.write({'state': 'validate'})
        active_blocks = leave.rfid_block_ids.filtered(lambda b: b.state == 'active')
        self.assertEqual(len(active_blocks), 1)

    def test_cron_restores_expired(self):
        """Cron restores access for a leave whose end date has passed."""
        c1 = self._card('0000000041', active=True)
        # leave entirely in the past
        leave = self._leave(days_from_today=-10, length=3)
        leave.write({'state': 'validate'})
        self.assertFalse(c1.active)
        self.Block._cron_restore_expired_blocks()
        self.assertTrue(c1.active)
        self.assertEqual(leave.rfid_block_ids.state, 'restored')

    def test_no_active_cards_no_block(self):
        """Employee with no active cards → no block row created."""
        self._card('0000000051', active=False)
        leave = self._leave()
        leave.write({'state': 'validate'})
        self.assertFalse(leave.rfid_block_ids)

    def test_gc_restored_blocks(self):
        """Autovacuum drops old restored rows, keeps fresh + active ones."""
        c1 = self._card('0000000061', active=True)
        leave = self._leave()
        leave.write({'state': 'validate'})
        leave.write({'state': 'refuse'})
        block = leave.rfid_block_ids
        # Age it past the retention window (ORM write — readonly is UI-only).
        from odoo import fields
        block.write({'restored_at': fields.Datetime.subtract(
            fields.Datetime.now(), days=400)})
        done, has_more = self.Block._gc_restored_blocks()
        self.assertGreaterEqual(done, 1)
        self.assertFalse(has_more)
        self.assertFalse(block.exists())
