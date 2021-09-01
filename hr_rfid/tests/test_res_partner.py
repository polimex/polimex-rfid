from odoo.tests import common
from .common import create_webstacks, create_acc_grs_cnt, create_contacts, create_card, \
    get_ws_doors, create_departments, create_employees

import datetime


class ContactTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(ContactTests, cls).setUpClass()
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

    def test_add_remove_acc_gr(self):
        cont = self._contacts[0]
        ac1 = self._acc_grs[0]

        cont.hr_rfid_access_group_ids.unlink()
        self.assertFalse(cont.hr_rfid_access_group_ids)

        cont.add_acc_gr(ac1)
        self.assertTrue(cont.hr_rfid_access_group_ids)
        rel = cont.hr_rfid_access_group_ids

        try:
            rel.ensure_one()
        except ValueError:
            self.fail("rel.ensure_one() fails when it shouldn't.")

        self.assertEqual(rel.access_group_id, ac1)
        self.assertFalse(rel.expiration)

        date = '11.11.11 11:11:11'
        date_obj = datetime.datetime.strptime(date, '%m.%d.%y %H:%M:%S')
        cont.add_acc_gr(ac1, date_obj)

        self.assertTrue(cont.hr_rfid_access_group_ids)
        rel = cont.hr_rfid_access_group_ids

        try:
            rel.ensure_one()
        except ValueError:
            self.fail("rel.ensure_one() fails when it shouldn't.")

        self.assertEqual(rel.access_group_id, ac1)
        self.assertEqual(rel.expiration, date_obj)

        cont.remove_acc_gr(ac1)
        self.assertFalse(cont.hr_rfid_access_group_ids)

        cont.remove_acc_gr(ac1)
        self.assertFalse(cont.hr_rfid_access_group_ids)
