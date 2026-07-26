from odoo.tests.common import TransactionCase, tagged

from ..models.importers.base_importer import LEDGER_MODULE, BaseImporter

MODEL = "hr.rfid.event.system"
TABLE = "hr_rfid_event_system"
SRC_DB = "src_test_db"
STAMP = "2001-01-01 00:00:00"


@tagged("post_install", "-at_install", "rfid_odoo_import")
class TestBulkIdempotency(TransactionCase):
    """Bulk SQL rows must be re-runnable without duplicating or losing data.

    The bulk path bypasses the ORM for speed, so it does not get the
    ``ir.model.data`` external ID that makes the ORM import idempotent.
    ``_direct_sql_insert_tracked`` restores that guarantee: it writes an
    external ID per row (same convention as the ORM path) and skips source
    records that already have one - so a second run inserts nothing.

    No network access: ``BaseImporter`` only builds a lazy ServerProxy, and
    these tests exercise the bulk write path exclusively.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.importer = cls._new_importer()

    @classmethod
    def _new_importer(cls):
        """A fresh importer - empty id_map, like a resumed run in a new process."""
        return BaseImporter(
            env=cls.env, source_url="http://localhost:1", source_db=SRC_DB,
            source_uid=1, source_password="x", company_map={}, options={},
        )

    def _insert(self, source_ids, importer=None):
        rows = [(STAMP,) for _ in source_ids]
        return (importer or self.importer)._direct_sql_insert_tracked(
            TABLE, ["timestamp"], rows, MODEL, list(source_ids),
        )

    def _row_count(self):
        self.env.cr.execute(
            "SELECT count(*) FROM hr_rfid_event_system WHERE timestamp = %s", (STAMP,))
        return self.env.cr.fetchone()[0]

    def _xmlids(self):
        self.env.cr.execute(
            "SELECT name, res_id FROM ir_model_data "
            "WHERE module = %s AND model = %s AND name LIKE %s ORDER BY name",
            (LEDGER_MODULE, MODEL, f"rfid_import_{SRC_DB}_hr_rfid_event_system_%"),
        )
        return self.env.cr.fetchall()

    # ── core idempotency ──────────────────────────────────────
    def test_second_run_inserts_nothing(self):
        source_ids = [900001, 900002, 900003]
        self.assertEqual(self._insert(source_ids), (3, 0, 0))
        self.assertEqual(self._row_count(), 3)
        self.assertEqual(len(self._xmlids()), 3)

        # Same source records again - nothing new may be written.
        self.assertEqual(self._insert(source_ids), (0, 3, 0))
        self.assertEqual(self._row_count(), 3, "re-run duplicated bulk rows")
        self.assertEqual(len(self._xmlids()), 3)

    def test_partial_rerun_inserts_only_new_records(self):
        self.assertEqual(self._insert([900010, 900011]), (2, 0, 0))
        # Two already-imported + one new.
        self.assertEqual(self._insert([900010, 900011, 900012]), (1, 2, 0))
        self.assertEqual(self._row_count(), 3)
        self.assertEqual(len(self._xmlids()), 3)

    def test_external_ids_point_at_the_inserted_rows(self):
        self._insert([900020, 900021])
        self.env.cr.execute(
            "SELECT id FROM hr_rfid_event_system WHERE timestamp = %s", (STAMP,))
        real_ids = {r[0] for r in self.env.cr.fetchall()}
        mapped = {res_id for _name, res_id in self._xmlids()}
        self.assertTrue(mapped)
        self.assertLessEqual(mapped, real_ids,
                             "external IDs must resolve to the rows just inserted")

    # ── resume path (a new run must still resolve earlier records) ──
    def test_resumed_run_repopulates_id_map_for_skipped_rows(self):
        """A record imported by an earlier run must stay resolvable.

        Later phases map FKs through id_map; if a resumed run skipped a row
        without re-registering it, those FKs would silently become NULL
        (e.g. balance history losing its vending event link).
        """
        self._insert([900030, 900031])
        target_id = self.importer._get_target_id(MODEL, 900030)

        fresh = self._new_importer()
        self.assertFalse(fresh._get_target_id(MODEL, 900030), "precondition: empty map")
        fresh._direct_sql_insert_tracked(
            TABLE, ["timestamp"], [(STAMP,)], MODEL, [900030])
        self.assertEqual(
            fresh._get_target_id(MODEL, 900030), target_id,
            "a resumed run must resolve records imported by the previous run")

    def test_already_imported_returns_source_to_target_map(self):
        self._insert([900040])
        target_id = self.importer._get_target_id(MODEL, 900040)
        mapping = self.importer.already_imported(MODEL, [900040, 900041])
        self.assertEqual(mapping, {900040: target_id})

    def test_deleted_target_row_is_reimported(self):
        """An external ID whose row is gone must not block re-import."""
        self._insert([900050])
        target_id = self.importer._get_target_id(MODEL, 900050)
        self.env.cr.execute("DELETE FROM hr_rfid_event_system WHERE id = %s", (target_id,))

        self.assertEqual(self.importer.already_imported(MODEL, [900050]), {},
                         "orphan external ID must not count as imported")
        inserted, already, _ = self._insert([900050], importer=self._new_importer())
        self.assertEqual((inserted, already), (1, 0), "row must be re-imported")

    # ── bookkeeping ───────────────────────────────────────────
    def test_id_map_is_populated_for_later_phases(self):
        self._insert([900060])
        self.assertTrue(self.importer._get_target_id(MODEL, 900060),
                        "bulk insert must record the source->target id map")

    def test_row_and_source_id_length_mismatch_raises(self):
        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            self.importer._direct_sql_insert_tracked(
                TABLE, ["timestamp"], [(STAMP,), (STAMP,)], MODEL, [900070])

    def test_empty_input_is_a_noop(self):
        self.assertEqual(
            self.importer._direct_sql_insert_tracked(TABLE, ["timestamp"], [], MODEL, []),
            (0, 0, 0))


@tagged("post_install", "-at_install", "rfid_odoo_import")
class TestBulkConstraintRejection(TransactionCase):
    """A row the database refuses must NOT get an external ID.

    Otherwise the ledger claims the record was imported while the row is
    missing: it is lost silently, counted as imported, and skipped forever on
    every later run. rfid.service.sale carries a real unique constraint, so it
    is used here to force a rejection.
    """

    MODEL = "rfid.service.sale"
    TABLE = "rfid_service_sale"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.env["ir.model"].search_count([("model", "=", cls.MODEL)]) == 0:
            raise cls.skipTest(cls, "rfid_service_base not installed")
        cls.importer = BaseImporter(
            env=cls.env, source_url="http://localhost:1", source_db=SRC_DB,
            source_uid=1, source_password="x", company_map={}, options={},
        )
        cls.env.cr.execute(
            "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid = 'rfid_service_sale'::regclass AND contype = 'u'")
        cls.unique_defs = cls.env.cr.fetchall()

    def test_unique_constraint_exists(self):
        self.assertTrue(self.unique_defs,
                        "test premise: rfid_service_sale must have a unique constraint")

    def test_rejected_row_gets_no_external_id(self):
        access_group = self.env["hr.rfid.access.group"].create({"name": "D35 probe AG"})
        service = self.env["rfid.service"].create({
            "name": "D35 reject probe",
            "access_group_id": access_group.id,
        })
        partner = self.env["res.partner"].create({"name": "D35 probe partner"})
        # partner_id must be set: the unique constraint covers it, and NULLs do
        # not collide in PostgreSQL, so a NULL partner would not trigger it.
        cols = ["service_id", "start_date", "end_date", "partner_id"]
        row = (service.id, "2001-01-01", "2001-01-02", partner.id)

        first, _, first_rejected = self.importer._direct_sql_insert_tracked(
            self.TABLE, cols, [row], self.MODEL, [910001])
        self.assertEqual(first, 1)
        self.assertEqual(first_rejected, 0)

        # Same business key, different source id -> the DB rejects the row.
        second, _, rejected = self.importer._direct_sql_insert_tracked(
            self.TABLE, cols, [row], self.MODEL, [910002])
        self.assertEqual(second, 0, "rejected row must not be counted as imported")
        self.assertEqual(
            rejected, 1,
            "a row the database refused must be reported, not only logged - "
            "otherwise the operator reads 'imported 0' and cannot tell whether "
            "there was nothing to do or everything was refused")

        self.env.cr.execute(
            "SELECT count(*) FROM ir_model_data WHERE module = %s AND model = %s "
            "AND name = %s",
            (LEDGER_MODULE, self.MODEL,
             f"rfid_import_{SRC_DB}_rfid_service_sale_910002"),
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0,
                         "a rejected row must not leave a dangling external ID")
