# -*- coding: utf-8 -*-
"""Regression tests for improvements back-ported from 19.0 to rfid_pms_base.

Run:  odoo-bin -u rfid_pms_base --test-enable --test-tags pms_base_backport
"""
from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install', 'pms_base_backport')
class PmsBaseBackportRegressions(TransactionCase):

    # ---- 572b170: room-number range check actually rejects bad values ------
    def test_room_number_range_check(self):
        """The old constraint was `0 > number > 65535` (a chained comparison
        that is ALWAYS False), so it never rejected anything. It must now reject
        numbers outside 1..65535 and accept those inside."""
        Room = self.env['rfid_pms_base.room']
        door = self.env['hr.rfid.door'].search([], limit=1)
        ag = self.env['hr.rfid.access.group'].search([], limit=1)
        if not door or not ag:
            self.skipTest('no hr.rfid.door / access.group fixture available to attach a room to')
        base = {'name': 'BP Room', 'door_id': door.id, 'access_group_id': ag.id}
        # a valid number is accepted
        room = Room.create(dict(base, number=100))
        self.assertEqual(room.number, 100)
        # out-of-range numbers are rejected (old constraint 0 > n > 65535 never fired)
        with self.assertRaises(ValidationError):
            Room.create(dict(base, name='BP Bad Room', number=99999))
        with self.assertRaises(ValidationError):
            Room.create(dict(base, name='BP Zero Room', number=0))

    # ---- 24d8e67: Schneider dead code dropped -------------------------------
    def test_schneider_dead_model_removed(self):
        self.assertNotIn('rfid_pms_base.message_wiz', self.env,
                         'the Schneider message_wiz dead model must be gone')
