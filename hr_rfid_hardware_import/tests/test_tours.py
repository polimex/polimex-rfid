"""One tour per process narrative: the operator can drive the survey on screen.

Business statement: the person surveying a site adds a module by address,
watches a long reading, reviews the people and the hardware, resolves what
blocks the import, merges groups, starts the import and hands the modules
over - by typing and clicking, not by reading a screen that renders but takes
no input. The tours use names, classes, icons and numbers as triggers, never
visible text, because the database may run in any language.
"""
import base64

from odoo.tests import HttpCase, tagged

from .common import site_script, NAMES_CSV, ADDR_180, MODULE_A_SERIAL, MODULE_B_IP
from odoo.addons.hr_rfid_hardware_import.helpers.fake_transport import FakeBackend
from odoo.addons.hr_rfid_hardware_import.models import hw_import_run


@tagged('post_install', '-at_install', 'rfid_hw_import', 'rfid_hw_import_tour')
class TestSurveyTours(HttpCase):

    _registry_readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend = FakeBackend(site_script())
        hw_import_run.override_backend(cls.backend)
        cls.addClassCleanup(hw_import_run.override_backend, None)
        cls.env['hr.rfid.time.schedule'].sudo().set_company_ts()

    # ------------------------------------------------------------ seeding

    def _work(self, run):
        while run.state in hw_import_run.WORKER_STATES:
            self.env['hr.rfid.hw.import.run']._cron_process()
            run.invalidate_recordset()

    def _add_module_b(self, run):
        self.env['hr.rfid.hw.import.add.ip.wiz'].create({'run_id': run.id, 'ip': MODULE_B_IP}).action_add()

    def _seeded_run(self, state, names=False, resolved=False, include_known=False):
        """A survey brought to ``state`` by the worker, exactly as the operator
        would have got it there."""
        self.patch(self.env.cr, 'commit', lambda: None)
        self.patch(self.env.cr, 'rollback', lambda: None)
        run = self.env['hr.rfid.hw.import.run'].create({'company_id': self.env.company.id})
        run.action_discover()
        self._work(run)
        self._add_module_b(run)
        if include_known:
            run.module_ids.write({'include': True})
        if state == 'reading':
            run.action_read()
            original = hw_import_run.PASS_SECONDS
            hw_import_run.PASS_SECONDS = 0.0
            try:
                self.env['hr.rfid.hw.import.run']._cron_process()
            finally:
                hw_import_run.PASS_SECONDS = original
            run.invalidate_recordset()
            self.assertEqual(run.state, 'reading')
            return run
        run.action_read()
        self._work(run)
        self.assertEqual(run.state, 'naming')
        if names:
            wiz = self.env['hr.rfid.hw.import.names.wiz'].create({
                'run_id': run.id, 'file': base64.b64encode(NAMES_CSV.encode('utf-8')), 'file_name': 'names.csv'})
            wiz.action_load()
        if resolved:
            run.ts_slot_ids.filtered(lambda s: s.number == 2).source_ctrl_id = run.ctrl_ids.filtered(
                lambda c: c.address == ADDR_180)
            run.person_ids.filtered(lambda p: p.review_state == 'blocked').action_split()
            for issue in run.issue_ids.filtered(lambda i: i.severity == 'blocker'):
                issue.resolution = 'link'
        if state == 'naming':
            return run
        run.action_to_grouping() if run.name_line_ids else run.action_skip_names()
        if state == 'grouping':
            return run
        wiz = self.env['hr.rfid.hw.import.options.wiz'].with_context(default_run_id=run.id).create({'run_id': run.id})
        wiz.action_start()
        self._work(run)
        self.assertEqual(run.state, 'done', run.last_error)
        return run

    # ------------------------------------------------------------ the narratives

    def test_narrative_2_the_operator_adds_a_module_by_address(self):
        self.start_tour('/odoo', 'hw_import_survey_tour', login='admin')

    def test_narrative_9_the_operator_watches_a_reading_in_progress(self):
        self._seeded_run('reading')
        self.start_tour('/odoo', 'hw_import_progress_tour', login='admin')

    def test_narrative_7_the_operator_sees_what_kind_of_hardware_was_found(self):
        self._seeded_run('naming')
        self.start_tour('/odoo', 'hw_import_hardware_tour', login='admin')

    def test_narrative_3_the_operator_reviews_the_people_of_the_names_file(self):
        self._seeded_run('naming', names=True)
        self.start_tour('/odoo', 'hw_import_names_tour', login='admin')

    def test_narrative_4_the_operator_turns_a_generated_owner_into_an_employee(self):
        self._seeded_run('naming')
        self.start_tour('/odoo', 'hw_import_placeholders_tour', login='admin')

    def test_narrative_5_the_operator_resolves_a_schedule_conflict(self):
        self._seeded_run('grouping')
        self.start_tour('/odoo', 'hw_import_schedules_tour', login='admin')

    def test_narrative_6_the_operator_decides_on_records_already_here(self):
        self.env['hr.rfid.webstack'].sudo().create({
            'name': 'Existing module', 'serial': MODULE_A_SERIAL, 'active': False,
            'company_id': self.env.company.id})
        holder = self.env['res.partner'].create({'name': 'Existing holder'})
        self.env['hr.rfid.card'].sudo().with_context(no_hardware_commands=True).create({
            'number': '0000100001', 'card_input_type': 'w34', 'contact_id': holder.id,
            'company_id': self.env.company.id})
        self._seeded_run('grouping', include_known=True)
        self.start_tour('/odoo', 'hw_import_conflicts_tour', login='admin')

    def test_narrative_10_the_operator_renames_and_merges_groups(self):
        self._seeded_run('grouping')
        self.start_tour('/odoo', 'hw_import_groups_tour', login='admin')

    def test_narrative_1_the_operator_starts_the_import(self):
        self._seeded_run('grouping', resolved=True)
        self.start_tour('/odoo', 'hw_import_import_tour', login='admin')

    def test_narrative_8_the_operator_hands_the_modules_over(self):
        self._seeded_run('done', resolved=True)
        self.start_tour('/odoo', 'hw_import_handover_tour', login='admin')
