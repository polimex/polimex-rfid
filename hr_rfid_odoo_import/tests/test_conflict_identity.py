# -*- coding: utf-8 -*-
"""Regression tests for conflict detection - identity by ID, never by text.

Every case here corresponds to a cross-tenant leak measured on the real Odoo 15
cloud migration (session 9). The conflict detector ran BEFORE the import and
pre-seeded the source->target map by matching TEXT, which overrode the ledger
for the whole run:

* controllers were scanned with an EMPTY domain - the whole source table, in a
  run migrating a single tenant;
* they were matched on ``serial_number`` ALONE while the target constraint is
  ``UNIQUE(serial_number, hw_version)`` - so two controllers of two different
  customers (serial 868, hw 11 and 17) were declared the same device, although
  the database has no objection to both existing;
* cards were matched on ``number`` alone while the constraint is
  ``UNIQUE(number, company_id)`` - the same number under another tenant is
  legitimate, not a collision;
* every match was auto-resolved as ``link`` (the field was ``required=True,
  default='link'``), so the merge happened silently and the blocking check for
  unresolved conflicts was dead code.

Measured damage of the single false controller match: 4 readers, 2 doors and
1 964 user events of one customer ended up inside another customer's company.
"""

from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

SRC_DB = "conflict_src"


class _FakeProxy:
    """Stands in for the XML-RPC ``models`` proxy.

    Records the domain each scan asked for - the empty-domain defect is
    asserted directly on it.
    """

    def __init__(self, data):
        self._data = data
        self.domains = {}

    def execute_kw(self, db, uid, password, model, method, args, kwargs=None):
        assert method == "search_read", method
        self.domains[model] = args[0]
        return [dict(rec) for rec in self._data.get(model, [])]


