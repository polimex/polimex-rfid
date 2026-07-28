# -*- coding: utf-8 -*-
"""Memberships the v19 model layer refuses are copied, not dropped (D41).

Both relation classes hold legacy rows in the live Odoo 15 cloud that today's
code would no longer create - the checks are word for word identical in v15,
so the source could not recreate them either:

* 234 employee memberships whose employee has NO department, so
  ``check_access_group`` matches them against an empty set of allowed groups.
  210 of those employees are active, 176 hold a live card and 2 120 card->door
  permissions hang off them - dropping the rows costs 176 people their access.
* 3 contact memberships with overlapping active periods for the same group
  (two of them expiring BEFORE they activate).

The bulk insert is NOT stubbed here: the row has to land in the real table,
under the real constraints, or the test proves nothing.
"""

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.access_importer import AccessImporter
from ..models.importers.base_importer import BaseImporter

SRC_DB = "verbatim_src"


class _FakeSource(BaseImporter):
    """BaseImporter reading in-memory fixtures; the TARGET side stays real."""

    def __init__(self, env, company_map, data):
        self.env = env
        self.source_db = SRC_DB
        self.source_url = "http://localhost:1"
        self.source_uid = 1
        self.source_password = "x"
        self.company_map = company_map
        self.id_map = {}
        self.options = {"import_cards": False}
        self._field_cache = {}
        self._data = data

    def _has_model(self, model):
        return model in self._data

    def _get_source_fields(self, model):
        keys = set()
        for rec in self._data.get(model, []):
            keys |= set(rec)
        return {k: {} for k in keys}

    def _has_field(self, model, field_name):
        return field_name in self._get_source_fields(model)

    def _search_read(self, model, domain, fields, order="id asc", limit=0,
                     include_archived=True):
        return [dict(rec) for rec in self._data.get(model, [])]

    def _read_all(self, model, domain, fields, batch_size=1000):
        return self._search_read(model, domain, fields)


