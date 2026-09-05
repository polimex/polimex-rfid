"""What the survey says when a device, a network or a database does not behave.

Business statement (owner): the survey is run on a WORKING system at a
customer's site. A controller that answers badly, a module that drops off, a
search that cannot run - none of that may go quiet, none of that may fail the
whole survey, and none of that may ever leak into a command that changes the
hardware.
"""
import json
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.hr_rfid_hardware_import.models import hw_import_run

from .common import (HwImportCase, site_script, make_f0, COMMON, ADDR_180, ADDR_110, ADDR_115,
                     MODULE_A_IP, MODULE_B_IP, MODULE_A_SERIAL)

ADDR_STRANGE = 60


@tagged('post_install', '-at_install', 'rfid_hw_import', 'rfid_hw_import_failures')
class TestFailureShapes(HwImportCase):

    def _finding(self, run, text):
        return run.issue_ids.filtered(lambda i: text in i.message)

    # ------------------------------------------------------------ one controller misbehaves

    def test_a_damaged_bus_fails_that_controller_only_and_says_where_to_look(self):
        """One controller behind bad wiring must not stop the survey of the others."""
        script = site_script()
        script['modules'][MODULE_A_IP]['devices'][ADDR_110]['errors'] = {'F0': 22}
        self._with_script(script)
        run = self._survey(with_b=False)
        self.assertEqual(run.state, 'naming', "the survey went on without that controller")
        c110 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_110)
        c180 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_180)
        self.assertEqual(c110.read_state, 'failed')
        self.assertEqual(c180.read_state, 'done')
        finding = self._finding(run, 'damaged reply')
        self.assertEqual(finding.ctrl_id, c110)
        self.assertIn('wiring', finding.message)
        self.assertNotIn('22', finding.message, "the wire code stays in the command log")
        self.assertTrue(run.has_read_failures)
        # The wiring is fixed; the operator reads the failed controller again.
        del script['modules'][MODULE_A_IP]['devices'][ADDR_110]['errors']
        run.action_read_again()
        self._work(run)
        self.assertEqual(run.state, 'naming')
        self.assertEqual(c110.read_state, 'done')
        self.assertEqual(c110.cards_read, 5)
        self.assertFalse(run.has_read_failures)
        self.assertFalse(self._write_commands())

    def test_a_module_that_drops_off_fails_the_module_and_can_be_read_again(self):
        script = site_script()
        self._with_script(script)
        run = self._new_run()
        run.action_discover()
        self._work(run)
        self._add_module_b(run)
        module_b = script['modules'].pop(MODULE_B_IP)  # the router link goes down
        run.action_read()
        self._work(run)
        self.assertEqual(run.state, 'naming')
        b = run.module_ids.filtered(lambda m: m.ip == MODULE_B_IP)
        self.assertEqual(b.read_state, 'failed')
        self.assertTrue(b.read_error)
        self.assertTrue(self._finding(run, 'could not be read'))
        self.assertTrue(run.has_read_failures)
        with self.assertRaises(UserError):
            run.action_open_import_options()  # not from here: wrong state
        script['modules'][MODULE_B_IP] = module_b  # the link is back
        run.action_read_again()
        self._work(run)
        self.assertEqual(b.read_state, 'done')
        self.assertEqual(run.ctrl_ids.filtered(lambda c: c.address == ADDR_115).cards_read, 2)
        self.assertEqual(run.state, 'naming')
        run.action_skip_names()
        with self.assertRaises(UserError):
            run.action_read_again()  # nothing failed: nothing to read again

    def test_a_refused_request_is_a_warning_and_the_other_slots_are_still_read(self):
        """A controller that rejects one request has not said 'unsupported'."""
        self.backend.faults[(ADDR_180, 'F3')] = 'wrong_value'
        run = self._survey(with_b=False)
        c180 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_180)
        self.assertEqual(c180.read_state, 'done')
        self.assertNotIn('F3', json.loads(c180.gaps_json or '[]'), "a refusal is not a capability gap")
        self.assertEqual(len(c180.ts_ids), 14, "slot 1 was refused; the other fourteen were read")
        finding = self._finding(run, 'refused the request')
        self.assertEqual(finding.ctrl_id, c180)
        self.assertIn('time schedules', finding.message)

    def test_an_empty_reply_is_reported_and_not_taken_for_a_setting(self):
        self.backend.faults[(ADDR_180, 'FC')] = 'empty'
        run = self._survey(with_b=False)
        c180 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_180)
        self.assertEqual(c180.read_state, 'done')
        self.assertFalse(c180.fc_hex)
        self.assertFalse(c180.apb_bitmap)
        finding = self._finding(run, 'could not interpret')
        self.assertIn('anti-passback', finding.message)
        self.assertIn('empty', finding.message)

    def test_an_unreadable_reply_fails_only_that_setting_or_only_that_controller(self):
        script = site_script()
        script['modules'][MODULE_A_IP]['devices'][ADDR_180]['F5'] = 'ZZ'          # one setting
        script['modules'][MODULE_A_IP]['devices'][ADDR_110]['F0'] = 'ZZ' * 32     # the identity itself
        self._with_script(script)
        run = self._survey(with_b=False)
        self.assertEqual(run.state, 'naming', "neither reply stopped the survey")
        c180 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_180)
        self.assertEqual(c180.read_state, 'done')
        self.assertEqual(c180.f5_hex, 'ZZ', "the raw reply is kept as evidence")
        self.assertIn('operating mode', self._finding(run, 'could not interpret').message)
        c110 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_110)
        self.assertEqual(c110.read_state, 'failed')
        self.assertTrue(self._finding(run, 'could not read').filtered(lambda i: i.ctrl_id == c110))

    def test_a_card_count_beyond_the_controllers_capacity_is_clamped(self):
        script = site_script()
        device = script['modules'][MODULE_A_IP]['devices'][ADDR_110]
        device['F0'] = make_f0(6, 1101, 741, 3, 3, 2, 15, 28, 0, 0x01, 3, 3056)  # holds three cards
        self._with_script(script)
        run = self._survey(with_b=False)
        c110 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_110)
        self.assertEqual(c110.card_count_device, 3)
        self.assertEqual(c110.cards_read, 3)
        self.assertIn('can hold at most', self._finding(run, 'reports 5 cards').message)

    def test_an_incomplete_card_table_is_a_failed_read_not_a_short_import(self):
        script = site_script()
        script['modules'][MODULE_A_IP]['devices'][ADDR_110]['card_count'] = 8  # announces 8, serves 5
        self._with_script(script)
        run = self._survey(with_b=False)
        c110 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_110)
        self.assertEqual(c110.read_state, 'failed')
        self.assertIn('incomplete', c110.read_error)
        self.assertTrue(run.has_read_failures)

    def test_an_unknown_hardware_type_is_reported_and_never_imported(self):
        """The access control module cannot hold a hardware type it does not
        know; a controller of such a type is listed, said, and left out - it
        must not stop the import of everything else."""
        script = site_script()
        module = script['modules'][MODULE_A_IP]
        module['config']['sdk']['devFound'] = 6
        module['details']['devFound'] = 6
        module['status'][5] = {'dev': {'devID': ADDR_STRANGE, 'devHardware': 99, 'devSoftware': 700,
                                       'devSerial': 9901}}
        module['devices'][ADDR_STRANGE] = dict(COMMON, F0=make_f0(99, 9901, 700, 2, 2, 2, 15, 28, 0, 0x01, 100, 100))
        self._with_script(script)
        run = self._survey(with_b=False)
        strange = run.ctrl_ids.filtered(lambda c: c.address == ADDR_STRANGE)
        self.assertEqual(strange.family, 'unknown')
        self.assertEqual(strange.read_state, 'done')
        self.assertEqual([c[3] for c in hw_import_run.current_backend().commands_sent() if c[2] == ADDR_STRANGE],
                         ['F0'], "only its system information was asked for")
        run.ts_slot_ids.filtered(lambda s: s.number == 2).source_ctrl_id = run.ctrl_ids.filtered(
            lambda c: c.address == ADDR_180)
        run.action_skip_names()
        self._import(run)
        self.assertEqual(run.state, 'done', run.last_error)
        self.assertFalse(strange.ctrl_rec_id, "no record for hardware this system cannot hold")
        self.assertTrue(self._finding(run, 'does not know'))
        self.assertTrue(run.ctrl_ids.filtered(lambda c: c.address == ADDR_180).ctrl_rec_id,
                        "the other controllers were imported")
        self.assertFalse(self._write_commands())

    # ------------------------------------------------------------ the module

    def test_a_module_serial_the_system_cannot_hold_is_left_out_before_the_import(self):
        script = site_script()
        script['modules'][MODULE_B_IP]['config']['convertor'] = 'TEST02-TOO-LONG'
        script['modules'][MODULE_B_IP]['discovery']['serial'] = 'TEST02-TOO-LONG'
        self._with_script(script)
        run = self._survey()
        b = run.module_ids.filtered(lambda m: m.ip == MODULE_B_IP)
        self.assertFalse(b.include, "decided at analysis, not half-way through the import")
        self.assertTrue(self._finding(run, 'longer than this system can hold'))
        run.ts_slot_ids.filtered(lambda s: s.number == 2).source_ctrl_id = run.ctrl_ids.filtered(
            lambda c: c.address == ADDR_180)
        run.action_skip_names()
        self._import(run)
        self.assertEqual(run.state, 'done', run.last_error)
        self.assertFalse(b.webstack_id)
        self.assertFalse(b.ctrl_ids.mapped('ctrl_rec_id'))
        self.assertTrue(run.module_ids.filtered(lambda m: m.ip == MODULE_A_IP).webstack_id)
        self.assertFalse(self._write_commands())

    def test_a_module_without_a_serial_number_blocks_the_import(self):
        script = site_script()
        script['modules'][MODULE_B_IP]['config']['convertor'] = ''
        script['modules'][MODULE_B_IP]['discovery']['serial'] = ''
        self._with_script(script)
        run = self._survey()
        b = run.module_ids.filtered(lambda m: m.ip == MODULE_B_IP)
        self.assertFalse(b.serial)
        finding = self._finding(run, 'reports no serial number')
        self.assertEqual(finding.severity, 'blocker')
        self.assertTrue(run.has_blockers)

    def test_a_network_search_that_cannot_run_is_reported_not_shown_as_an_empty_network(self):
        script = site_script()
        script['discovery_fault'] = 'port 30303 is in use'
        self._with_script(script)
        run = self._new_run()
        run.action_discover()
        self._work(run)
        self.assertEqual(run.state, 'draft')
        self.assertFalse(run.module_ids)
        finding = self._finding(run, 'network search could not be run')
        self.assertIn('in use', finding.message)
        self.assertIn('by address', finding.message)

    # ------------------------------------------------------------ passwords and parked surveys

    def _age(self, run, **delta):
        stamp = fields.Datetime.now() - timedelta(**delta)
        # Pending writes would stamp "now" over the age on their way to the table.
        self.env.flush_all()
        self.env.cr.execute("UPDATE hr_rfid_hw_import_run SET write_date = %s WHERE id = %s", (stamp, run.id))
        run.invalidate_recordset(['write_date'])

    def test_a_survey_left_parked_for_a_day_forgets_the_module_passwords(self):
        run = self._new_run()
        wiz = self.env['hr.rfid.hw.import.add.ip.wiz'].create({
            'run_id': run.id, 'ip': MODULE_B_IP, 'module_username': 'sdk', 'module_password': 'letmein'})
        wiz.action_add()
        module = run.module_ids
        self.assertEqual(module.sudo().module_password, 'letmein')
        self._age(run, hours=2)
        self.env['hr.rfid.hw.import.run']._abandon_stalled_runs()
        self.assertEqual(module.sudo().module_password, 'letmein', "two hours is a lunch break, not abandonment")
        self._age(run, hours=hw_import_run.IDLE_PASSWORD_HOURS + 1)
        self.env['hr.rfid.hw.import.run']._abandon_stalled_runs()
        self.assertFalse(module.sudo().module_password)
        self.assertEqual(run.state, 'draft', "the survey itself is kept")
        self.assertTrue(run.message_ids.filtered(lambda m: 'passwords' in (m.body or '')))

    def test_a_survey_the_worker_abandoned_is_closed_with_its_passwords_cleared(self):
        run = self._new_run()
        wiz = self.env['hr.rfid.hw.import.add.ip.wiz'].create({
            'run_id': run.id, 'ip': MODULE_B_IP, 'module_password': 'letmein'})
        wiz.action_add()
        run.action_read()
        self._age(run, minutes=hw_import_run.STALLED_MINUTES + 1)
        self.env['hr.rfid.hw.import.run']._abandon_stalled_runs()
        self.assertEqual(run.state, 'failed')
        self.assertIn('stopped without finishing', run.last_error)
        self.assertFalse(run.module_ids.sudo().module_password)

    # ------------------------------------------------------------ another company's records

    def test_records_of_another_company_block_the_import_without_being_named(self):
        other = self.env['res.company'].create({'name': 'Other tenant'})
        webstack = self.env['hr.rfid.webstack'].sudo().create({
            'name': 'Their secret module', 'serial': MODULE_A_SERIAL, 'active': False, 'company_id': other.id})
        self.env['hr.rfid.ctrl'].sudo().with_context(no_hardware_commands=True).create({
            'name': 'Their secret controller', 'ctrl_id': ADDR_180, 'serial_number': '1801',
            'webstack_id': webstack.id, 'hw_version': '10'})
        run = self._survey(with_b=False, include_known=True)
        module = run.module_ids
        self.assertEqual(module.status, 'known')
        self.assertFalse(module.existing_webstack_id, "another company's record is not linked")
        module_finding = run.issue_ids.filtered(lambda i: i.kind == 'conflict_webstack')
        self.assertIn('elsewhere in this database', module_finding.message)
        self.assertNotIn('secret', module_finding.message)
        self.assertFalse(module_finding.target_id)
        ctrl_finding = run.issue_ids.filtered(lambda i: i.kind == 'conflict_ctrl')
        self.assertIn('elsewhere in this database', ctrl_finding.message)
        self.assertNotIn('secret', ctrl_finding.message)
        self.assertFalse(run.ctrl_ids.filtered(lambda c: c.address == ADDR_180).existing_ctrl_id)
        self.assertTrue(run.has_blockers)
        # The operator leaves them out and imports the rest.
        (module_finding | ctrl_finding).write({'resolution': 'skip'})
        run.ts_slot_ids.filtered(lambda s: s.number == 2).source_ctrl_id = run.ctrl_ids.filtered(
            lambda c: c.address == ADDR_110)
        run.action_skip_names()
        self._import(run)
        self.assertEqual(run.state, 'done', run.last_error)
        self.assertFalse(module.webstack_id)
        self.assertEqual(self.env['hr.rfid.webstack'].sudo().with_context(active_test=False).search_count(
            [('serial', '=', MODULE_A_SERIAL)]), 1, "no second record with that serial")
        self.assertFalse(self._write_commands())
        self.assertFalse(self.env['hr.rfid.command'].sudo().search(
            [('webstack_id', '=', webstack.id), ('id', 'not in', list(self._commands_before))]),
            "nothing was queued for the other company's module")

    # ------------------------------------------------------------ what the reading found stays visible

    def test_what_the_reading_found_is_still_there_after_the_analysis(self):
        """The operator opens the survey at the Names step, after the analysis
        ran; every problem the reading met must still be on the Findings tab."""
        script = site_script()
        script['modules'][MODULE_A_IP]['devices'][ADDR_110]['errors'] = {'F0': 22}
        self._with_script(script)
        self.backend = hw_import_run.current_backend()
        run = self._survey(with_b=False)
        self.assertEqual(run.state, 'naming')
        read_findings = run.issue_ids.filtered(lambda i: i.phase == 'read')
        self.assertTrue(read_findings.filtered(lambda i: 'damaged reply' in i.message))
        self.assertTrue(read_findings.filtered(lambda i: 'vending machine' in i.message))
        self.assertTrue(run.issue_ids.filtered(lambda i: i.phase == 'analysis'), "the analysis wrote its own")

    def test_a_failed_module_is_not_knocked_on_every_pass(self):
        script = site_script()
        self._with_script(script)
        backend = hw_import_run.current_backend()
        run = self._new_run()
        run.action_discover()
        self._work(run)
        self._add_module_b(run)
        script['modules'].pop(MODULE_B_IP)
        backend.calls.clear()  # what the reading itself sends, not the probe at add time
        run.action_read()
        original = hw_import_run.PASS_SECONDS
        hw_import_run.PASS_SECONDS = 0.0
        try:
            passes = self._work(run)
        finally:
            hw_import_run.PASS_SECONDS = original
        self.assertGreater(passes, 3, "several passes were needed for the working module")
        knocks = [c for c in backend.calls if c[0] == 'GET' and c[1] == MODULE_B_IP]
        self.assertEqual(len(knocks), 1, "the dead module was tried once, then left for 'Read again'")
        self.assertEqual(len(run.issue_ids.filtered(lambda i: 'could not be read' in i.message)), 1)

    def test_a_clock_that_is_not_a_date_is_a_finding_not_zero_drift(self):
        """A controller with a flat clock battery is exactly the one whose
        schedules do not work; it must never look perfectly synchronised."""
        script = site_script()
        script['modules'][MODULE_A_IP]['devices'][ADDR_180]['F7'] = '00' * 7
        self._with_script(script)
        run = self._survey(with_b=False)
        c180 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_180)
        self.assertEqual(c180.read_state, 'done')
        self.assertFalse(c180.clock_read)
        finding = self._finding(run, 'could not interpret').filtered(lambda i: 'clock' in i.message)
        self.assertEqual(finding.ctrl_id, c180)

    # ------------------------------------------------------------ the worker itself

    def test_the_survey_says_so_when_the_scheduled_action_is_off(self):
        cron = self.env.ref('hr_rfid_hardware_import.ir_cron_hw_import_run')
        cron.sudo().active = False
        self.addCleanup(cron.sudo().write, {'active': True})
        run = self._new_run()
        with self.assertRaises(UserError) as caught, self.env.cr.savepoint():
            run.action_discover()
        self.assertIn('Scheduled Actions', str(caught.exception))
        self.assertEqual(run.state, 'draft', "nothing was started that nobody would finish")

    def test_a_second_survey_started_meanwhile_counts_as_remaining_work(self):
        """The scheduler keeps running only while something remains; a survey
        started while another one runs must be part of that count."""
        seen = []
        original = type(self.env['ir.cron'])._commit_progress

        def recording(cron, processed=0, *, remaining=None, deactivate=False):
            seen.append(remaining)
            return original(cron, processed, remaining=remaining, deactivate=deactivate)
        self.patch(type(self.env['ir.cron']), '_commit_progress', recording)
        first = self._new_run()
        first.action_discover()
        second = self._new_run()
        second.action_discover()
        self.env['hr.rfid.hw.import.run']._cron_process()
        first.invalidate_recordset()
        self.assertEqual(first.state, 'draft', "the older survey was worked on first")
        self.assertEqual(second.state, 'discovering')
        self.assertGreaterEqual(seen[-1], 1, "the waiting survey is remaining work")
        self._work(second)
        self.assertEqual(second.state, 'draft')

    def test_a_survey_that_stopped_can_be_reopened_and_finishes_without_duplicates(self):
        from odoo.addons.hr_rfid_hardware_import.models import importer as importer_module
        run = self._survey(with_b=False)
        run.ts_slot_ids.filtered(lambda s: s.number == 2).source_ctrl_id = run.ctrl_ids.filtered(
            lambda c: c.address == ADDR_180)
        run.action_skip_names()
        original = importer_module.HardwareImporter._step_groups
        calls = []

        def failing_once(importer):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("simulated failure in the groups step")
            return original(importer)
        self.patch(importer_module.HardwareImporter, '_step_groups', failing_once)
        self._import(run)
        self.assertEqual(run.state, 'failed')
        self.assertIn('Reopen', run.last_error)
        self.assertNotIn('RuntimeError', run.last_error.split('(')[0], "the operator gets the next step, not a Python class")
        cards_after_failure = self.env['hr.rfid.card'].search_count([('company_id', '=', self.company.id)])
        run.action_reopen()
        self.assertEqual(run.state, 'grouping')
        self._import(run)
        self.assertEqual(run.state, 'done', run.last_error)
        self.assertEqual(self.env['hr.rfid.card'].search_count([('company_id', '=', self.company.id)]),
                         cards_after_failure, "the steps already done were not repeated")
        self.assertTrue(run.group_ids.mapped('access_group_id'))
        self.assertFalse(self._write_commands())

    def test_the_same_module_reached_by_two_addresses_is_set_aside_not_a_crash(self):
        script = site_script()
        script['discovery'].append(dict(script['discovery'][0], ip='192.0.2.11'))  # module A answers twice
        script['modules']['192.0.2.11'] = script['modules'][MODULE_A_IP]
        self._with_script(script)
        run = self._new_run()
        run.action_discover()
        self._work(run)
        self.assertEqual(run.state, 'draft', "the survey went on")
        aside = run.module_ids.filtered(lambda m: m.ip == '192.0.2.11')
        self.assertEqual(aside.status, 'unreachable')
        self.assertFalse(aside.include)
        self.assertTrue(self._finding(run, 'second address was set aside'))
        self.assertEqual(run.module_ids.filtered(lambda m: m.serial == MODULE_A_SERIAL).ip, MODULE_A_IP)

    def test_reading_again_keeps_the_operators_decisions(self):
        script = site_script()
        script['modules'][MODULE_A_IP]['devices'][ADDR_110]['errors'] = {'F0': 22}
        self._with_script(script)
        self.env['hr.rfid.webstack'].sudo().create({
            'name': 'Existing module', 'serial': MODULE_A_SERIAL, 'active': False, 'company_id': self.company.id})
        run = self._survey(with_b=False, include_known=True)
        conflict = run.issue_ids.filtered(lambda i: i.kind == 'conflict_webstack')
        conflict.resolution = 'link'
        pair = run.group_ids.filtered(lambda g: g.card_count == 2)[:1]
        pair.name = 'Front doors'
        del script['modules'][MODULE_A_IP]['devices'][ADDR_110]['errors']
        run.action_read_again()
        self._work(run)
        self.assertEqual(run.state, 'naming')
        self.assertEqual(run.ctrl_ids.filtered(lambda c: c.address == ADDR_110).read_state, 'done')
        conflict = run.issue_ids.filtered(lambda i: i.kind == 'conflict_webstack')
        self.assertEqual(conflict.resolution, 'link', "the decision on the conflict survived")
        self.assertTrue(run.group_ids.filtered(lambda g: g.name == 'Front doors'), "the group name survived")
        slot2 = run.ts_slot_ids.filtered(lambda s: s.number == 2)
        self.assertEqual(slot2.state, 'conflict', "the second controller brought a second reading")
        slot2.source_ctrl_id = run.ctrl_ids.filtered(lambda c: c.address == ADDR_180)
        self.assertFalse(run.has_blockers, run.issue_ids.filtered(lambda i: not i.resolved).mapped('message'))

    def test_an_adopted_employee_in_another_department_still_gets_the_group(self):
        """A card already registered to an employee of some department: the
        operator links it, and the import must open that department for the
        new access groups instead of failing half-way."""
        other = self.env['hr.department'].create({'name': 'Warehouse'})
        employee = self.env['hr.employee'].create({'name': 'Existing Worker', 'department_id': other.id})
        self.env['hr.rfid.card'].sudo().with_context(no_hardware_commands=True).create({
            'number': '0000100003', 'card_input_type': 'w34', 'employee_id': employee.id,
            'company_id': self.company.id})
        run = self._survey(with_b=False)
        run.issue_ids.filtered(lambda i: i.kind == 'conflict_card').write({'resolution': 'link'})
        run.ts_slot_ids.filtered(lambda s: s.number == 2).source_ctrl_id = run.ctrl_ids.filtered(
            lambda c: c.address == ADDR_180)
        run.action_skip_names()
        self._import(run)
        self.assertEqual(run.state, 'done', run.last_error)
        self.assertEqual(self._card(run, '0000100003').person_id.employee_id, employee)
        self.assertTrue(employee.hr_rfid_access_group_ids, "the adopted employee holds the imported groups")
        self.assertTrue(other.hr_rfid_allowed_access_groups)
        self.assertFalse(self._write_commands())
