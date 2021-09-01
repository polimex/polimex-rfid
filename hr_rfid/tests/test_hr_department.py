from odoo.tests import common
from .common import create_webstacks, create_acc_grs_cnt, create_contacts, create_card, \
    get_ws_doors, create_departments, create_employees


class DepartmentTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(DepartmentTests, cls).setUpClass()
        cls._env = cls.env['hr.rfid.card.door.rel']
        cls._ws = create_webstacks(cls.env, webstacks=1, controllers=[2, 2, 0x22])
        cls._doors = get_ws_doors(cls._ws)
        cls._acc_grs = create_acc_grs_cnt(cls.env, 4)
        cls._departments = create_departments(cls.env, ['Upstairs Office', 'Downstairs Office'])

        cls._employees = create_employees(cls.env,
                                          ['Max', 'Cooler Max', 'Jacob', 'Andrej'],
                                          [cls._departments[0], cls._departments[1]])
        cls._contacts = create_contacts(cls.env, ['Greg', 'Cooler Greg', 'Richard'])

        cls._cards = [
            create_card(cls.env, '0000000001', cls._employees[0]),
            create_card(cls.env, '0000000002', cls._employees[0]),
            create_card(cls.env, '0000000003', cls._employees[1]),
            create_card(cls.env, '0000000004', cls._employees[2]),
            create_card(cls.env, '0000000005', cls._contacts[0]),
            create_card(cls.env, '0000000006', cls._contacts[2]),
            create_card(cls.env, '0000000007', cls._employees[3]),
        ]

        cls._departments[0].hr_rfid_allowed_access_groups = cls._acc_grs[0] + cls._acc_grs[1]
        cls._departments[1].hr_rfid_allowed_access_groups = cls._acc_grs[1] + cls._acc_grs[2] + cls._acc_grs[3]

        cls._employees[0].add_acc_gr(cls._acc_grs[0])
        cls._employees[1].add_acc_gr(cls._acc_grs[1])
        cls._employees[3].add_acc_gr(cls._acc_grs[3])

        cls._contacts[0].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[1])
        cls._contacts[2].add_acc_gr(cls._acc_grs[2])

        cls._def_ts = cls.env.ref('hr_rfid.hr_rfid_time_schedule_0')
        cls._other_ts = cls.env.ref('hr_rfid.hr_rfid_time_schedule_1')

        cls._acc_grs[0].add_doors(cls._doors[0], cls._def_ts)
        cls._acc_grs[1].add_doors(cls._doors[1], cls._def_ts)
        cls._acc_grs[2].add_doors(cls._doors[2] + cls._doors[3], cls._def_ts)
        cls._acc_grs[3].add_doors(cls._doors[4], cls._other_ts)

    def test_def_acc_gr(self):
        emp = self._employees[2]
        dep = self._departments[0]

        dep.hr_rfid_default_access_group = self._acc_grs[0]

        emp.department_id = dep

        # self.assertEqual(emp.hr_rfid_access_group_ids.access_group_id, self._acc_grs[0])
        self.assertIn(self._acc_grs[0], emp.hr_rfid_access_group_ids.access_group_id)

    def test_write(self):
        emp = self._employees[2]
        dep = self._departments[0]
        emp.department_id = dep

        for acc_gr in dep.hr_rfid_allowed_access_groups:
            emp.add_acc_gr(acc_gr)

        dep.hr_rfid_allowed_access_groups -= self._acc_grs[0]
        self.assertEqual(emp.hr_rfid_access_group_ids.mapped('access_group_id'), self._acc_grs[1])
        dep.hr_rfid_allowed_access_groups -= self._acc_grs[1]
        self.assertFalse(emp.hr_rfid_access_group_ids)
