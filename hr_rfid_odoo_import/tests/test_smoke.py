from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_odoo_import")
class TestOdooImportSmoke(TransactionCase):
    """Smoke coverage - checks the import wizard registers, accepts the
    minimum required fields, and the auxiliary log/conflict models can
    be created. Network-dependent flows (action_test_connection,
    action_import) are not exercised here."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wizard = cls.env["hr.rfid.odoo.import.wiz"].create({
            "source_url": "https://example.invalid",
            "source_db": "demo_db",
            "source_login": "admin",
            "source_password": "x",
        })

    def test_wizard_create_starts_in_connection_state(self):
        self.assertEqual(self.wizard.state, "connection")
        self.assertEqual(self.wizard.source_url, "https://example.invalid")
        self.assertTrue(self.wizard.import_hardware,
                        "import_hardware default must be True")

    def test_log_record_persists(self):
        log = self.env["hr.rfid.odoo.import.log"].create({
            "wizard_id": self.wizard.id,
        })
        self.assertTrue(log.id)

    def test_conflict_record_can_be_created(self):
        conflict = self.env["hr.rfid.odoo.import.conflict"].create({
            "wizard_id": self.wizard.id,
        })
        self.assertTrue(conflict.id)

    def test_company_line_create(self):
        line = self.env["hr.rfid.odoo.import.company.line"].create({
            "wizard_id": self.wizard.id,
        })
        self.assertTrue(line.id)
