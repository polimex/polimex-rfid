# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Regression + edge case tests for overlapping access_group_contact_rel handling.

Bug history: when an old access_group_contact_rel expired exactly as a new one
activated (typical monthly subscription renewal), _deactivate used to wipe the
card.door.rel unconditionally. If _activate ran first via lazy _compute_state
recompute, create_rel hit its idempotency guard and skipped the ADD command —
then _deactivate erased the rel anyway. Result on the controller: card lost
its permission, only a REMOVE D1 was sent, no ADD followed.

These tests cover both the regression scenarios (normal lifecycle stays
intact) and the edge case (overlap rels keep access continuous).
"""
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.tests.common import RFIDAppCase


@tagged('standard', 'at_install', 'rfid', 'rfid_access_group', 'rfid_overlap')
class TestOverlappingAccessGroups(RFIDAppCase):
    """Regression + edge cases for HrRfidAccessGroupContactRel._deactivate/_activate."""

    def setUp(self):
        super().setUp()
        # Build controller + door + reader directly (no F0 handshake — we only
        # need the model relationships for card.door.rel generation, not real
        # hardware emulation).
        ctrl = self.env['hr.rfid.ctrl'].create({
            'name': 'Test Ctrl Overlap',
            'ctrl_id': 99,
            'webstack_id': self.test_webstack_10_3_id.id,
            'hw_version': '12',
            'serial_number': '999',
            'sw_version': '030',
            'mode': 1,
            'inputs': 1,
            'outputs': 1,
            'readers': 1,
        })
        self.test_door = self.env['hr.rfid.door'].create({
            'name': 'Test Door Overlap',
            'number': 1,
            'controller_id': ctrl.id,
            'company_id': self.test_company_id,
        })
        self.env['hr.rfid.reader'].create({
            'name': 'R1',
            'number': 1,
            'reader_type': '0',
            'mode': '01',
            'controller_id': ctrl.id,
            'door_id': self.test_door.id,
        })
        ts = self.env['hr.rfid.time.schedule'].search([('number', '!=', 0)], limit=1)
        self.env['hr.rfid.access.group.door.rel'].create({
            'access_group_id': self.test_ag_partner_1.id,
            'door_id': self.test_door.id,
            'time_schedule_id': ts.id,
        })
        # Per-test reset: drop the access group rel auto-created in common setUp
        # and any door rels for the partner card, plus any pending commands for it.
        self.env['hr.rfid.access.group.contact.rel'].search([
            ('contact_id', '=', self.test_partner.id),
        ]).unlink()
        self.env['hr.rfid.card.door.rel'].search([
            ('card_id', '=', self.test_card_partner.id),
        ]).unlink(create_cmd=False)
        self.env['hr.rfid.command'].search([
            ('card_number', '=', self.test_card_partner.number),
        ]).unlink()
        self.env.flush_all()
        self.env.invalidate_all()
        self.now = fields.Datetime.now()

    # -------- helpers --------
    def _card_state(self):
        card = self.test_card_partner
        cmds_total = self.env['hr.rfid.command'].search_count([
            ('card_number', '=', card.number),
        ])
        cmds_add = self.env['hr.rfid.command'].search_count([
            ('card_number', '=', card.number),
            ('rights_data', '!=', '0'),
        ])
        cmds_remove = self.env['hr.rfid.command'].search_count([
            ('card_number', '=', card.number),
            ('rights_data', '=', '0'),
        ])
        return {
            'door_rels': len(card.door_rel_ids),
            'cmds_total': cmds_total,
            'cmds_add': cmds_add,
            'cmds_remove': cmds_remove,
        }

    def _make_rel(self, activate_on, expiration):
        return self.env['hr.rfid.access.group.contact.rel'].create({
            'access_group_id': self.test_ag_partner_1.id,
            'contact_id': self.test_partner.id,
            'activate_on': activate_on,
            'expiration': expiration,
        })

    # ============================================================
    # REGRESSION — normal flows should still work after fix.
    # ============================================================

    def test_r1_new_rel_activate_creates_door_rel_and_add(self):
        """R1: New rel that activates → 1 door rel + 1 ADD command, no REMOVE."""
        before = self._card_state()
        self._make_rel(self.now - relativedelta(hours=1), self.now + relativedelta(days=30))
        self.env.flush_all()
        after = self._card_state()

        self.assertEqual(after['door_rels'] - before['door_rels'], 1,
                         'Should create exactly one card.door.rel')
        self.assertEqual(after['cmds_add'] - before['cmds_add'], 1,
                         'Should enqueue exactly one ADD command')
        self.assertEqual(after['cmds_remove'] - before['cmds_remove'], 0,
                         'Should not enqueue any REMOVE command')

    def test_r2_lone_rel_expires_removes_door_rel_and_emits_remove(self):
        """R2: Single rel expires → -1 door rel + 1 REMOVE command."""
        rel = self._make_rel(self.now - relativedelta(days=30), self.now + relativedelta(hours=1))
        self.env.flush_all()
        before = self._card_state()

        rel.expiration = self.now - relativedelta(minutes=10)
        rel._compute_state()
        self.env.flush_all()
        after = self._card_state()

        self.assertEqual(after['door_rels'] - before['door_rels'], -1,
                         'card.door.rel should be removed')
        self.assertEqual(after['cmds_remove'] - before['cmds_remove'], 1,
                         'Should enqueue exactly one REMOVE command')
        self.assertEqual(after['cmds_add'] - before['cmds_add'], 0,
                         'Should not enqueue any ADD command')

    def test_r3_card_not_ready_no_rel(self):
        """R3: card.active=False → _activate creates no rel and no commands."""
        self.test_card_partner.active = False
        self.env.flush_all()
        before = self._card_state()

        self._make_rel(self.now - relativedelta(hours=1), self.now + relativedelta(days=30))
        self.env.flush_all()
        after = self._card_state()

        self.assertEqual(after['door_rels'] - before['door_rels'], 0)
        self.assertEqual(after['cmds_total'] - before['cmds_total'], 0)

    def test_r5_rel_unlink_removes_door_rel(self):
        """R5: rel.unlink() → -1 door rel + 1 REMOVE command."""
        rel = self._make_rel(self.now - relativedelta(hours=1), self.now + relativedelta(days=30))
        self.env.flush_all()
        before = self._card_state()

        rel.unlink()
        self.env.flush_all()
        after = self._card_state()

        self.assertEqual(after['door_rels'] - before['door_rels'], -1)
        self.assertEqual(after['cmds_remove'] - before['cmds_remove'], 1)

    def test_r6_card_write_noop_idempotent(self):
        """R6: card.write({deactivate_on: same}) → triggers update_card_rels but no duplicate work."""
        self._make_rel(self.now - relativedelta(hours=1), self.now + relativedelta(days=30))
        self.env.flush_all()
        before = self._card_state()

        # No-op write — same value, but vals.keys() includes 'deactivate_on' → triggers update_card_rels
        self.test_card_partner.write({'deactivate_on': self.test_card_partner.deactivate_on})
        self.env.flush_all()
        after = self._card_state()

        self.assertEqual(after['door_rels'], before['door_rels'],
                         'door_rels should remain stable')
        self.assertEqual(after['cmds_total'], before['cmds_total'],
                         'no duplicate commands should be enqueued')

    # ============================================================
    # EDGE CASES — overlap rels (the bug scenarios)
    # ============================================================

    def test_e1_activate_before_deactivate_preserves_access(self):
        """E1 (THE BUG): _activate called BEFORE _deactivate (lazy recompute order).

        Without fix: card.door.rel wiped + only REMOVE enqueued (production bug).
        With fix:    card.door.rel preserved + 0 churn (continuous access).
        """
        # Old rel — currently active. Use SQL to bypass overlap constraint when we
        # later move dates around.
        old_rel = self._make_rel(self.now - relativedelta(days=30), self.now + relativedelta(hours=1))
        self.env.flush_all()
        self.assertGreaterEqual(len(self.test_card_partner.door_rel_ids), 1,
                                'old rel should have created the door rel')

        # New rel — created as future via direct SQL to skip overlap constraint
        new_rel_id = self._raw_insert_rel(
            self.now + relativedelta(hours=2),
            self.now + relativedelta(days=30),
            state=False,
        )

        # Simulate the cron-time transition: bump dates so old rel just expired
        # and new rel just activated. State fields kept manually to mirror prod.
        self.env.cr.execute("""
            UPDATE hr_rfid_access_group_contact_rel
            SET expiration=%s, state=true, internal_state=true
            WHERE id=%s
        """, (self.now - relativedelta(minutes=5), old_rel.id))
        self.env.cr.execute("""
            UPDATE hr_rfid_access_group_contact_rel
            SET activate_on=%s
            WHERE id=%s
        """, (self.now - relativedelta(minutes=3), new_rel_id))
        self.env.cr.flush()
        self.env.invalidate_all()

        before = self._card_state()
        new_rel = self.env['hr.rfid.access.group.contact.rel'].browse(new_rel_id)
        old_rel = self.env['hr.rfid.access.group.contact.rel'].browse(old_rel.id)

        # CRITICAL: _activate the new one FIRST (the bug scenario)
        new_rel._compute_state()
        self.env.flush_all()
        # Then _deactivate the old one
        old_rel._compute_state()
        self.env.flush_all()

        after = self._card_state()

        # With fix: door rel preserved, zero command churn (continuous access)
        self.assertEqual(after['door_rels'], before['door_rels'],
                         'card.door.rel must be preserved across overlap transition')
        self.assertEqual(after['cmds_total'], before['cmds_total'],
                         'no commands should be enqueued for a continuous overlap')

    def test_e2_deactivate_before_activate_preserves_access(self):
        """E2: _deactivate called BEFORE _activate (normal cron order)."""
        old_rel = self._make_rel(self.now - relativedelta(days=30), self.now + relativedelta(hours=1))
        self.env.flush_all()

        new_rel_id = self._raw_insert_rel(
            self.now + relativedelta(hours=2),
            self.now + relativedelta(days=30),
            state=False,
        )

        self.env.cr.execute("""
            UPDATE hr_rfid_access_group_contact_rel
            SET expiration=%s, state=true, internal_state=true
            WHERE id=%s
        """, (self.now - relativedelta(minutes=5), old_rel.id))
        self.env.cr.execute("""
            UPDATE hr_rfid_access_group_contact_rel
            SET activate_on=%s
            WHERE id=%s
        """, (self.now - relativedelta(minutes=3), new_rel_id))
        self.env.cr.flush()
        self.env.invalidate_all()

        before = self._card_state()
        new_rel = self.env['hr.rfid.access.group.contact.rel'].browse(new_rel_id)
        old_rel = self.env['hr.rfid.access.group.contact.rel'].browse(old_rel.id)

        # Normal order: _deactivate first, then _activate
        old_rel._compute_state()
        self.env.flush_all()
        new_rel._compute_state()
        self.env.flush_all()

        after = self._card_state()
        self.assertEqual(after['door_rels'], before['door_rels'],
                         'card.door.rel must be preserved')

    # -------- helper --------
    def _raw_insert_rel(self, activate_on, expiration, state):
        """Insert a contact rel bypassing the overlap @api.constrains check (we want overlap)."""
        self.env.cr.execute("""
            INSERT INTO hr_rfid_access_group_contact_rel
                (access_group_id, contact_id, activate_on, expiration,
                 state, internal_state, visits_counting, permitted_visits, visits_counter,
                 create_uid, write_uid, create_date, write_date)
            VALUES (%s, %s, %s, %s, %s, %s, false, 0, 0,
                    %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            self.test_ag_partner_1.id, self.test_partner.id,
            activate_on, expiration, state, state,
            self.env.uid, self.env.uid,
        ))
        return self.env.cr.fetchone()[0]
