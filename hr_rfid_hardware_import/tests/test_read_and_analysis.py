"""Narratives 1 (reading), 7 (mixed hardware), 9 (resume) and the group analysis.

Owner: "Зарежда се списъкът на всички контролери от всеки един модул с неговото
състояние ... Изключват се вендинг контролерите"; "минимален брой групи".
"""
import json

from odoo.tests import tagged

from odoo.addons.hr_rfid_hardware_import.helpers import allowlist
from odoo.addons.hr_rfid_hardware_import.models import hw_import_run

from .common import HwImportCase, ADDR_180, ADDR_110, ADDR_VEND, ADDR_RELAY, ADDR_TEMP, ADDR_FIRE, ADDR_115


@tagged('post_install', '-at_install', 'rfid_hw_import', 'rfid_hw_import_read')
class TestReadAndAnalysis(HwImportCase):

    def test_every_controller_is_read_with_read_commands_only(self):
        run = self._survey()
        self.assertEqual(run.state, 'naming')
        opcodes = {c[3] for c in self.backend.commands_sent()}
        self.assertTrue(opcodes <= allowlist.READ_OPCODES | {'B0'}, opcodes)
        b0 = [c for c in self.backend.commands_sent() if c[3] == 'B0']
        self.assertTrue(all(c[4] == '01' for c in b0), "the alarm setup is only ever read")
        self.assertEqual(set(run.cmd_log_ids.mapped('opcode')), opcodes)
        self.assertFalse(self._write_commands())

    def test_the_survey_knows_each_controller_and_what_it_holds(self):
        run = self._survey()
        by_addr = {(c.module_id.ip, c.address): c for c in run.ctrl_ids}
        c180 = by_addr[('192.0.2.10', ADDR_180)]
        self.assertEqual((c180.family, c180.serial, c180.mode, c180.readers, c180.alarm_lines),
                         ('access', '1801', 2, 4, 4))
        self.assertEqual(c180.record_size, 20)
        self.assertEqual(c180.card_count_device, 6)
        self.assertEqual(c180.cards_read, 6)
        self.assertEqual(c180.read_state, 'done')
        self.assertEqual(json.loads(c180.door_map_json), {'1': [1, 2], '2': [3, 4]})
        self.assertEqual(c180.apb_bitmap, 1)
        self.assertEqual(json.loads(c180.alarm_setup_json)['zones_enabled'], 3)
        self.assertEqual(len(c180.ts_ids), 15, 'every slot is read')
        self.assertEqual(len(c180.ts_ids.filtered(lambda t: not t.is_empty)), 2)
        c110 = by_addr[('192.0.2.10', ADDR_110)]
        self.assertEqual((c110.family, c110.record_size, c110.cards_read), ('access', 19, 5))
        self.assertEqual(len(run.card_ids), 9, "one card number, however many controllers hold it")
        self.assertEqual(len(self._card(run, '0000100001').record_ids), 3)

    def test_vending_machines_are_listed_but_never_read_for_cards(self):
        run = self._survey(with_b=False)
        vend = run.ctrl_ids.filtered(lambda c: c.address == ADDR_VEND)
        self.assertEqual(vend.family, 'vending')
        self.assertFalse(vend.include)
        self.assertEqual(vend.read_state, 'skipped')
        sent_to_vend = [c for c in self.backend.commands_sent() if c[2] == ADDR_VEND]
        self.assertEqual([c[3] for c in sent_to_vend], ['F0'])
        self.assertFalse(self._card(run, '0000100099'), "the vending card table is not part of the survey")

    def test_other_families_are_read_for_settings_only_and_gaps_are_recorded(self):
        run = self._survey()
        relay = run.ctrl_ids.filtered(lambda c: c.address == ADDR_RELAY)
        temp = run.ctrl_ids.filtered(lambda c: c.address == ADDR_TEMP)
        fire = run.ctrl_ids.filtered(lambda c: c.address == ADDR_FIRE)
        for ctrl in (relay, temp, fire):
            self.assertEqual(ctrl.read_state, 'done', ctrl.name)
            self.assertFalse(ctrl.reads_cards)
            sent = [c[3] for c in self.backend.commands_sent() if c[2] == ctrl.address]
            self.assertNotIn('F2', sent, ctrl.name)
        self.assertIn('F3', json.loads(relay.gaps_json))
        self.assertIn('FF', json.loads(fire.gaps_json))
        self.assertNotIn(('CMD', '192.0.2.20', ADDR_FIRE, 'F6', ''), self.backend.commands_sent(), 'no readers, no reader-mode read')
        gaps = run.issue_ids.filtered(lambda i: i.kind == 'gap')
        self.assertEqual(set(gaps.mapped('ctrl_id')), set(relay + temp + fire))
        self.assertTrue(all(i.severity == 'info' for i in gaps), "a gap is not a failure")

    def test_a_reading_that_runs_out_of_time_resumes_where_it_stopped(self):
        run = self._new_run()
        run.action_discover()
        self._work(run)
        run.action_read()
        original = hw_import_run.PASS_SECONDS
        hw_import_run.PASS_SECONDS = 0.0
        try:
            passes = self._work(run)
        finally:
            hw_import_run.PASS_SECONDS = original
        self.assertGreater(passes, 3, "several passes were needed")
        self.assertEqual(run.state, 'naming')
        c180 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_180)
        self.assertEqual((c180.cards_read, c180.read_cursor), (6, -1))
        f2_pages = [c for c in self.backend.commands_sent() if c[2] == ADDR_180 and c[3] == 'F2' and c[4] != '0000000000']
        self.assertEqual(len(f2_pages), 2, "the six cards were read in two pages, none twice")

    def test_rights_and_the_minimum_number_of_groups(self):
        run = self._survey()
        card1 = self._card(run, '0000100001')
        rights = json.loads(card1.door_rights_json)
        self.assertEqual(len(rights), 3)
        self.assertTrue(any(r['alarm'] and r['ts'] == 1 for r in rights))
        card6 = self._card(run, '0000100006')
        self.assertEqual(card6.anomaly, 'reader_ts_mismatch')
        card7 = self._card(run, '0000100007')
        self.assertEqual(card7.anomaly, 'partial_reader')
        card2 = self._card(run, '0000100002')
        self.assertEqual(card2.anomaly, 'pin_mismatch')
        self.assertEqual(card2.pin, '')
        # Every right belongs to exactly one group; a right's group holds exactly the cards holding it.
        rights_seen = {}
        for group in run.group_ids:
            for right in group.right_ids:
                key = (right.ctrl_id.id, right.door_number, right.ts_number, right.alarm)
                self.assertNotIn(key, rights_seen, "a right in two groups")
                rights_seen[key] = group
        for card in run.card_ids:
            for right in json.loads(card.door_rights_json):
                group = rights_seen[(right['ctrl'], right['door'], right['ts'], bool(right['alarm']))]
                self.assertIn(card, group.card_ids)
        shared = run.group_ids.filtered(lambda g: '0000100005' in g.card_ids.mapped('number')
                                        and '0000100001' in g.card_ids.mapped('number'))
        self.assertEqual(len(shared), 1, "cards 1 and 5 share exactly one right set on the iCON180")
        self.assertEqual(shared.door_count, 1)
        self.assertEqual(len(run.group_ids), 8)
        self.assertEqual(run.group_ids[0].sequence, 1)

    def test_schedule_slots_are_compared_across_controllers(self):
        run = self._survey()
        slots = {s.number: s for s in run.ts_slot_ids}
        self.assertEqual(slots[1].state, 'ok')
        self.assertEqual(slots[1].variant_count, 1)
        self.assertEqual(slots[2].state, 'conflict')
        self.assertEqual(slots[2].variant_count, 2)
        self.assertEqual(slots[3].state, 'ok')
        self.assertTrue(run.has_blockers, "the conflicting slot blocks the schedule import")

    def test_placeholder_owners_are_generated_for_every_card(self):
        run = self._survey()
        self.assertEqual(len(run.person_ids), len(run.card_ids))
        self.assertTrue(all(p.source == 'placeholder' for p in run.person_ids))
        self.assertTrue(all(p.owner_type == 'contact' for p in run.person_ids))
        self.assertIn('0000100001', self._card(run, '0000100001').person_id.name)
