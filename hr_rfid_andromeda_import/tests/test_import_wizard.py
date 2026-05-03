from unittest.mock import MagicMock

from odoo.tests import common, tagged


@tagged("post_install", "-at_install", "andromeda_import")
class TestAndromedaImportWizard(common.TransactionCase):
    """Smoke + idempotency tests for the Andromeda import wizard.

    The real wizard talks to a Firebird database via fdb. These tests bypass
    the network/DB layer and exercise the helper methods directly with
    plain mocked user records, which is the part that broke when v19
    removed @api.returns.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.WizardModel = cls.env["hr.rfid.andromeda.import.users"]
        cls.wizard = cls.WizardModel.create({})

    @staticmethod
    def _fake_user(**overrides):
        user = MagicMock()
        defaults = dict(
            u_id=1,
            u_code="0001",
            u_name="Test",
            u_fname="Test",
            u_sname="Middle",
            u_lname="User",
            d_id=10,
            d_name="IT",
            c_id=20,
            c_name="Acme",
            get_full_name=MagicMock(return_value="Test Middle User"),
            get_record_for_note=MagicMock(return_value="andromeda raw row"),
        )
        defaults.update(overrides)
        for key, value in defaults.items():
            setattr(user, key, value)
        return user

    def test_create_res_partner_company_creates_record(self):
        user = self._fake_user(c_id=42, c_name="Acme Corp")
        company = self.wizard.create_res_partner_company(user)
        self.assertTrue(company)
        self.assertEqual(company.name, "Acme Corp")
        self.assertTrue(company.is_company)

    def test_create_res_partner_company_is_idempotent(self):
        user = self._fake_user(c_id=43, c_name="Idem Co")
        first = self.wizard.create_res_partner_company(user)
        second = self.wizard.create_res_partner_company(user)
        self.assertEqual(
            first.id, second.id,
            "Re-importing the same Andromeda company must not create a duplicate",
        )

    def test_create_department_creates_record(self):
        dept = self.wizard.create_department(d_id=99, d_name="Logistics")
        self.assertTrue(dept)
        self.assertEqual(dept.name, "Logistics")

    def test_create_department_is_idempotent(self):
        first = self.wizard.create_department(d_id=100, d_name="QA")
        second = self.wizard.create_department(d_id=100, d_name="QA Renamed")
        self.assertEqual(
            first.id, second.id,
            "Existing department lookup must short-circuit creation",
        )
        # Name should not have been re-written by the helper.
        self.assertEqual(first.name, "QA")

    def test_create_employee_creates_record(self):
        user = self._fake_user(u_id=200, u_code="EMP200")
        dept = self.wizard.create_department(d_id=200, d_name="Field Service")
        employee = self.wizard.create_employee(user, dept)
        self.assertTrue(employee)
        self.assertEqual(employee.name, "Test Middle User")
        self.assertEqual(employee.identification_id, "EMP200")
        self.assertEqual(employee.department_id, dept)

    def test_create_employee_is_idempotent(self):
        user = self._fake_user(u_id=201, u_code="EMP201")
        dept = self.wizard.create_department(d_id=201, d_name="Recurring")
        first = self.wizard.create_employee(user, dept)
        second = self.wizard.create_employee(user, dept)
        self.assertEqual(first.id, second.id)

    def test_create_res_partner_uses_default_company_when_forced(self):
        default_company = self.env["res.partner"].create({
            "name": "Default Co", "is_company": True,
        })
        self.wizard.write({
            "force_default_company": True,
            "default_company": default_company.id,
        })
        user = self._fake_user(u_id=300, c_id=999, c_name="Should be ignored")
        partner = self.wizard.create_res_partner(user)
        self.assertEqual(partner.parent_id, default_company)
