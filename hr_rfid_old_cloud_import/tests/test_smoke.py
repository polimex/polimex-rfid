from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_old_cloud_import")
class TestOldCloudImportSmoke(TransactionCase):
    """Smoke coverage — wizard records persist and the helper formatters
    produce stable strings the controllers can consume."""

    def test_welcome_wizard_create(self):
        wiz = self.env["hr.rfid.old.cloud.welcome.wiz"].create({})
        self.assertTrue(wiz.id)

    def test_import_wiz_model_is_registered(self):
        Model = self.env["hr.rfid.old.cloud.import.wiz"]
        self.assertEqual(Model._name, "hr.rfid.old.cloud.import.wiz")

    def test_import_user_get_full_name(self):
        user_row = self.env["hr.rfid.old.cloud.import.users"].create({
            "u_id": 1,
            "u_code": "0001",
            "u_name": "Joe",
            "u_fname": "John",
            "u_sname": "Q",
            "u_lname": "Public",
        })
        # get_full_name composes a display string from the parts.
        full = user_row.get_full_name()
        self.assertIsInstance(full, str)
        self.assertIn("John", full)

    def test_import_user_get_record_for_note(self):
        user_row = self.env["hr.rfid.old.cloud.import.users"].create({
            "u_id": 2,
            "u_code": "0002",
            "u_name": "Test",
        })
        note = user_row.get_record_for_note()
        self.assertIsInstance(note, str)
