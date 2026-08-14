from unittest.mock import MagicMock, patch

from odoo.tests import common, tagged


@tagged("post_install", "-at_install", "andromeda_import")
class TestAndromedaImportWizard(common.TransactionCase):
    """The import must be runnable an unlimited number of times.

    The real wizard reads an Andromeda Firebird database through fdb. These
    tests replace that read with canned rows and exercise the wizard itself,
    which is where the "run it again" behaviour lives.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fallback_department = cls.env["hr.department"].create({
            "name": "Import fallback department",
        })
        cls.fallback_company = cls.env["res.partner"].create({
            "name": "Import fallback company",
            "is_company": True,
        })
        cls.WizardModel = cls.env["hr.rfid.andromeda.import.wiz"]
        cls.wizard = cls.WizardModel.with_context(
            defs={
                "default_import_as": "employee",
                "company_dict": "[]",
                "ag_dict": "[]",
            },
        ).create({
            "ip_address": "127.0.0.1",
            "database_path": "test.fdb",
            "default_department": cls.fallback_department.id,
            "default_company": cls.fallback_company.id,
            "users_ids": [],
        })

    def setUp(self):
        super().setUp()
        # No test may reach the Firebird server; every test says what the
        # source is supposed to answer.
        self._source_rows(ag_rows=(), tag_rows=())

    def _source_rows(self, ag_rows=(), tag_rows=()):
        """Make the source database answer with these rows."""
        def fake_sql(_wizard, sql):
            if "AG_USERS" in sql:
                return list(ag_rows)
            if "USERS_TAGDATA" in sql:
                return list(tag_rows)
            return []

        patcher = patch.object(
            type(self.wizard), "do_fb_sql_context", fake_sql,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

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

    def _imported_access_group(self, source_ag_id, name):
        """An access group the import already brought in from the source."""
        group = self.env["hr.rfid.access.group"].create({"name": name})
        self.wizard._mark_imported(group, "ag_%s" % source_ag_id)
        return group

    def _door_and_the_department_allowed_through_it(self, label):
        """A door, and a department whose people may open it."""
        door = self.env["hr.rfid.door"].create({
            "name": "%s door" % label, "number": 1,
        })
        group = self.env["hr.rfid.access.group"].create({"name": "%s group" % label})
        group.add_doors(door)
        department = self.env["hr.department"].create({
            "name": "%s department" % label,
            "hr_rfid_allowed_access_groups": [(4, group.id, 0)],
            "hr_rfid_default_access_group": group.id,
        })
        return door, department

    def _run_the_import(self, department, user):
        """One person, brought in the way the operator brings people in."""
        self.wizard.write({
            "force_default_department": True,
            "default_department": department.id,
        })
        return self.wizard.do_import_user_as_employee(user)

    def _cards_numbered(self, number):
        """Every card carrying this number - switched off ones included."""
        return self.env["hr.rfid.card"].with_context(active_test=False).search([
            ("number", "=", number),
        ])

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

    # -- Running the import a second time ---------------------------------

    def test_a_second_run_does_not_create_a_second_employee(self):
        Employee = self.env["hr.employee"]
        Department = self.env["hr.department"]
        employees_before = Employee.search_count([])
        departments_before = Department.search_count([])
        user = self._fake_user(u_id=400, u_code="EMP400", d_id=400, c_id=400,
                               d_name="Gate", c_name="Plant")

        first = self.wizard.do_import_user_as_employee(user)
        second = self.wizard.do_import_user_as_employee(user)

        self.assertEqual(first, second)
        self.assertEqual(
            Employee.search_count([]), employees_before + 1,
            "Importing the same person again must not create a second employee",
        )
        self.assertEqual(
            Department.search_count([]), departments_before + 1,
            "The department of an already imported person must not be made twice",
        )

    def test_a_second_run_does_not_create_a_second_contact(self):
        Partner = self.env["res.partner"]
        partners_before = Partner.search_count([])
        user = self._fake_user(u_id=401, u_code="CON401", c_id=401,
                               c_name="Visitors Ltd")

        first = self.wizard.create_res_partner(user)
        second = self.wizard.create_res_partner(user)

        self.assertEqual(first, second)
        self.assertEqual(
            Partner.search_count([]), partners_before + 2,
            "The second run must add neither the contact nor their company again",
        )

    def test_a_second_run_does_not_give_an_employee_the_same_access_group_twice(self):
        self._source_rows(ag_rows=[(402, 42, None, None, 1)])
        group = self._imported_access_group(42, "Gate access")
        department = self.env["hr.department"].create({"name": "Shift A"})
        employee = self.env["hr.employee"].create({
            "name": "Second run employee", "department_id": department.id,
        })
        user = self._fake_user(u_id=402)

        self.wizard.create_user_ag_relation(user, employee_id=employee)
        self.wizard.create_user_ag_relation(user, employee_id=employee)

        memberships = employee.hr_rfid_access_group_ids.filtered(
            lambda rel: rel.access_group_id == group,
        )
        self.assertEqual(
            len(memberships), 1,
            "Importing the same person again must not give them the same "
            "access group a second time",
        )

    def test_a_second_run_does_not_give_a_contact_the_same_access_group_twice(self):
        self._source_rows(ag_rows=[(403, 43, None, None, 1)])
        group = self._imported_access_group(43, "Lobby access")
        contact = self.env["res.partner"].create({"name": "Second run contact"})
        user = self._fake_user(u_id=403)

        self.wizard.create_user_ag_relation(user, partner_id=contact)
        self.wizard.create_user_ag_relation(user, partner_id=contact)

        memberships = contact.hr_rfid_access_group_ids.filtered(
            lambda rel: rel.access_group_id == group,
        )
        self.assertEqual(len(memberships), 1)

    def test_an_access_group_a_person_already_had_is_not_given_again(self):
        """Access rights that predate this import must survive untouched.

        Nothing in the database says where such a membership came from, so
        only the (person, access group) check can catch it.
        """
        self._source_rows(ag_rows=[(404, 44, None, None, 1)])
        group = self._imported_access_group(44, "Warehouse access")
        department = self.env["hr.department"].create({
            "name": "Shift B",
            "hr_rfid_allowed_access_groups": [(4, group.id, 0)],
            "hr_rfid_default_access_group": group.id,
        })
        # The employee is given the group by the department, not by us.
        employee = self.env["hr.employee"].create({
            "name": "Existing rights employee", "department_id": department.id,
        })
        self.assertEqual(len(employee.hr_rfid_access_group_ids), 1)
        existing = employee.hr_rfid_access_group_ids

        self.wizard.create_user_ag_relation(self._fake_user(u_id=404),
                                            employee_id=employee)

        self.assertEqual(
            employee.hr_rfid_access_group_ids, existing,
            "An access group the person already had must be left alone",
        )

    def test_a_second_run_does_not_create_a_second_placeholder_group(self):
        AccessGroup = self.env["hr.rfid.access.group"]
        groups_before = AccessGroup.search_count([])

        first = self.wizard._get_placeholder_access_group(45)
        second = self.wizard._get_placeholder_access_group(45)

        self.assertEqual(first, second)
        self.assertEqual(
            AccessGroup.search_count([]), groups_before + 1,
            "The stand-in group must be made once, not once per import run",
        )

    # -- The cards people carry -------------------------------------------

    def test_a_second_run_does_not_hand_out_the_same_card_twice(self):
        """One badge in the customer's hand is one card in Odoo, always.

        Two cards for one badge is not a tidiness problem: the door then has
        two answers for the same number, and whichever one the operator later
        blocks, the other still opens the door.
        """
        self._source_rows(tag_rows=[(600, 1, "6000000001")])
        _door, department = self._door_and_the_department_allowed_through_it("Front")
        user = self._fake_user(u_id=600, u_code="EMP600")

        employee = self._run_the_import(department, user)
        after_first_run = self._cards_numbered("6000000001")
        self.assertEqual(
            len(after_first_run), 1,
            "The first run must bring the person's card in",
        )

        self._run_the_import(department, user)

        self.assertEqual(
            self._cards_numbered("6000000001"), after_first_run,
            "Importing the same person again must not issue their badge a "
            "second time",
        )
        self.assertEqual(
            after_first_run.employee_id, employee,
            "The card must stay with the person it was imported for",
        )

    def test_a_second_run_does_not_let_a_door_see_one_card_twice(self):
        """The door keeps exactly one way in per badge."""
        self._source_rows(tag_rows=[(601, 1, "6000000002")])
        door, department = self._door_and_the_department_allowed_through_it("Back")
        user = self._fake_user(u_id=601, u_code="EMP601")

        self._run_the_import(department, user)
        self.assertEqual(
            len(door.card_rel_ids), 1,
            "An imported card must open the door its department is allowed "
            "through - otherwise this test proves nothing",
        )

        self._run_the_import(department, user)

        self.assertEqual(
            len(door.card_rel_ids), 1,
            "A second run must not leave the door with two ways in for one "
            "physical card",
        )

    def test_a_card_switched_off_in_andromeda_is_not_reissued(self):
        """A badge the customer withdrew must not come back through a re-run.

        Withdrawn cards are archived here, and an archived record is precisely
        the one an ordinary lookup stops finding - so a re-run is where a
        second, working copy of a withdrawn badge would appear.
        """
        self._source_rows(tag_rows=[(602, 0, "6000000003")])
        door, department = self._door_and_the_department_allowed_through_it("Side")
        user = self._fake_user(u_id=602, u_code="EMP602")

        self._run_the_import(department, user)
        self._run_the_import(department, user)

        cards = self._cards_numbered("6000000003")
        self.assertEqual(
            len(cards), 1,
            "A withdrawn badge must not be imported a second time",
        )
        self.assertFalse(
            cards.active,
            "A badge withdrawn in Andromeda must arrive withdrawn here too",
        )
        self.assertFalse(
            door.card_rel_ids,
            "A withdrawn badge must open nothing",
        )

    def test_a_second_run_does_not_hand_a_visitor_the_same_card_twice(self):
        """People kept as contacts carry badges too."""
        self._source_rows(tag_rows=[(603, 1, "6000000004")])
        user = self._fake_user(u_id=603, u_code="CON603", c_id=603,
                               c_name="Visitors Ltd")

        contact = self.wizard.create_res_partner(user)
        after_first_run = self._cards_numbered("6000000004")
        self.assertEqual(
            len(after_first_run), 1,
            "The first run must bring the visitor's card in",
        )

        self.wizard.create_res_partner(user)

        self.assertEqual(
            self._cards_numbered("6000000004"), after_first_run,
            "Importing the same visitor again must not issue their badge a "
            "second time",
        )
        self.assertEqual(after_first_run.contact_id, contact)

    def test_a_second_department_reuses_the_same_placeholder_group(self):
        """Two departments needing a stand-in must share the one group."""
        self._source_rows(ag_rows=[(405, 46, None, None, 1)])
        group = self._imported_access_group(46, "Yard access")
        placeholders = []
        for index in (1, 2):
            department = self.env["hr.department"].create({
                "name": "Placeholder dept %d" % index,
            })
            employee = self.env["hr.employee"].create({
                "name": "Placeholder employee %d" % index,
                "department_id": department.id,
            })
            self.wizard.create_user_ag_relation(
                self._fake_user(u_id=405 + index), employee_id=employee,
            )
            placeholders.append(department.hr_rfid_default_access_group)
        self.assertTrue(placeholders[0])
        self.assertEqual(placeholders[0], placeholders[1])
        self.assertNotEqual(placeholders[0], group)
