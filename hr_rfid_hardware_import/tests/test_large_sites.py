"""A large site, a server with time limits, an operator who types anything.

Business statements:

* Owner, 2026-09-03: the survey is the inventory of a WORKING system, read
  "строго само за четене" - nothing may reach a device but a read, and no
  address the operator types may open another page of the module.
* Owner, 2026-10-13, before production: a site with tens of thousands of cards
  must survey and import to the end; the server's own time limit for
  scheduled work must never cut a step in the middle and start it again for
  ever.
"""

import time
from contextlib import closing
from datetime import timedelta

import xlsxwriter

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from ..helpers import allowlist, transport
from ..models import exporter as exporter_module
from ..models import hw_import_run, importer, reader
from .common import (
    ADDR_180,
    MODULE_A_IP,
    MODULE_A_SERIAL,
    MODULE_B_IP,
    HwImportCase,
    choose_slot_source,
)


@tagged("post_install", "-at_install", "rfid_hw_import", "rfid_hw_import_large")
class TestLargeSites(HwImportCase):
    def _in_small_passes(self):
        """Every pass gets no time at all: each does one piece and stops, the
        way a very large site looks to the worker."""
        self.patch(hw_import_run, "PASS_SECONDS", 0.0)
        self.patch(importer, "IMPORT_BATCH", 1)
        self.patch(importer, "MEMBERSHIP_BATCH", 1)

    # ------------------------------------------------------------ the import in pieces

    def test_an_import_cut_into_many_passes_ends_complete_and_creates_nothing_twice(
        self,
    ):
        """Every person, card and membership is there once, however many times
        the worker had to stop between two pieces of a step."""
        run = self._resolved_survey()
        self._in_small_passes()
        self._start_import(run)
        passes = self._work(run)
        self.assertEqual(run.state, "done", run.last_error)
        people = run.person_ids.filtered(lambda p: p.include and p.card_ids)
        self.assertGreater(
            passes,
            len(importer.STEPS) + len(people),
            "the people, cards and memberships steps really stopped between pieces",
        )
        self.assertTrue(all(p.employee_id or p.partner_id for p in people))
        cards = run.card_ids.filtered(lambda c: c.include and c.person_id)
        self.assertTrue(all(cards.mapped("card_rec_id")))
        self.assertEqual(
            len(cards.mapped("card_rec_id")), len(cards), "one card here per card read"
        )
        holders = self.env["hr.rfid.card"].search(
            [("id", "in", cards.mapped("card_rec_id").ids)]
        )
        self.assertEqual(len(holders), len(cards))
        memberships = self.env["hr.rfid.access.group.contact.rel"].search(
            [("access_group_id", "in", run.group_ids.mapped("access_group_id").ids)]
        )
        pairs = [(rel.access_group_id.id, rel.contact_id.id) for rel in memberships]
        self.assertEqual(len(pairs), len(set(pairs)), "no membership was given twice")
        for group in run.group_ids.filtered("include"):
            for person in group.card_ids.mapped("person_id").filtered("include"):
                holder = person.employee_id or person.partner_id
                self.assertIn(
                    group.access_group_id,
                    holder.hr_rfid_access_group_ids.mapped("access_group_id"),
                    "%s holds %s" % (person.name, group.name),
                )
        messages = run.issue_ids.filtered(lambda i: i.phase == "import").mapped(
            "message"
        )
        self.assertEqual(
            len(messages), len(set(messages)), "no line of the report was written twice"
        )
        self.assertEqual(run.step_cursor, 0)
        self.assertFalse(self._write_commands())

    def test_cutting_the_import_into_pieces_changes_nothing_in_what_it_creates(self):
        """The control case for the test above: the same survey imported in one
        pass and in many gives the same people, cards and groups."""
        run = self._resolved_survey()

        def outcome():
            return sorted(
                (
                    p.name,
                    len(p.card_ids.mapped("card_rec_id")),
                    sorted(
                        (p.employee_id or p.partner_id).hr_rfid_access_group_ids.mapped(
                            "access_group_id.name"
                        )
                    ),
                )
                for p in run.person_ids
                if p.employee_id or p.partner_id
            )

        # Imported once in one pass, measured, and undone (contextlib.closing
        # rolls a savepoint back, as the core's own tests do).
        with closing(self.env.cr.savepoint()):
            self._import(run)
            self.assertEqual(run.state, "done", run.last_error)
            whole = outcome()
        self.env.invalidate_all()
        self.assertEqual(run.state, "grouping", "the one-pass import was undone")
        self.assertTrue(whole)
        self._in_small_passes()
        self._import(run)
        self.assertEqual(run.state, "done", run.last_error)
        self.assertEqual(outcome(), whole)

    # ------------------------------------------------------------ the scheduler's time limit

    def test_a_job_that_has_used_its_time_starts_no_new_work(self):
        """Once the scheduler's job has had its time, the worker hands over to
        a fresh job instead of starting another piece in this one."""
        run = self._new_run()
        run.action_discover()
        Run = self.env["hr.rfid.hw.import.run"]
        Run.with_context(cron_end_time=time.monotonic() - 1)._cron_process()
        run.invalidate_recordset()
        self.assertEqual(run.state, "discovering", "no work was started")
        self.assertFalse(self.backend.calls, "the network was not touched")
        Run.with_context(cron_end_time=time.monotonic() + 60)._cron_process()
        run.invalidate_recordset()
        self.assertEqual(run.state, "draft", "a job with time left does the work")

    def _in_a_scheduler_job(self, time_left):
        """The context the core's scheduler gives one run of the job
        (ir.cron._run_job), with its progress record."""
        cron, progress = self.env.ref(hw_import_run.WORKER_CRON)._add_progress()
        Run = self.env["hr.rfid.hw.import.run"].with_context(
            cron_id=cron.id,
            ir_cron_progress_id=progress.id,
            cron_end_time=time.monotonic() + time_left,
        )
        return Run, progress

    def test_a_job_out_of_time_tells_the_scheduler_to_come_back_at_once(self):
        """Work left with nothing done is what makes the core run the job again
        at once ("partially done"); "nothing left" would park the survey until
        the next daily run."""
        run = self._new_run()
        run.action_discover()
        Run, progress = self._in_a_scheduler_job(-1)
        Run._cron_process()
        self.assertEqual(progress.done, 0)
        self.assertGreaterEqual(progress.remaining, 1)

    def test_a_survey_held_by_someone_else_is_tried_again_at_once(self):
        """The survey row is being written in another transaction; the pass
        does nothing and asks to be repeated - it does not report "done"."""
        run = self._new_run()
        run.action_discover()
        self.patch(type(run), "try_lock_for_update", lambda records, **kwargs: False)
        Run, progress = self._in_a_scheduler_job(60)
        Run._cron_process()
        run.invalidate_recordset()
        self.assertEqual(run.state, "discovering")
        self.assertEqual(progress.done, 0)
        self.assertGreaterEqual(progress.remaining, 1)

    def test_a_module_answering_for_other_commands_is_given_up_within_the_command_budget(
        self,
    ):
        class Session:
            posted = 0

            def post(self, url, json=None, **kwargs):
                Session.posted += 1
                return type(
                    "R",
                    (),
                    {
                        "status_code": 200,
                        "json": lambda s: {"id": 9, "c": "B3", "e": 0, "d": ""},
                    },
                )()

        self.patch(transport, "COMMAND_BUDGET_SECONDS", 0.0)
        client = transport.HardwareClient(
            "192.0.2.1", sleep=lambda s: None, session=Session()
        )
        with self.assertRaises(transport.Unreachable):
            client.cmd(15, "F0")
        self.assertEqual(
            Session.posted, 1, "a module out of time is not asked again eight times"
        )

    # ------------------------------------------------------------ a card table read in pieces

    def test_a_card_table_half_read_when_the_survey_stopped_continues_from_its_page(
        self,
    ):
        """The survey stops while a card table is half read; reopened and read
        again, the controller carries on from the page it reached - no page is
        asked for twice on the customer's bus."""
        self.patch(reader, "READ_CARDS_BLOCK_SIZE", 2)
        self.patch(hw_import_run, "PASS_SECONDS", 0.0)
        run = self._new_run()
        run.action_discover()
        self._work(run)
        run.action_read()
        Run = self.env["hr.rfid.hw.import.run"]
        c180 = run.ctrl_ids.browse()
        for _attempt in range(100):
            Run._cron_process()
            run.invalidate_recordset()
            c180 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_180)
            if c180.read_state == "cards" and c180.read_cursor > 1:
                break
        self.assertEqual(c180.read_state, "cards")
        reached = c180.read_cursor
        self.assertGreater(reached, 1)
        run._finish("failed", "The server was restarted.")
        run.action_reopen()
        self.assertEqual(run.state, "draft")
        run.action_read()
        self.assertEqual(
            c180.read_cursor, reached, "the position in the card table is kept"
        )
        self._work(run)
        self.assertEqual(c180.read_state, "done")
        self.assertEqual(c180.cards_read, 6)
        pages = [
            call[4]
            for call in self.backend.commands_sent()
            if call[2] == ADDR_180 and call[3] == "F2"
        ]
        self.assertEqual(
            len(pages), len(set(pages)), "no page of the card table was asked for twice"
        )
        self.assertFalse(self._write_commands())

    # ------------------------------------------------------------ what the operator types

    def test_an_address_with_a_path_or_credentials_is_refused(self):
        """Only the address of the module goes into the address field; a page,
        a query, a user name or a port glued to it would reach something other
        than the read-only interface."""
        run = self._new_run()
        for typed in (
            "10.0.0.5/protect/config.htm?x=",
            "10.0.0.5:8080",
            "user:pass@10.0.0.5",
            "http://10.0.0.5",
            "10.0.0.5 #",
            "",
            "module..local",
            "fe80::1%]@192.0.2.99",
            "gate\n.example",
            "192.168.1",
            "10.1",
            "3232235777",
            "0x7f.1",
        ):
            with self.subTest(address=typed), self.assertRaises(UserError):
                with self.env.cr.savepoint():
                    self.env["hr.rfid.hw.import.add.ip.wiz"].create(
                        {"run_id": run.id, "ip": typed}
                    ).action_add()
        self.assertFalse(run.module_ids)
        self.assertFalse(self.backend.calls, "nothing was asked of the network")

    def test_an_ip_address_or_a_host_name_is_accepted(self):
        run = self._new_run()
        Module = self.env["hr.rfid.hw.import.module"]
        for typed in ("192.168.1.50", "gate-module.example", "fe80::1", "module7"):
            Module.create(
                {"run_id": run.id, "source": "manual", "ip": typed, "port": 80}
            )
        self.assertEqual(len(run.module_ids), 4)
        client = transport.HardwareClient("fe80::1", session=object())
        self.assertEqual(
            client._url("/config.json"),
            "http://[fe80::1]:80/config.json",
            "an IPv6 address is bracketed in the URL",
        )

    def test_numbers_that_are_not_a_valid_ip_address_are_called_that(self):
        """Parts missing, an extra part, leading zeros: the operator is told how
        an IP address is written, not that the field holds no address."""
        run = self._new_run()
        for typed in ("192.168.1", "1.2.3.4.5", "192.168.001.050"):
            with (
                self.subTest(address=typed),
                self.assertRaises(ValidationError) as caught,
            ):
                with self.env.cr.savepoint():
                    self.env["hr.rfid.hw.import.module"].create(
                        {"run_id": run.id, "source": "manual", "ip": typed}
                    )
            self.assertIn("four numbers from 0 to 255", caught.exception.args[0])

    def test_the_client_itself_refuses_an_address_with_a_path_before_any_request(self):
        class Session:
            def post(self, *args, **kwargs):
                raise AssertionError("no request may be made")

            get = post

        with self.assertRaises(allowlist.ForbiddenHost):
            transport.HardwareClient(
                "10.0.0.5/protect/config.htm?x=", session=Session()
            )

    def test_a_port_outside_the_tcp_range_is_refused(self):
        run = self._new_run()
        Module = self.env["hr.rfid.hw.import.module"]
        for port in (0, 65536, 70000):
            with self.subTest(port=port), self.assertRaises(ValidationError):
                with self.env.cr.savepoint():
                    Module.create(
                        {
                            "run_id": run.id,
                            "source": "manual",
                            "ip": "192.168.1.50",
                            "port": port,
                        }
                    )
        for number, port in enumerate((1, 65535)):
            Module.create(
                {
                    "run_id": run.id,
                    "source": "manual",
                    "ip": "192.168.1.%s" % (60 + number),
                    "port": port,
                }
            )
        self.assertEqual(len(run.module_ids), 2)

    def test_an_address_saved_before_the_check_sets_that_module_aside_not_the_survey(
        self,
    ):
        """A survey from before addresses were checked holds '10.0.0.5:8080';
        the network search and the reading set that module aside with a
        finding - the survey goes on with the others."""
        run = self._new_run()
        run.action_discover()
        self._work(run)
        self._add_module_b(run)
        legacy = run.module_ids.filtered(lambda m: m.ip == MODULE_B_IP)
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE hr_rfid_hw_import_module SET ip = %s WHERE id = %s",
            ("10.0.0.5:8080", legacy.id),
        )
        legacy.invalidate_recordset(["ip"])
        run.action_discover()
        self._work(run)
        self.assertEqual(run.state, "draft", run.last_error)
        self.assertEqual(legacy.status, "unreachable")
        self.assertIn(
            "correct the address",
            legacy.read_error,
            "the operator reads what to do, not a Python text",
        )
        legacy.write({"status": "new", "include": True})  # the operator ticks it anyway
        run.action_read()
        self._work(run)
        self.assertEqual(run.state, "naming", run.last_error)
        self.assertEqual(legacy.read_state, "failed")
        self.assertIn("address", legacy.read_error)
        self.assertTrue(
            run.ctrl_ids.filtered(lambda c: c.address == ADDR_180).read_state == "done",
            "the other module was read",
        )

    def test_a_department_of_another_company_is_refused(self):
        other = self.env["res.company"].create({"name": "Another company (test)"})
        foreign = self.env["hr.department"].create(
            {"name": "Their department", "company_id": other.id}
        )
        run = self._resolved_survey()
        wiz = (
            self.env["hr.rfid.hw.import.options.wiz"]
            .with_context(default_run_id=run.id)
            .create(
                {
                    "run_id": run.id,
                    "default_department_id": foreign.id,
                    "placeholder_owner_type": "employee",
                }
            )
        )
        with self.assertRaises(UserError) as caught:
            wiz.action_start()
        self.assertIn("Another company (test)", caught.exception.args[0])
        self.assertNotEqual(run.state, "importing")

    def test_a_department_of_no_company_is_accepted(self):
        shared = self.env["hr.department"].create(
            {"name": "Department of no company", "company_id": False}
        )
        run = self._resolved_survey()
        self._import(
            run, default_department_id=shared.id, placeholder_owner_type="employee"
        )
        self.assertEqual(run.state, "done", run.last_error)

    def test_a_module_registered_before_the_survey_is_not_pointed_again_even_when_asked_directly(
        self,
    ):
        """The row hides the button; the server refuses too, so no call of the
        action can restart a module that already works here."""
        self.env["hr.rfid.webstack"].sudo().create(
            {
                "name": "Existing module",
                "serial": MODULE_A_SERIAL,
                "active": False,
                "company_id": self.company.id,
            }
        )
        run = self._resolved_survey(upload=False, with_b=False, include_known=True)
        run.issue_ids.filtered(
            lambda i: i.kind == "conflict_webstack"
        ).resolution = "link"
        self._import(run)
        self.assertEqual(run.state, "done", run.last_error)
        module = run.module_ids.filtered(lambda m: m.ip == MODULE_A_IP)
        self.assertTrue(module.webstack_id and module.existing_webstack_id)
        posted = []
        from odoo.addons.hr_rfid.models import hr_rfid_webstack

        self.patch(
            hr_rfid_webstack.requests, "post", lambda url, **kwargs: posted.append(url)
        )
        with self.assertRaises(UserError) as caught:
            module.action_point_to_server()
        self.assertIn(MODULE_A_IP, caught.exception.args[0])
        self.assertEqual(posted, [], "nothing was sent to the module")
        self.assertFalse(module.pointed_at)
        self.assertFalse(self._write_commands())

    # ------------------------------------------------------------ what the operator is told

    def test_a_member_holding_cards_that_were_not_read_is_named_in_the_report(self):
        """A person already here gets the surveyed groups; the access control
        module gives them to all of that person's cards. The operator is told
        which cards the controllers do not know."""
        employee = self.env["hr.employee"].create(
            {"name": "Existing Worker (test)", "department_id": self.department.id}
        )
        Card = self.env["hr.rfid.card"].sudo().with_context(no_hardware_commands=True)
        Card.create(
            {
                "number": "0000100003",
                "card_input_type": "w34",
                "employee_id": employee.id,
                "company_id": self.company.id,
            }
        )
        unread = Card.create(
            {
                "number": "0000777777",
                "card_input_type": "w34",
                "employee_id": employee.id,
                "company_id": self.company.id,
            }
        )
        run = self._survey(with_b=False)
        run.issue_ids.filtered(lambda i: i.kind == "conflict_card").write(
            {"resolution": "link"}
        )
        choose_slot_source(run, ADDR_180)
        run.action_skip_names()
        self._import(run)
        self.assertEqual(run.state, "done", run.last_error)
        warnings = run.issue_ids.filtered(
            lambda i: "not read on these controllers" in i.message
        )
        self.assertEqual(
            len(warnings),
            1,
            "only the person already here has cards that were not read",
        )
        self.assertEqual(warnings.severity, "warning")
        self.assertIn("Existing Worker (test)", warnings.message)
        self.assertIn(unread.number, warnings.message)
        self.assertFalse(self._write_commands())

    def test_the_command_log_opens_from_the_survey_with_its_count(self):
        run = self._survey(with_b=False)
        logs = self.env["hr.rfid.hw.import.cmd.log"].search([("run_id", "=", run.id)])
        self.assertTrue(logs)
        self.assertEqual(run.cmd_log_count, len(logs))
        action = run.action_open_cmd_log()
        self.assertEqual(
            self.env["hr.rfid.hw.import.cmd.log"].search(action["domain"]), logs
        )
        self.assertEqual(run.card_count, len(run.card_ids))
        self.assertEqual(run.person_count, len(run.person_ids))
        self.assertEqual(run.group_count, len(run.group_ids))
        other = self._new_run()
        self.assertEqual(other.cmd_log_count, 0, "each survey counts its own commands")

    def test_an_excel_sheet_too_long_is_refused_instead_of_cut(self):
        """A sheet holds a limited number of rows; the rows past the limit
        would be lost without a word. The operator is sent to the JSON file,
        which holds everything."""
        run = self._survey(with_b=False)
        original = xlsxwriter.Workbook.add_worksheet

        def small_sheets(book, *args, **kwargs):
            sheet = original(book, *args, **kwargs)
            sheet.xls_rowmax = 4
            return sheet

        self.patch(xlsxwriter.Workbook, "add_worksheet", small_sheets)
        with self.assertRaises(UserError) as caught:
            exporter_module.SurveyExporter(run).xlsx_bytes()
        self.assertIn("JSON", caught.exception.args[0])
        self.assertTrue(
            exporter_module.SurveyExporter(run).json_bytes(),
            "the JSON file still works",
        )

    def test_the_cleanup_keeps_the_command_log_of_a_survey_still_in_progress(self):
        parked = self._survey(with_b=False)
        finished = self._survey(with_b=False)
        finished._finish("done")
        stopped = self._survey(with_b=False)
        stopped._finish("failed", "test")
        Log = self.env["hr.rfid.hw.import.cmd.log"]
        old = fields.Datetime.now() - timedelta(days=200)
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE hr_rfid_hw_import_cmd_log SET create_date = %s WHERE run_id IN %s",
            (old, (parked.id, finished.id, stopped.id)),
        )
        Log.invalidate_model(["create_date"])
        Log._gc_cmd_logs()
        self.assertTrue(
            Log.search_count([("run_id", "=", parked.id)]),
            "a survey still open keeps its proof",
        )
        self.assertFalse(
            Log.search_count([("run_id", "in", (finished.id, stopped.id))])
        )

    # ------------------------------------------------------------ what an import cut into pieces must keep

    def test_a_site_imported_in_pieces_is_recognised_on_the_next_survey(self):
        """Every piece writes down what it created; a second survey of the same
        site, months later, creates no twin of anything the pieces made."""
        run = self._resolved_survey()
        self._in_small_passes()
        self._import(run)
        self.assertEqual(run.state, "done", run.last_error)
        ledger = self.env["ir.model.data"].sudo()
        for record in [
            *run.person_ids.mapped("partner_id"),
            *run.card_ids.mapped("card_rec_id"),
        ]:
            self.assertTrue(
                ledger.search_count(
                    [
                        ("module", "=", "__import__"),
                        ("model", "=", record._name),
                        ("res_id", "=", record.id),
                    ]
                ),
                "%s is written down as created by this import" % record.display_name,
            )
        counts = self._counts()
        again = self._survey(include_known=True)
        for issue in again.issue_ids.filtered(lambda i: i.severity == "blocker"):
            issue.resolution = "link"
        choose_slot_source(again, ADDR_180)
        again.person_ids.filtered(lambda p: p.review_state == "blocked").action_split()
        again.action_skip_names()
        self._import(again)
        self.assertEqual(again.state, "done", again.last_error)
        self.assertEqual(self._counts(), counts)

    def test_two_people_with_the_same_name_stay_two_people_when_imported_in_pieces(
        self,
    ):
        """A merged name split back into two people: two records here, each
        with only their own card - never one person with both cards' rights."""
        run = self._resolved_survey()
        namesakes = self._person(run, "Demo Holder One")
        self.assertEqual(len(namesakes), 2)
        self._in_small_passes()
        self._import(run)
        self.assertEqual(run.state, "done", run.last_error)
        self.assertEqual(len(namesakes.mapped("partner_id")), 2)
        for person in namesakes:
            self.assertEqual(
                person.card_ids.mapped("card_rec_id.contact_id"), person.partner_id
            )

    def test_employees_get_their_groups_once_when_imported_in_pieces(self):
        run = self._resolved_survey(upload=False)
        self._in_small_passes()
        self._import(run, placeholder_owner_type="employee")
        self.assertEqual(run.state, "done", run.last_error)
        rels = self.env["hr.rfid.access.group.employee.rel"].search(
            [("access_group_id", "in", run.group_ids.mapped("access_group_id").ids)]
        )
        pairs = [(rel.access_group_id.id, rel.employee_id.id) for rel in rels]
        self.assertTrue(pairs)
        self.assertEqual(len(pairs), len(set(pairs)))
        for group in run.group_ids.filtered("include"):
            for person in group.card_ids.mapped("person_id").filtered("include"):
                self.assertIn(
                    group.access_group_id,
                    person.employee_id.hr_rfid_access_group_ids.mapped(
                        "access_group_id"
                    ),
                )
        self.assertFalse(
            run.issue_ids.filtered(lambda i: "has no department" in i.message)
        )
        self.assertFalse(self._write_commands())

    def test_a_card_left_out_gives_its_holder_no_group(self):
        """The operator unticks a card: its holder must not receive the group
        that card belonged to, or the access control module would open those
        doors on every card the holder has."""
        run = self._resolved_survey(upload=False)
        card = self._card(run, "0000100003")
        left_out_groups = card.group_ids
        self.assertTrue(left_out_groups)
        card.include = False
        holder = card.person_id
        self._import(run)
        self.assertEqual(run.state, "done", run.last_error)
        owner = holder.employee_id or holder.partner_id
        if owner:
            given = owner.hr_rfid_access_group_ids.mapped("access_group_id")
            self.assertFalse(given & left_out_groups.mapped("access_group_id"))
        self.assertFalse(card.card_rec_id)

    def test_an_import_started_again_after_a_failure_says_nothing_twice(self):
        """The import stops half-way, the operator reopens the survey and starts
        the import again: the records are not created twice, and neither is
        any line of the report."""
        run = self._resolved_survey()
        original = importer.HardwareImporter._step_memberships
        calls = []

        def failing_once(step_self):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("simulated failure in the memberships step")
            return original(step_self)

        self.patch(importer.HardwareImporter, "_step_memberships", failing_once)
        self._import(run)
        self.assertEqual(run.state, "failed")
        run.action_reopen()
        self._import(run)
        self.assertEqual(run.state, "done", run.last_error)
        lines = [
            (
                i.kind,
                i.message,
                i.card_id.id,
                i.ctrl_id.id,
                i.module_id.id,
                i.group_id.id,
                i.slot_id.id,
            )
            for i in run.issue_ids.filtered(lambda i: i.phase == "import")
        ]
        self.assertTrue(lines)
        self.assertEqual(len(lines), len(set(lines)), "no line of the report twice")
        self.assertFalse(self._write_commands())

    def test_a_module_answering_for_other_commands_is_told_as_such(self):
        """Another program talking to the module at the same time is named as
        the likely cause - not the cabling, not the power."""
        from ..models.reader import unreachable_label

        label = unreachable_label(self.env, transport.Unreachable("x", kind="skew"))
        self.assertIn("another program", label)

    def test_the_step_keys_are_not_texts_to_translate(self):
        """The catalog holds what the operator reads; the internal names of the
        import steps are not part of it."""
        import polib

        from odoo.tools import file_path

        pot = polib.pofile(
            file_path("hr_rfid_hardware_import/i18n/hr_rfid_hardware_import.pot")
        )
        msgids = {entry.msgid for entry in pot}
        self.assertIn(
            "Members of the access groups", msgids, "the labels of the steps are there"
        )
        self.assertFalse(
            msgids & set(importer.STEPS), sorted(msgids & set(importer.STEPS))
        )

    def test_a_group_too_large_for_one_excel_cell_is_given_as_a_count(self):
        """A group of thousands of cards does not fit one cell; the workbook says
        how many cards it has instead of cutting the list without a word."""
        run = self._survey(with_b=False)
        self.patch(exporter_module, "CELL_MAX_LENGTH", 5)
        group = run.group_ids.filtered(lambda g: len(g.card_ids) > 1)[:1]
        text = exporter_module.SurveyExporter(run)._card_list(group)
        self.assertIn(str(len(group.card_ids)), text)
        self.assertNotIn(group.card_ids[:1].number_display, text)

    def test_an_excel_cell_cut_by_the_library_stops_the_export(self):
        run = self._survey(with_b=False)
        original = xlsxwriter.Workbook.add_worksheet

        def short_cells(book, *args, **kwargs):
            sheet = original(book, *args, **kwargs)
            sheet.xls_strmax = 3
            return sheet

        self.patch(xlsxwriter.Workbook, "add_worksheet", short_cells)
        with self.assertRaises(UserError) as caught:
            exporter_module.SurveyExporter(run).xlsx_bytes()
        self.assertIn("too long for an Excel cell", caught.exception.args[0])
