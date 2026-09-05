"""Narratives 3, 4, 5, 6, 8 and the end of narrative 1: names, decisions, import.

Owner: "csv/excel с 2 колони име и номер на карта"; "служебни имена"; "внос
като служители и/или партньори"; "командите към контролерите са строго само за
четене"; hardware import "без да се загуби работоспособността".
"""
import base64
import json

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.hr_rfid_hardware_import.helpers import allowlist, codecs
from odoo.addons.hr_rfid_hardware_import.models import importer as importer_module

from .common import (HwImportCase, ADDR_180, ADDR_FIRE, ADDR_110, ADDR_115, MODULE_A_SERIAL, MODULE_A_IP,
                     MODULE_B_IP, ts_reply)


@tagged('post_install', '-at_install', 'rfid_hw_import', 'rfid_hw_import_import')
class TestNamesAndImport(HwImportCase):

    def _resolved_survey(self, upload=True):
        run = self._survey()
        if upload:
            self._upload_names(run)
        slot2 = run.ts_slot_ids.filtered(lambda s: s.number == 2)
        slot2.source_ctrl_id = run.ctrl_ids.filtered(lambda c: c.address == ADDR_180)
        blocked = run.person_ids.filtered(lambda p: p.review_state == 'blocked')
        blocked.action_split()
        run.invalidate_recordset()
        if run.state == 'naming':
            run.action_to_grouping() if run.name_line_ids else run.action_skip_names()
        return run

    def test_the_names_file_matches_cards_by_number_only(self):
        run = self._survey()
        self._upload_names(run)
        by_status = {}
        for line in run.name_line_ids:
            by_status.setdefault(line.status, []).append(line)
        self.assertEqual(len(by_status['matched']), 4)
        self.assertEqual(len(by_status['unmatched']), 1)
        self.assertEqual(len(by_status['duplicate']), 1)
        self.assertEqual(len(by_status['invalid']), 1)
        one = self._person(run, 'Demo Holder One')
        self.assertEqual(len(one), 1)
        self.assertEqual(set(one.card_ids.mapped('number')), {'0000100001', '0000100005'})
        self.assertTrue(one.merged)
        self.assertEqual(one.review_state, 'blocked', "the two cards open one door on different schedules")
        two = self._person(run, 'Demo Holder Two')
        self.assertEqual(two.card_ids.number, '0000100002', "a short number is padded before matching")
        self.assertEqual(self._card(run, '0000100004').person_id.source, 'placeholder')
        self.assertFalse(self._person(run, 'Ghost Holder'), "a name without a surveyed card creates nobody")

    def test_a_merged_person_can_be_split_back(self):
        run = self._survey()
        self._upload_names(run)
        one = self._person(run, 'Demo Holder One')
        one.action_split()
        people = self._person(run, 'Demo Holder One')
        self.assertEqual(len(people), 2)
        self.assertTrue(all(len(p.card_ids) == 1 for p in people))
        self.assertTrue(all(p.review_state == 'ok' for p in people))
        self.assertEqual(len(run.name_line_ids.filtered(lambda l: l.person_id in people)), 2)

    def test_an_excel_file_is_read_like_a_csv(self):
        import io
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['Име', 'Карта'])
        ws.append(['Excel Holder', 100003])
        buffer = io.BytesIO()
        wb.save(buffer)
        run = self._survey()
        wiz = self.env['hr.rfid.hw.import.names.wiz'].create({
            'run_id': run.id, 'file': base64.b64encode(buffer.getvalue()), 'file_name': 'names.xlsx'})
        wiz.action_load()
        self.assertEqual(self._card(run, '0000100003').person_id.name, 'Excel Holder')

    def test_the_import_creates_everything_with_zero_write_commands(self):
        run = self._resolved_survey()
        self.assertFalse(run.has_blockers, run.issue_ids.filtered(lambda i: not i.resolved).mapped('message'))
        self._import(run)
        self.assertEqual(run.state, 'done', run.last_error)
        self.assertFalse(self._write_commands(), self._write_commands().mapped('cmd'))
        webstacks = run.module_ids.mapped('webstack_id')
        self.assertEqual(len(webstacks), 2)
        self.assertTrue(all(not ws.active for ws in webstacks), "imported modules stay switched off")
        self.assertEqual(webstacks.filtered(lambda w: w.serial == MODULE_A_SERIAL).last_ip, '192.0.2.10')
        c180 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_180).ctrl_rec_id
        self.assertEqual((c180.hw_version, c180.serial_number, c180.mode, c180.readers), ('10', '1801', 2, 4))
        self.assertEqual(len(c180.door_ids), 2)
        self.assertEqual(len(c180.reader_ids), 4)
        self.assertEqual(len(c180.alarm_line_ids), 4)
        self.assertTrue(c180.door_ids.filtered(lambda d: d.number == 1).apb_mode)
        self.assertEqual(c180.alarm_lines_setup, '000003')
        fire = run.ctrl_ids.filtered(lambda c: c.address == ADDR_FIRE)
        self.assertTrue(fire.ctrl_rec_id)
        self.assertTrue(fire.imported_without_doors)
        self.assertFalse(fire.ctrl_rec_id.door_ids)
        self.assertFalse(run.ctrl_ids.filtered(lambda c: c.family == 'vending').ctrl_rec_id)
        ts1 = self.env['hr.rfid.time.schedule'].search([('company_id', '=', self.company.id), ('number', '=', 1)])
        self.assertFalse(ts1.is_empty)
        self.assertEqual(ts1._get_interval_from_day_tuple(0, 0), (8.0, 18.0))
        self.assertIn(c180, ts1.controller_ids, "the controller already holds this schedule")
        ts2 = self.env['hr.rfid.time.schedule'].search([('company_id', '=', self.company.id), ('number', '=', 2)])
        self.assertEqual(ts2._get_interval_from_day_tuple(5, 0), (7.0, 20.0), "slot 2 came from the chosen controller")
        c110 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_110).ctrl_rec_id
        self.assertNotIn(c110, ts2.controller_ids, "the other controller holds a different slot 2")
        self.assertTrue(all(c.card_rec_id for c in run.card_ids), "every card was created")
        card3 = self._card(run, '0000100003').card_rec_id
        rels = {(r.door_id.controller_id.ctrl_id, r.door_id.number, r.time_schedule_id.number, r.alarm_right)
                for r in card3.door_rel_ids}
        self.assertEqual(rels, {(ADDR_180, 1, 1, False), (ADDR_180, 2, 2, False)},
                         "the database mirrors the controller's card record")
        card2 = self._card(run, '0000100002')
        self.assertEqual(card2.card_rec_id.contact_id.hr_rfid_pin_code, '0000', "conflicting PINs import none")
        self.assertTrue(run.group_ids.mapped('access_group_id'))
        self.assertTrue(run.issue_ids.filtered(lambda i: i.kind == 'report' and 'No command' in i.message))

    def test_employees_need_a_department_and_get_it(self):
        run = self._resolved_survey()
        three = self._person(run, 'Demo Holder Three')
        three.owner_type = 'employee'
        run.write({'default_department_id': False})
        with self.assertRaises(UserError):
            run.action_start_import()
        run.write({'default_department_id': self.department.id})
        self._import(run)
        self.assertEqual(run.state, 'done', run.last_error)
        self.assertEqual(three.employee_id.department_id, self.department)
        self.assertTrue(three.employee_id.hr_rfid_access_group_ids)
        self.assertFalse(self._write_commands())

    COUNTED_MODELS = ('hr.rfid.webstack', 'hr.rfid.ctrl', 'hr.rfid.door', 'hr.rfid.reader', 'hr.rfid.card',
                      'hr.rfid.access.group', 'hr.rfid.access.group.door.rel', 'hr.rfid.access.group.contact.rel',
                      'hr.rfid.access.group.employee.rel', 'hr.rfid.card.door.rel', 'res.partner', 'hr.employee')

    def _counts(self):
        return {model: self.env[model].sudo().with_context(active_test=False).search_count([])
                for model in self.COUNTED_MODELS}

    def test_a_second_survey_of_the_same_site_creates_nothing_twice(self):
        """The site was surveyed with a names file; months later it is surveyed
        again, this time without one. The people of the first survey are the
        owners of the cards - no twin contacts, no second group, no extra right."""
        run = self._resolved_survey()
        self._import(run)
        counts = self._counts()
        self.backend.calls.clear()
        again = self._survey(include_known=True)
        self.assertEqual(set(again.module_ids.mapped('status')), {'known'})
        self.assertTrue(again.issue_ids.filtered(lambda i: i.kind == 'conflict_card'))
        for issue in again.issue_ids.filtered(lambda i: i.severity == 'blocker'):
            issue.resolution = 'link'
        again.ts_slot_ids.filtered(lambda s: s.number == 2).source_ctrl_id = again.ctrl_ids.filtered(
            lambda c: c.address == ADDR_180)
        again.person_ids.filtered(lambda p: p.review_state == 'blocked').action_split()
        again.action_skip_names()
        self._import(again)
        self.assertEqual(again.state, 'done', again.last_error)
        self.assertEqual(self._counts(), counts)
        one = self._person(run, 'Demo Holder One')[:1]
        self.assertEqual(self._card(again, '0000100001').person_id.partner_id, one.partner_id,
                         "the generated holder of the second survey is the person named in the first")
        self.assertFalse(self._write_commands())

    def test_every_part_can_be_left_out(self):
        run = self._resolved_survey(upload=False)
        self._import(run, import_people=False, import_cards=False, import_groups=False, import_schedules=False)
        self.assertEqual(run.state, 'done', run.last_error)
        self.assertTrue(run.module_ids.mapped('webstack_id'))
        self.assertFalse(run.card_ids.mapped('card_rec_id'))
        self.assertFalse(run.person_ids.mapped('partner_id'))
        left_out = run.issue_ids.filtered(lambda i: 'left out on request' in i.message)
        self.assertEqual(len(left_out), 4)

    def test_pointing_a_module_is_a_separate_explicit_action_through_the_core(self):
        run = self._resolved_survey(upload=False)
        self._import(run)
        module = run.module_ids.filtered(lambda m: m.serial == MODULE_A_SERIAL)
        calls = []

        def fake_settings(webstack):
            calls.append(webstack.serial)
            return True
        self.patch(type(module.webstack_id), 'action_set_webstack_settings', fake_settings)
        self.assertFalse(module.pointed_at)
        module.action_point_to_server()
        self.assertEqual(calls, [MODULE_A_SERIAL])
        self.assertTrue(module.pointed_at)
        self.assertFalse(module.webstack_id.active, "pointing does not enable; that is the next button")
        module.action_enable_module()
        self.assertTrue(module.webstack_id.active)
        self.assertFalse(self._write_commands())

    def test_the_report_can_be_downloaded(self):
        run = self._resolved_survey(upload=False)
        self._import(run)
        action = run.action_download_report()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        text = run._report_text()
        self.assertIn('Modules: 2', text)
        self.assertIn('No command was sent', text)

    # ------------------------------------------------------------ the zero-write promise, on a live company

    def test_hardware_already_running_here_is_untouched_and_the_controllers_schedule_wins(self):
        """Decision 11: the company's schedule is overwritten by what the
        controllers hold, the company's own controllers that now differ are
        listed in the report - and nothing at all is queued for the live module."""
        ctx = importer_module.IMPORT_CONTEXT
        live_ws = self.env['hr.rfid.webstack'].sudo().with_context(**ctx).create({
            'name': 'Live module', 'serial': 'LIVE01', 'active': True, 'company_id': self.company.id,
            'last_ip': '192.0.2.50'})
        live_ctrl = self.env['hr.rfid.ctrl'].sudo().with_context(**ctx).create({
            'name': 'Live controller', 'ctrl_id': 3, 'serial_number': '9001', 'webstack_id': live_ws.id,
            'hw_version': '10', 'mode': 2})
        ts1 = self.env['hr.rfid.time.schedule'].search([('company_id', '=', self.company.id), ('number', '=', 1)])
        ts1.with_context(**ctx).write({
            'ts_data': codecs.decode_ts(ts_reply(1, {0: [('09:00', '17:00')]}))['ts_data'],
            'controller_ids': [(4, live_ctrl.id)]})
        self._commands_before = set(self.env['hr.rfid.command'].sudo().search([]).ids)
        run = self._resolved_survey(upload=False)
        slot1 = run.ts_slot_ids.filtered(lambda s: s.number == 1)
        self.assertTrue(slot1.existing_differs)
        self.assertEqual(slot1.state, 'ok', "the controllers agree: no question is asked")
        self._import(run)
        self.assertEqual(run.state, 'done', run.last_error)
        self.assertEqual(ts1._get_interval_from_day_tuple(0, 0), (8.0, 18.0), "the hardware wins")
        self.assertNotIn(live_ctrl, ts1.controller_ids)
        self.assertTrue(run.issue_ids.filtered(lambda i: 'Live controller' in i.message),
                        "the company's own controller that now differs is listed")
        self.assertFalse(self._write_commands())
        self.assertFalse(self.env['hr.rfid.command'].sudo().search(
            [('webstack_id', '=', live_ws.id), ('id', 'not in', list(self._commands_before))]),
            "nothing whatsoever was queued for the live module")

    def test_every_imported_card_mirrors_exactly_what_its_controllers_hold(self):
        run = self._resolved_survey(upload=False)
        self._import(run)
        self.assertEqual(run.state, 'done', run.last_error)
        checked = 0
        for card in run.card_ids:
            self.assertTrue(card.card_rec_id, card.number)
            expected = set()
            for right in json.loads(card.door_rights_json):
                ctrl = run.ctrl_ids.browse(right['ctrl'])
                if ctrl.ctrl_rec_id and ctrl.ctrl_rec_id.door_ids.filtered(lambda d: d.number == right['door']):
                    expected.add((ctrl.address, right['door'], right['ts'], bool(right['alarm'])))
            actual = {(r.door_id.controller_id.ctrl_id, r.door_id.number, r.time_schedule_id.number, r.alarm_right)
                      for r in card.card_rec_id.door_rel_ids}
            self.assertEqual(actual, expected, card.number)
            checked += 1
        self.assertEqual(checked, 9)

    def test_a_right_on_a_schedule_this_company_lacks_is_left_out_not_widened(self):
        """A card limited to a schedule must never come out of the import with
        no schedule at all - that would open the door around the clock."""
        Run = type(self.env['hr.rfid.hw.import.run'])
        original = Run._company_ts

        def without_slot_three(run, number):
            return run.env['hr.rfid.time.schedule'] if number == 3 else original(run, number)
        self.patch(Run, '_company_ts', without_slot_three)
        run = self._resolved_survey(upload=False)
        self._import(run)
        self.assertEqual(run.state, 'done', run.last_error)
        card = self._card(run, '0000100001').card_rec_id
        self.assertFalse(card.door_rel_ids.filtered(lambda r: r.door_id.controller_id.ctrl_id == ADDR_115),
                         "no right without a schedule where the controller had one")
        self.assertTrue(card.door_rel_ids.filtered(lambda r: r.door_id.controller_id.ctrl_id == ADDR_180),
                        "the card's other rights are unaffected")
        self.assertTrue(run.issue_ids.filtered(lambda i: 'follows schedule 3' in i.message))

    # ------------------------------------------------------------ the gate before the import

    def test_the_import_refuses_to_start_while_a_finding_must_be_resolved(self):
        run = self._survey()
        run.action_skip_names()
        self.assertTrue(run.has_blockers, "slot 2 is read differently by two controllers")
        with self.assertRaises(UserError):
            run.action_start_import()
        self.assertEqual(run.state, 'grouping')
        # Leaving the schedules out of the import takes the question off the table.
        self._import(run, import_schedules=False)
        self.assertEqual(run.state, 'done', run.last_error)
        self.assertFalse(self._write_commands())

    def test_a_person_whose_cards_disagree_blocks_only_the_import_of_people(self):
        run = self._survey()
        self._upload_names(run)
        run.ts_slot_ids.filtered(lambda s: s.number == 2).source_ctrl_id = run.ctrl_ids.filtered(
            lambda c: c.address == ADDR_180)
        run.action_to_grouping()
        self.assertTrue(run.person_ids.filtered(lambda p: p.review_state == 'blocked'))
        wiz = self.env['hr.rfid.hw.import.options.wiz'].with_context(default_run_id=run.id).create({'run_id': run.id})
        self.assertEqual(wiz.blocker_count, 1)
        with self.assertRaises(UserError):
            wiz.action_start()
        self.assertEqual(run.state, 'grouping')
        self._import(run, import_people=False, import_cards=False, import_groups=False)
        self.assertEqual(run.state, 'done', run.last_error)

    def test_the_import_dialog_choice_of_employee_reaches_every_generated_holder(self):
        """Decision 8: the kind chosen for the whole survey applies to every
        generated holder the operator did not change by hand."""
        run = self._resolved_survey(upload=False)
        self.assertTrue(all(p.owner_type == 'contact' for p in run.person_ids))
        wiz = self.env['hr.rfid.hw.import.options.wiz'].with_context(default_run_id=run.id).create({
            'run_id': run.id, 'placeholder_owner_type': 'employee', 'default_department_id': self.department.id})
        self.assertEqual((wiz.employee_count, wiz.contact_count), (len(run.person_ids), 0),
                         "the dialog shows what the import will do")
        wiz.action_start()
        self._work(run)
        self.assertEqual(run.state, 'done', run.last_error)
        self.assertTrue(all(p.employee_id for p in run.person_ids))
        self.assertFalse(run.person_ids.mapped('partner_id'))
        self.assertTrue(all(c.card_rec_id.employee_id for c in run.card_ids))
        self.assertFalse(self._write_commands())

    # ------------------------------------------------------------ merging groups (narrative 10)

    def _group_with(self, run, *rights):
        """The proposed group whose rights are exactly ``rights`` ((address, door, ts, alarm) tuples)."""
        wanted = set(rights)
        for group in run.group_ids:
            if {(r.ctrl_id.address, r.door_number, r.ts_number, r.alarm) for r in group.right_ids} == wanted:
                return group
        self.fail("no proposed group holds exactly %s" % (wanted,))

    def test_two_groups_can_be_merged_and_the_merged_group_is_imported_once(self):
        """Narrative 10: the doors of two proposed groups always go together
        after all; the operator merges them, reads what every card gains, and
        the import creates the merged group once."""
        run = self._resolved_survey(upload=False)
        first = self._group_with(run, (ADDR_110, 1, 0, False))
        second = self._group_with(run, (ADDR_115, 1, 0, False))
        second_name = second.name
        cards = first.card_ids | second.card_ids
        expected = {(ADDR_110, 1, 0, False), (ADDR_115, 1, 0, False)}
        wiz = self.env['hr.rfid.hw.import.group.merge.wiz'].with_context(
            active_model='hr.rfid.hw.import.group', active_ids=(first | second).ids).create({'name': 'Merged doors'})
        self.assertIn('will also open', wiz.warning, "the operator is told what every card gains")
        wiz.action_merge()
        self.assertEqual(len(run.group_ids), 7)
        merged = run.group_ids.filtered(lambda g: g.name == 'Merged doors')
        self.assertEqual(merged.card_ids, cards)
        self.assertEqual({(r.ctrl_id.address, r.door_number, r.ts_number, r.alarm) for r in merged.right_ids}, expected)
        self.assertEqual(json.loads(merged.merged_from_json), [second_name])
        self._import(run)
        self.assertEqual(run.state, 'done', run.last_error)
        self.assertEqual(self.env['hr.rfid.access.group'].search_count([('name', '=', 'Merged doors')]), 1)
        rels = self.env['hr.rfid.access.group.door.rel'].search([('access_group_id', '=', merged.access_group_id.id)])
        self.assertEqual(len(rels), 2)
        for card in cards:
            held = {(r.door_id.controller_id.ctrl_id, r.door_id.number, r.time_schedule_id.number, r.alarm_right)
                    for r in card.card_rec_id.door_rel_ids}
            self.assertTrue(expected <= held, "%s opens every door of the merged group" % card.number)
        self.assertFalse(self._write_commands())

    def test_a_merge_the_access_control_module_would_refuse_is_refused_here_with_the_reason(self):
        """Two proposed groups that open the same door on different terms, or
        a merge that would give a card a door through two groups, are refused
        before the import - not by the access control module afterwards."""
        run = self._resolved_survey(upload=False)
        Wiz = self.env['hr.rfid.hw.import.group.merge.wiz'].with_context(active_model='hr.rfid.hw.import.group')
        # Same door of the same controller, with and without the alarm right.
        with_alarm = self._group_with(run, (ADDR_180, 1, 1, True))
        without_alarm = self._group_with(run, (ADDR_180, 1, 1, False))
        wiz = Wiz.with_context(active_ids=(with_alarm | without_alarm).ids).create({'name': 'Clash'})
        self.assertIn('cannot be merged', wiz.warning)
        self.assertIn('different schedules or with different alarm rights', wiz.warning)
        with self.assertRaises(UserError):
            wiz.action_merge()
        # A card of the union already reaches a door of the merge through another group.
        other_door = self._group_with(run, (ADDR_110, 1, 0, False))
        wiz = Wiz.with_context(active_ids=(with_alarm | other_door).ids).create({'name': 'Twice'})
        self.assertIn('through two groups', wiz.warning)
        with self.assertRaises(UserError) as caught:
            wiz.action_merge()
        self.assertIn(self._card(run, '0000100002').number_display, str(caught.exception),
                      "the card that would hold the door twice is named")
        self.assertEqual(len(run.group_ids), 8, "nothing was merged")

    def test_merging_into_a_card_set_another_group_already_has_is_refused_with_a_reason(self):
        run = self._resolved_survey(upload=False)
        Group = self.env['hr.rfid.hw.import.group']
        pair = self._group_with(run, (ADDR_180, 1, 1, True))
        self.assertEqual(pair.card_count, 2)
        singles = Group
        for card in pair.card_ids:
            key = Group._holder_key_for(card)
            single = run.group_ids.filtered(lambda g: g.holder_key == key)
            if not single:
                single = Group.create({'run_id': run.id, 'sequence': 99, 'name': 'Only %s' % card.number,
                                       'holder_key': key, 'card_ids': [(6, 0, card.ids)]})
            singles |= single
        wiz = self.env['hr.rfid.hw.import.group.merge.wiz'].with_context(
            active_model='hr.rfid.hw.import.group', active_ids=singles.ids).create({'name': 'Twin'})
        with self.assertRaises(UserError) as caught:
            wiz.action_merge()
        self.assertIn(pair.name, str(caught.exception))

    # ------------------------------------------------------------ pointing, with the core really running

    def test_pointing_runs_the_core_setup_against_the_module_and_nothing_else(self):
        run = self._resolved_survey(upload=False)
        self._import(run)
        module = run.module_ids.filtered(lambda m: m.serial == MODULE_A_SERIAL)
        posted = []

        class _Ok:
            status_code = 200
            reason = 'OK'
            text = ''

        def fake_post(url, **kwargs):
            posted.append(url)
            return _Ok()
        from odoo.addons.hr_rfid.models import hr_rfid_webstack
        self.patch(hr_rfid_webstack.requests, 'post', fake_post)
        module.action_point_to_server()
        self.assertEqual(posted, ['http://192.0.2.10/protect/uart/conf', 'http://192.0.2.10/protect/config.htm'],
                         "exactly the module setup of the access control module, to the module itself")
        self.assertTrue(module.pointed_at)
        self.assertFalse(self._write_commands())
        queued = self.env['hr.rfid.command'].sudo().search(
            [('webstack_id', '=', module.webstack_id.id), ('id', 'not in', list(self._commands_before))])
        self.assertTrue(queued <= queued.filtered(lambda c: c.cmd in allowlist.READ_OPCODES | {'B1'}),
                        "only read commands sit in the queue of the imported module")

    def test_pointing_all_modules_keeps_the_ones_that_worked_when_one_refuses(self):
        run = self._resolved_survey(upload=False)
        self._import(run)

        class _Reply:
            def __init__(self, status):
                self.status_code = status
                self.reason = 'x'
                self.text = ''

        def fake_post(url, **kwargs):
            return _Reply(500 if MODULE_B_IP in url else 200)
        from odoo.addons.hr_rfid.models import hr_rfid_webstack
        self.patch(hr_rfid_webstack.requests, 'post', fake_post)
        result = run.action_point_modules()
        self.assertEqual(result['params']['type'], 'warning')
        self.assertIn(MODULE_B_IP, result['params']['message'])
        self.assertTrue(run.module_ids.filtered(lambda m: m.ip == MODULE_A_IP).pointed_at)
        self.assertFalse(run.module_ids.filtered(lambda m: m.ip == MODULE_B_IP).pointed_at)

    # ------------------------------------------------------------ the names file, edge shapes

    def test_a_first_line_with_a_blank_number_is_kept_as_unreadable_not_dropped(self):
        run = self._survey()
        self._upload_names(run, text="Nameless First,\nDemo Holder Two,100002\n")
        self.assertEqual({line.row_number: line.status for line in run.name_line_ids}, {1: 'invalid', 2: 'matched'})

    def test_a_file_with_more_than_two_columns_says_which_ones_were_used(self):
        run = self._survey()
        wiz = self.env['hr.rfid.hw.import.names.wiz'].create({
            'run_id': run.id, 'file': base64.b64encode(b"First,Last,Card\nDemo,Three,100003\n"),
            'file_name': 'names.csv'})
        result = wiz.action_load()
        self.assertIn('3 columns', result['params']['message'])
        self.assertEqual(self._card(run, '0000100003').person_id.name, 'Demo')
