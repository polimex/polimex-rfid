import json
from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_old_cloud_import")
class TestOldCloudImportIsRepeatable(TransactionCase):
    """The import must be runnable an unlimited number of times.

    Everything these tests touch works off the payload the wizard already
    fetched from the legacy cloud, so no call goes out to the network.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fallback_department = cls.env["hr.department"].create({
            "name": "Old cloud fallback department",
        })
        cls.fallback_company = cls.env["res.partner"].create({
            "name": "Old cloud fallback company",
            "is_company": True,
        })
        cls.wizard = cls.env["hr.rfid.old.cloud.import.wiz"].with_context(
            defs={"default_import_as": "employee"},
        ).create({
            "url_domain": "pc",
            "url_token": "TEST_TOKEN_PLACEHOLDER",
            "default_department": cls.fallback_department.id,
            "default_company": cls.fallback_company.id,
            "users_ids": [],
        })

    @staticmethod
    def _fake_user(u_id, access_groups=(), tags=(), **overrides):
        """A user row as the wizard holds it after reading the cloud."""
        user = MagicMock()
        defaults = dict(
            u_id=u_id,
            u_code="H%04d" % u_id,
            u_name="Cloud",
            u_fname="Cloud",
            u_sname="Q",
            u_lname="User",
            d_id=10,
            d_name="Gate",
            c_id=20,
            c_name="Customer 20",
            json_data=json.dumps({
                "access_groups": list(access_groups),
                "tags": list(tags),
            }),
            get_full_name=MagicMock(return_value="Cloud Q User"),
            get_record_for_note=MagicMock(return_value="old cloud raw row"),
        )
        defaults.update(overrides)
        for key, value in defaults.items():
            setattr(user, key, value)
        return user

    @staticmethod
    def _source_access_group(source_ag_id, name):
        return {
            "id": source_ag_id,
            "name": name,
            "pivot": {"start": False, "end": False},
        }

    def _imported_access_group(self, source_ag_id, name):
        """An access group the import already brought in from the cloud."""
        group = self.env["hr.rfid.access.group"].create({"name": name})
        self.wizard._mark_imported(group, "ag_%s" % source_ag_id)
        return group

    @staticmethod
    def _source_tag(source_tag_id, number):
        return {"id": source_tag_id, "number": number}

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

    def test_a_second_run_does_not_create_a_second_employee(self):
        Employee = self.env["hr.employee"]
        Department = self.env["hr.department"]
        employees_before = Employee.search_count([])
        departments_before = Department.search_count([])
        user = self._fake_user(500)

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
        user = self._fake_user(501)

        first = self.wizard.create_res_partner(user)
        second = self.wizard.create_res_partner(user)

        self.assertEqual(first, second)
        self.assertEqual(
            Partner.search_count([]), partners_before + 2,
            "The second run must add neither the contact nor their company again",
        )

    def test_a_second_run_does_not_give_an_employee_the_same_access_group_twice(self):
        group = self._imported_access_group(52, "Gate access")
        user = self._fake_user(502, access_groups=[
            self._source_access_group(52, "Gate access"),
        ])
        department = self.env["hr.department"].create({"name": "Cloud shift A"})
        employee = self.env["hr.employee"].create({
            "name": "Second run employee", "department_id": department.id,
        })

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
        group = self._imported_access_group(53, "Lobby access")
        user = self._fake_user(503, access_groups=[
            self._source_access_group(53, "Lobby access"),
        ])
        contact = self.env["res.partner"].create({"name": "Second run contact"})

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
        group = self._imported_access_group(54, "Warehouse access")
        user = self._fake_user(504, access_groups=[
            self._source_access_group(54, "Warehouse access"),
        ])
        department = self.env["hr.department"].create({
            "name": "Cloud shift B",
            "hr_rfid_allowed_access_groups": [(4, group.id, 0)],
            "hr_rfid_default_access_group": group.id,
        })
        # The employee is given the group by the department, not by us.
        employee = self.env["hr.employee"].create({
            "name": "Existing rights employee", "department_id": department.id,
        })
        self.assertEqual(len(employee.hr_rfid_access_group_ids), 1)
        existing = employee.hr_rfid_access_group_ids

        self.wizard.create_user_ag_relation(user, employee_id=employee)

        self.assertEqual(
            employee.hr_rfid_access_group_ids, existing,
            "An access group the person already had must be left alone",
        )

    def test_a_second_run_does_not_create_a_second_placeholder_group(self):
        AccessGroup = self.env["hr.rfid.access.group"]
        groups_before = AccessGroup.search_count([])

        first = self.wizard._get_placeholder_access_group(55)
        second = self.wizard._get_placeholder_access_group(55)

        self.assertEqual(first, second)
        self.assertEqual(
            AccessGroup.search_count([]), groups_before + 1,
            "The stand-in group must be made once, not once per import run",
        )

    def test_a_second_department_reuses_the_same_placeholder_group(self):
        """Two departments needing a stand-in must share the one group."""
        group = self._imported_access_group(56, "Yard access")
        placeholders = []
        for index in (1, 2):
            department = self.env["hr.department"].create({
                "name": "Cloud placeholder dept %d" % index,
            })
            employee = self.env["hr.employee"].create({
                "name": "Cloud placeholder employee %d" % index,
                "department_id": department.id,
            })
            user = self._fake_user(505 + index, access_groups=[
                self._source_access_group(56, "Yard access"),
            ])
            self.wizard.create_user_ag_relation(user, employee_id=employee)
            placeholders.append(department.hr_rfid_default_access_group)
        self.assertTrue(placeholders[0])
        self.assertEqual(placeholders[0], placeholders[1])
        self.assertNotEqual(placeholders[0], group)

    # -- The cards people carry -------------------------------------------

    def test_a_second_run_does_not_hand_out_the_same_card_twice(self):
        """One badge in the customer's hand is one card in Odoo, always.

        Two cards for one badge is not a tidiness problem: the door then has
        two answers for the same number, and whichever one the operator later
        blocks, the other still opens the door.
        """
        _door, department = self._door_and_the_department_allowed_through_it("Front")
        user = self._fake_user(600, tags=[self._source_tag(600, "6100000001")])

        employee = self._run_the_import(department, user)
        after_first_run = self._cards_numbered("6100000001")
        self.assertEqual(
            len(after_first_run), 1,
            "The first run must bring the person's card in",
        )

        self._run_the_import(department, user)

        self.assertEqual(
            self._cards_numbered("6100000001"), after_first_run,
            "Importing the same person again must not issue their badge a "
            "second time",
        )
        self.assertEqual(
            after_first_run.employee_id, employee,
            "The card must stay with the person it was imported for",
        )

    def test_a_second_run_does_not_let_a_door_see_one_card_twice(self):
        """The door keeps exactly one way in per badge."""
        door, department = self._door_and_the_department_allowed_through_it("Back")
        user = self._fake_user(601, tags=[self._source_tag(601, "6100000002")])

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

    def test_a_second_run_does_not_hand_a_visitor_the_same_card_twice(self):
        """People kept as contacts carry badges too."""
        user = self._fake_user(602, tags=[self._source_tag(602, "6100000003")])

        contact = self.wizard.create_res_partner(user)
        after_first_run = self._cards_numbered("6100000003")
        self.assertEqual(
            len(after_first_run), 1,
            "The first run must bring the visitor's card in",
        )

        self.wizard.create_res_partner(user)

        self.assertEqual(
            self._cards_numbered("6100000003"), after_first_run,
            "Importing the same visitor again must not issue their badge a "
            "second time",
        )
        self.assertEqual(after_first_run.contact_id, contact)

    def test_the_two_clouds_never_share_an_external_id(self):
        """my.polimex.online and schoolsafety.online number their records
        independently, so the same number must not stand for one person."""
        polimex_cloud = self.wizard._xml_id("hr.employee", "u_7")
        self.wizard.url_domain = "ss"
        school_cloud = self.wizard._xml_id("hr.employee", "u_7")
        self.assertNotEqual(polimex_cloud, school_cloud)