@tagged("post_install", "-at_install", "rfid_odoo_import", "rfid_import_verbatim")
class TestAccessGroupRelVerbatim(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Verbatim Tenant"})
        cls.group = cls.env["hr.rfid.access.group"].create({
            "name": "Verbatim AG", "company_id": cls.company.id,
        })
        cls.other_group = cls.env["hr.rfid.access.group"].create({
            "name": "Verbatim AG 2", "company_id": cls.company.id,
        })
        # The employee that reproduces the defect: NO department at all.
        cls.orphan = cls.env["hr.employee"].create({
            "name": "No Department", "company_id": cls.company.id,
        })
        # ...and one whose department allows the group, for the normal path.
        cls.dept = cls.env["hr.department"].create({
            "name": "Verbatim Dept", "company_id": cls.company.id,
            "hr_rfid_allowed_access_groups": [(6, 0, [cls.group.id])],
        })
        cls.placed = cls.env["hr.employee"].create({
            "name": "With Department", "company_id": cls.company.id,
            "department_id": cls.dept.id,
        })
        cls.contact = cls.env["res.partner"].create({
            "name": "Verbatim Contact", "company_id": cls.company.id,
        })

    def _run(self, data, ledger_seed):
        base = _FakeSource(self.env, {101: self.company.id}, data)
        for model, mapping in ledger_seed.items():
            base.id_map[model] = dict(mapping)
        importer = AccessImporter(base)
        return base, importer

    def _result(self, importer, model):
        for res in importer.results:
            if res.get("model") == model:
                return res
        self.fail("no result reported for %s" % model)

    def _ledgered(self, model, source_id, base):
        xid = base._xml_id_name(model.replace(".", "_"), source_id)
        return self.env["ir.model.data"].search([
            ("module", "=", "__import__"), ("model", "=", model),
            ("name", "=", xid),
        ], limit=1)

    # ------------------------------------------------------------- employees
    def test_membership_of_department_less_employee_is_copied(self):
        model = "hr.rfid.access.group.employee.rel"
        base, importer = self._run(
            {model: [{"id": 7001, "access_group_id": [55, "AG"],
                      "employee_id": [900, "No Department"],
                      "state": True, "internal_state": True}]},
            {"hr.rfid.access.group": {55: self.group.id},
             "hr.employee": {900: self.orphan.id}},
        )
        importer._import_ag_employee_rels()

        rel = self.env[model].search([("employee_id", "=", self.orphan.id)])
        self.assertEqual(len(rel), 1, "the membership must exist in the target")
        self.assertEqual(rel.access_group_id, self.group)
        self.assertTrue(self._ledgered(model, 7001, base),
                        "a copied row still needs its external ID, or a re-run "
                        "duplicates it and reconciliation counts it missing")
        res = self._result(importer, model)
        self.assertEqual(res["imported_count"], 1)
        self.assertEqual(res["skipped_count"], 0,
                         "a copied membership is migrated, not skipped")

    def test_the_orm_path_is_still_used_when_it_works(self):
        """The fallback must not swallow the normal path (and its side effects)."""
        model = "hr.rfid.access.group.employee.rel"
        base, importer = self._run(
            {model: [{"id": 7002, "access_group_id": [55, "AG"],
                      "employee_id": [901, "With Department"], "state": True}]},
            {"hr.rfid.access.group": {55: self.group.id},
             "hr.employee": {901: self.placed.id}},
        )
        calls = []
        original = importer._copy_ag_rels_verbatim
        importer._copy_ag_rels_verbatim = lambda m, c, r: (
            calls.append(r) or original(m, c, r))
        importer._import_ag_employee_rels()

        self.assertEqual(calls, [[]], "nothing should have been refused")
        rel = self.env[model].search([("employee_id", "=", self.placed.id)])
        self.assertEqual(len(rel), 1)
        self.assertEqual(self._result(importer, model)["imported_count"], 1)

    def test_a_copied_row_carries_the_source_values(self):
        model = "hr.rfid.access.group.employee.rel"
        base, importer = self._run(
            {model: [{"id": 7003, "access_group_id": [55, "AG"],
                      "employee_id": [900, "No Department"], "state": True,
                      "activate_on": "2025-03-01 08:00:00",
                      "expiration": "2025-09-01 08:00:00",
                      "visits_counting": True, "permitted_visits": 12,
                      "visits_counter": 5}]},
            {"hr.rfid.access.group": {55: self.group.id},
             "hr.employee": {900: self.orphan.id}},
        )
        importer._import_ag_employee_rels()

        rel = self.env[model].search([("employee_id", "=", self.orphan.id)])
        self.assertEqual(len(rel), 1)
        self.assertEqual(rel.permitted_visits, 12)
        self.assertEqual(rel.visits_counter, 5)
        self.assertTrue(rel.visits_counting)
        self.assertEqual(str(rel.activate_on), "2025-03-01 08:00:00")
        self.assertEqual(str(rel.expiration), "2025-09-01 08:00:00")

    def test_second_run_does_not_duplicate_a_copied_row(self):
        model = "hr.rfid.access.group.employee.rel"
        data = {model: [{"id": 7004, "access_group_id": [55, "AG"],
                         "employee_id": [900, "No Department"], "state": True}]}
        seed = {"hr.rfid.access.group": {55: self.group.id},
                "hr.employee": {900: self.orphan.id}}
        _, first = self._run(data, seed)
        first._import_ag_employee_rels()
        _, second = self._run(data, seed)
        second._import_ag_employee_rels()

        rel = self.env[model].search([("employee_id", "=", self.orphan.id)])
        self.assertEqual(len(rel), 1, "the external ID must make the copy idempotent")
        self.assertEqual(self._result(second, model)["imported_count"], 1)

    def test_unmapped_employee_is_skipped_not_copied(self):
        """A row we cannot place is a gap to report - never a row to force in."""
        model = "hr.rfid.access.group.employee.rel"
        base, importer = self._run(
            {model: [{"id": 7005, "access_group_id": [55, "AG"],
                      "employee_id": [999, "Never imported"], "state": True}]},
            {"hr.rfid.access.group": {55: self.group.id}, "hr.employee": {}},
        )
        importer._import_ag_employee_rels()

        self.assertFalse(self._ledgered(model, 7005, base))
        res = self._result(importer, model)
        self.assertEqual(res["imported_count"], 0)
        self.assertEqual(res["skipped_count"], 1)

    # -------------------------------------------------------------- contacts
    def test_overlapping_contact_periods_are_copied(self):
        model = "hr.rfid.access.group.contact.rel"
        base, importer = self._run(
            {model: [
                {"id": 7101, "access_group_id": [55, "AG"],
                 "contact_id": [700, "Verbatim Contact"], "state": False,
                 "activate_on": "2024-10-30 05:00:00",
                 "expiration": "2024-12-30 05:00:00"},
                # Overlaps the first one - the v19 model layer refuses it.
                {"id": 7102, "access_group_id": [55, "AG"],
                 "contact_id": [700, "Verbatim Contact"], "state": False,
                 "activate_on": "2024-11-26 05:00:00",
                 "expiration": "2025-01-26 05:00:00"},
            ]},
            {"hr.rfid.access.group": {55: self.group.id},
             "res.partner": {700: self.contact.id}},
        )
        importer._import_ag_contact_rels()

        rels = self.env[model].search([("contact_id", "=", self.contact.id)])
        self.assertEqual(len(rels), 2,
                         "both source periods belong in the target audit trail")
        self.assertTrue(self._ledgered(model, 7102, base))
        res = self._result(importer, model)
        self.assertEqual(res["imported_count"], 2)
        self.assertEqual(res["skipped_count"], 0)
