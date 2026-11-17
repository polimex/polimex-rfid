"""Narrative 11: everything read can be taken away as a file, without importing.

Owner: "всичко изчетено трябва да може да се предложи като файл за експорт без
да се импортира в одоо". A survey of a working site is a record in its own
right - for the customer's file, for another system, for an import later.
"""

import io
import json

import openpyxl

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import ADDR_180, MODULE_A_SERIAL, HwImportCase, choose_slot_source


@tagged("post_install", "-at_install", "rfid_hw_import", "rfid_hw_import_export")
class TestExport(HwImportCase):
    def _export(self, run, file_format, include_commands=False):
        before = self.env["ir.attachment"].search(
            [("res_model", "=", run._name), ("res_id", "=", run.id)]
        )
        wiz = self.env["hr.rfid.hw.import.export.wiz"].create(
            {
                "run_id": run.id,
                "file_format": file_format,
                "include_commands": include_commands,
            }
        )
        action = wiz.action_export()
        self.assertEqual(action["type"], "ir.actions.act_url")
        attachment = (
            self.env["ir.attachment"].search(
                [("res_model", "=", run._name), ("res_id", "=", run.id)]
            )
            - before
        )
        self.assertEqual(len(attachment), 1)
        return attachment

    def test_everything_read_is_in_the_workbook_and_nothing_was_imported(self):
        run = self._survey()
        cards_before = self.env["hr.rfid.card"].search_count([])
        ctrls_before = self.env["hr.rfid.ctrl"].search_count([])
        attachment = self._export(run, "xlsx")
        self.assertTrue(attachment.name.endswith(".xlsx"))
        book = openpyxl.load_workbook(io.BytesIO(attachment.raw))
        titles = book.sheetnames
        for expected in (
            "Modules",
            "Controllers",
            "Schedules",
            "Cards",
            "Card records",
            "Access groups",
            "People",
            "Findings",
            "Raw replies",
        ):
            self.assertTrue(
                any(expected in t for t in titles), "%s in %s" % (expected, titles)
            )
        cards = book[[t for t in titles if "Cards" in t and "records" not in t][0]]
        self.assertEqual(cards.max_row - 1, len(run.card_ids), "one row per card")
        numbers = {row[0] for row in cards.iter_rows(min_row=2, values_only=True)}
        self.assertIn(self._card(run, "0000100001").number_display, numbers)
        records = book[[t for t in titles if "Card records" in t][0]]
        self.assertEqual(
            records.max_row - 1, len(run.ctrl_ids.mapped("card_record_ids"))
        )
        raw = book[[t for t in titles if "Raw replies" in t][0]]
        c180 = run.ctrl_ids.filtered(lambda c: c.address == ADDR_180)
        self.assertIn(
            c180.f0_hex,
            {row[2] for row in raw.iter_rows(min_row=2, values_only=True)},
            "the system information reply itself is in the file",
        )
        controllers = book[
            [t for t in titles if t == "Controllers" or t.startswith("Controllers")][0]
        ]
        self.assertEqual(controllers.max_row - 1, len(run.ctrl_ids))
        self.assertEqual(
            self.env["hr.rfid.card"].search_count([]),
            cards_before,
            "nothing was imported",
        )
        self.assertEqual(self.env["hr.rfid.ctrl"].search_count([]), ctrls_before)
        self.assertFalse(self._write_commands())
        self.assertNotIn("Commands", titles, "the command log is only there on request")

    def test_the_json_document_holds_every_setting_and_every_raw_reply(self):
        run = self._survey()
        attachment = self._export(run, "json", include_commands=True)
        document = json.loads(attachment.raw.decode("utf-8"))
        self.assertEqual(document["format"], "hr_rfid_hardware_import/1")
        self.assertEqual(len(document["modules"]), 2)
        module_a = next(
            m for m in document["modules"] if m["serial"] == MODULE_A_SERIAL
        )
        c180 = next(c for c in module_a["controllers"] if c["address"] == ADDR_180)
        self.assertEqual(
            c180["raw"]["f0"],
            run.ctrl_ids.filtered(lambda c: c.address == ADDR_180).f0_hex,
        )
        self.assertEqual(len(c180["card_records"]), 6)
        self.assertEqual(c180["readers"], 4)
        self.assertEqual(c180["readers_per_door"], {"1": [1, 2], "2": [3, 4]})
        self.assertEqual(
            c180["anti_passback"],
            {
                "readers_1_and_2": True,
                "readers_3_and_4": False,
                "one_zone_for_both_pairs": False,
            },
            "another system reads which reader pair is guarded, not a number to decode",
        )
        self.assertTrue(
            any(s["slot"] == 1 and not s["empty"] for s in c180["schedules"])
        )
        self.assertEqual(len(document["cards"]), len(run.card_ids))
        card1 = next(c for c in document["cards"] if c["number"] == "0000100001")
        self.assertEqual(len(card1["doors"]), 3)
        self.assertTrue(document["commands"], "the command log was asked for")
        self.assertTrue(
            all(
                cmd["command"]
                in (
                    "F0",
                    "F2",
                    "F3",
                    "F4",
                    "F5",
                    "F6",
                    "F7",
                    "F8",
                    "F9",
                    "FB",
                    "FC",
                    "FF",
                    "B0",
                    "B3",
                )
                for cmd in document["commands"]
            ),
            "the log proves only read commands were sent",
        )
        self.assertFalse(self._write_commands())

    def test_nothing_read_means_nothing_to_export(self):
        run = self._new_run()
        with self.assertRaises(UserError):
            run.action_open_export()
        wiz = self.env["hr.rfid.hw.import.export.wiz"].create(
            {"run_id": run.id, "file_format": "json"}
        )
        with self.assertRaises(UserError):
            wiz.action_export()

    def test_the_export_is_still_there_after_the_import(self):
        run = self._survey(with_b=False)
        choose_slot_source(run, ADDR_180)
        run.action_skip_names()
        self._import(run)
        self.assertEqual(run.state, "done", run.last_error)
        attachment = self._export(run, "xlsx")
        book = openpyxl.load_workbook(io.BytesIO(attachment.raw))
        people = book[[t for t in book.sheetnames if "People" in t][0]]
        self.assertEqual(people.max_row - 1, len(run.person_ids))