@tagged("post_install", "-at_install", "rfid_odoo_import", "rfid_import_conflict")
class TestConflictIdentity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mine = cls.env["res.company"].create({"name": "Conflict Tenant A"})
        cls.other = cls.env["res.company"].create({"name": "Conflict Tenant B"})
        cls.ws_other = cls.env["hr.rfid.webstack"].create({
            "name": "B stack", "serial": "900001", "key": "k",
            "company_id": cls.other.id,
        })
        # The target controller that the buggy detector latched onto: same
        # serial as the source one below, DIFFERENT hw_version.
        cls.ctrl_other = cls.env["hr.rfid.ctrl"].create({
            "name": "B ctrl", "ctrl_id": 29, "serial_number": "868",
            "hw_version": "11", "webstack_id": cls.ws_other.id,
        })
        # A card must carry exactly one owner (hr.rfid.card CHECK constraint).
        cls.emp_mine = cls.env["hr.employee"].create({
            "name": "Card holder A", "company_id": cls.mine.id,
        })
        cls.emp_other = cls.env["hr.employee"].create({
            "name": "Card holder B", "company_id": cls.other.id,
        })

    def _wizard(self, source_company_id=101, target_company=None):
        wiz = self.env["hr.rfid.odoo.import.wiz"].create({
            "source_url": "http://localhost:1",
            "source_db": SRC_DB,
            "source_login": "admin",
            "source_password": "x",
        })
        wiz.source_uid = 1
        self.env["hr.rfid.odoo.import.company.line"].create({
            "wizard_id": wiz.id,
            "source_id": source_company_id,
            "source_name": "Source tenant",
            "do_import": True,
            "target_company_id": (target_company or self.mine).id,
        })
        return wiz

    def _detect(self, wiz, data, company_ids=(101,)):
        proxy = _FakeProxy(data)
        wiz._detect_conflicts(proxy, list(company_ids))
        return proxy

    # -- the defect that leaked 1 970 records --------------------------

    def test_partial_key_match_is_not_a_conflict(self):
        """Same serial + DIFFERENT hw_version does not violate the constraint.

        The target key is UNIQUE(serial_number, hw_version); matching on the
        serial alone invents a collision the database would never raise, and
        the invented link dragged the controller's readers, doors and events
        into the other tenant's company.
        """
        wiz = self._wizard()
        self._detect(wiz, {"hr.rfid.ctrl": [
            {"id": 125, "display_name": "Garage", "serial_number": "868",
             "hw_version": "17"},
        ]})
        self.assertFalse(
            wiz.conflict_ids,
            "controller with the same serial but a different hw_version must "
            "not be reported as a conflict - the constraint is on both columns",
        )

    def test_full_key_match_is_a_conflict_and_blocks(self):
        """A real constraint collision is reported AND left undecided."""
        wiz = self._wizard()
        self._detect(wiz, {"hr.rfid.ctrl": [
            {"id": 126, "display_name": "Clash", "serial_number": "868",
             "hw_version": "11"},
        ]})
        self.assertEqual(len(wiz.conflict_ids), 1)
        conflict = wiz.conflict_ids
        self.assertEqual(conflict.target_id, self.ctrl_other.id)
        self.assertFalse(
            conflict.resolution,
            "a collision is reported for the operator to decide - auto-linking "
            "merges two different objects",
        )
        # The warnings compute only speaks on the confirm step - that is the
        # screen where the operator resolves conflicts before starting.
        wiz.state = "confirm"
        wiz._compute_warnings()
        self.assertIn("unresolved_conflicts", wiz.warnings or {})
        self.assertEqual(
            wiz.warnings["unresolved_conflicts"]["level"], "danger",
            "an undecided conflict must BLOCK the run, not merely inform",
        )

    def test_controller_scan_is_company_scoped(self):
        """The controller scan must not read the whole source table.

        hr.rfid.ctrl carries no company_id of its own, so the axis runs through
        the webstack - but an axis there must be.
        """
        wiz = self._wizard()
        proxy = self._detect(wiz, {"hr.rfid.ctrl": []})
        domain = proxy.domains.get("hr.rfid.ctrl")
        self.assertTrue(domain, "empty domain reads every tenant in the source")
        self.assertTrue(
            any(str(leaf[0]).endswith("company_id") for leaf in domain),
            "controller scan is not restricted by company: %r" % (domain,),
        )

    # -- identity comes from the ledger --------------------------------

    def test_ledgered_record_is_never_a_conflict(self):
        """A source id already in the ledger IS the identity - no text match."""
        wiz = self._wizard()
        with patch.object(
            type(wiz), "_ledger_target_id",
            lambda self, importer, model, source_id: self.env[  # noqa: ARG005
                "hr.rfid.ctrl"].browse(1).id,
        ):
            self._detect(wiz, {"hr.rfid.ctrl": [
                {"id": 126, "display_name": "Clash", "serial_number": "868",
                 "hw_version": "11"},
            ]})
        self.assertFalse(
            wiz.conflict_ids,
            "a ledgered record is a re-run, not a collision",
        )

    # -- per-company constraints ---------------------------------------

    def test_card_number_in_another_company_is_not_a_conflict(self):
        """UNIQUE(number, company_id): the same number elsewhere is legitimate."""
        self.env["hr.rfid.card"].create({
            "number": "0000000042", "company_id": self.other.id,
            "employee_id": self.emp_other.id,
        })
        wiz = self._wizard()
        self._detect(wiz, {"hr.rfid.card": [
            {"id": 7, "display_name": "0000000042", "number": "0000000042",
             "company_id": [101, "Source tenant"]},
        ]})
        self.assertFalse(
            wiz.conflict_ids,
            "a card number held by ANOTHER company does not collide - the "
            "constraint is per company",
        )

    def test_card_number_in_the_same_company_is_a_conflict(self):
        """The same number inside the target company is a real collision."""
        self.env["hr.rfid.card"].create({
            "number": "0000000043", "company_id": self.mine.id,
            "employee_id": self.emp_mine.id,
        })
        wiz = self._wizard()
        self._detect(wiz, {"hr.rfid.card": [
            {"id": 8, "display_name": "0000000043", "number": "0000000043",
             "company_id": [101, "Source tenant"]},
        ]})
        self.assertEqual(len(wiz.conflict_ids), 1)
        self.assertFalse(wiz.conflict_ids.resolution)

    def test_empty_key_part_is_not_a_conflict(self):
        """A NULL part of the key cannot collide - PostgreSQL UNIQUE ignores it."""
        wiz = self._wizard()
        self._detect(wiz, {"hr.rfid.ctrl": [
            {"id": 127, "display_name": "No serial", "serial_number": False,
             "hw_version": "11"},
        ]})
        self.assertFalse(wiz.conflict_ids)
