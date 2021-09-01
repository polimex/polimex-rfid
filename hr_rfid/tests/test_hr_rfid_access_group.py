from odoo.tests import common
from odoo import exceptions
from .common import create_webstacks, create_acc_grs_cnt, create_contacts, create_card, \
    get_ws_doors, create_departments, create_employees


class AccessGroupTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(AccessGroupTests, cls).setUpClass()
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

    def find_card_door_rel(self, card, door):
        return self._env.search([ ('card_id', '=', card.id), ('door_id', '=', door.id) ])

    def test_add_del_doors(self):
        acc_gr = create_acc_grs_cnt(self.env, 1)
        rel_env = self.env['hr.rfid.card.door.rel']
        door = self._doors[0]
        self._contacts[0].remove_acc_gr(self._acc_grs[0])
        self._contacts[1].remove_acc_gr(self._acc_grs[1])
        self._contacts[2].remove_acc_gr(self._acc_grs[2])

        rel_env.search([]).unlink()

        acc_gr.add_doors(door)
        self.assertFalse(rel_env.search([]).exists())
        self.assertEqual(len(acc_gr.door_ids), 1)
        self.assertEqual(acc_gr.door_ids.time_schedule_id, self._def_ts)

        try:
            acc_gr.add_doors(door, self._def_ts)
        except exceptions.ValidationError:
            self.fail("acc_gr.add_doors failed when it wasn't supposed to.")
        self.assertFalse(rel_env.search([]).exists())
        self.assertEqual(len(acc_gr.door_ids), 1)
        self.assertEqual(acc_gr.door_ids.time_schedule_id, self._def_ts)

        with self.assertRaises(exceptions.ValidationError):
            acc_gr.add_doors(door, self._other_ts)

        acc_gr.del_doors(door)
        self.assertFalse(rel_env.search([]).exists())
        self.assertEqual(len(acc_gr.door_ids), 0)

        self._contacts[0].add_acc_gr(acc_gr)
        self._contacts[1].add_acc_gr(acc_gr)
        self._contacts[2].add_acc_gr(acc_gr)

        cards = self._contacts.mapped('hr_rfid_card_ids')

        acc_gr.add_doors(door)
        rels = self.env['hr.rfid.card.door.rel']
        for card in cards:
            rel = self.find_card_door_rel(card, door)
            rels += rel
            self.assertTrue(rel.exists())
            self.assertEqual(rel.time_schedule_id, self._def_ts)

        try:
            acc_gr.add_doors(door, self._def_ts)
        except exceptions.ValidationError:
            self.fail("acc_gr.add_doors failed when it wasn't supposed to.")
        new_rels = rel_env.search([ ('door_id', '=', door.id), ('card_id', 'in', cards.ids) ])
        self.assertEqual(len(new_rels), len(rels))
        self.assertCountEqual(rels, new_rels)
        self.assertEqual(rels.mapped('time_schedule_id'), self._def_ts)

        with self.assertRaises(exceptions.ValidationError):
            acc_gr.add_doors(door, self._other_ts)

        acc_gr.del_doors(door)
        new_rels = rel_env.search([])
        self.assertFalse(rels.exists())
        self.assertFalse(new_rels.exists())

    def test_inheritance_fields(self):
        # Picture:
        #      A0   A1
        #     /|    /
        #    / |   /
        #   /  |  /
        #  |   | /
        #  |   |/
        #  |   A2   A3
        #  |   /|   /|
        #  |  / |  / |
        #  | /  | /  |
        #  |/   |/   |
        #  A4  A5   A6
        #  |         |\
        #  |         | \
        #  |         |  \
        #  A7        A8  A9
        #  |
        #  |
        #  A10

        acc_grs = create_acc_grs_cnt(self.env, 11)
        acc_grs[0].inherited_ids = acc_grs[2] + acc_grs[4]
        acc_grs[1].inherited_ids = acc_grs[2]
        acc_grs[2].inherited_ids = acc_grs[4] + acc_grs[5]
        acc_grs[3].inherited_ids = acc_grs[5] + acc_grs[6]
        acc_grs[4].inherited_ids = acc_grs[7]
        acc_grs[6].inherited_ids = acc_grs[8] + acc_grs[9]
        acc_grs[7].inherited_ids = acc_grs[10]

        empty_acc_grs = self.env['hr.rfid.access.group']

        self.assertCountEqual(acc_grs[0].inheritor_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[1].inheritor_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[2].inheritor_ids, acc_grs[0] + acc_grs[1])
        self.assertCountEqual(acc_grs[3].inheritor_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[4].inheritor_ids, acc_grs[0] + acc_grs[2])
        self.assertCountEqual(acc_grs[5].inheritor_ids, acc_grs[2] + acc_grs[3])
        self.assertCountEqual(acc_grs[6].inheritor_ids, acc_grs[3])
        self.assertCountEqual(acc_grs[7].inheritor_ids, acc_grs[4])
        self.assertCountEqual(acc_grs[8].inheritor_ids, acc_grs[6])
        self.assertCountEqual(acc_grs[9].inheritor_ids, acc_grs[6])
        self.assertCountEqual(acc_grs[10].inheritor_ids, acc_grs[7])

        acc_grs[0].inheritor_ids = empty_acc_grs
        acc_grs[1].inheritor_ids = empty_acc_grs
        acc_grs[2].inheritor_ids = empty_acc_grs
        acc_grs[3].inheritor_ids = empty_acc_grs
        acc_grs[4].inheritor_ids = empty_acc_grs
        acc_grs[5].inheritor_ids = empty_acc_grs
        acc_grs[6].inheritor_ids = empty_acc_grs
        acc_grs[7].inheritor_ids = empty_acc_grs
        acc_grs[8].inheritor_ids = empty_acc_grs
        acc_grs[9].inheritor_ids = empty_acc_grs
        acc_grs[10].inheritor_ids = empty_acc_grs

        self.assertCountEqual(acc_grs[0].inherited_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[1].inherited_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[2].inherited_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[3].inherited_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[4].inherited_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[5].inherited_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[6].inherited_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[7].inherited_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[8].inherited_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[9].inherited_ids, empty_acc_grs)
        self.assertCountEqual(acc_grs[10].inherited_ids, empty_acc_grs)

        acc_grs[2].inheritor_ids = acc_grs[0] + acc_grs[1]
        acc_grs[4].inheritor_ids = acc_grs[0] + acc_grs[2]
        acc_grs[5].inheritor_ids = acc_grs[2] + acc_grs[3]
        acc_grs[6].inheritor_ids = acc_grs[3]
        acc_grs[7].inheritor_ids = acc_grs[4]
        acc_grs[8].inheritor_ids = acc_grs[6]
        acc_grs[9].inheritor_ids = acc_grs[6]
        acc_grs[10].inheritor_ids = acc_grs[7]

        self.assertCountEqual(acc_grs[0].inherited_ids, acc_grs[2] + acc_grs[4])
        self.assertCountEqual(acc_grs[1].inherited_ids, acc_grs[2])
        self.assertCountEqual(acc_grs[2].inherited_ids, acc_grs[4] + acc_grs[5])
        self.assertCountEqual(acc_grs[3].inherited_ids, acc_grs[5] + acc_grs[6])
        self.assertCountEqual(acc_grs[4].inherited_ids, acc_grs[7])
        self.assertCountEqual(acc_grs[6].inherited_ids, acc_grs[8] + acc_grs[9])
        self.assertCountEqual(acc_grs[7].inherited_ids, acc_grs[10])

    def test_inheritance_rels(self):
        empty_acc_gr = self.env['hr.rfid.access.group']

        a0 = self._acc_grs[0]
        a1 = self._acc_grs[1]
        a2 = self._acc_grs[2]

        a0_doors = a0.door_ids.mapped('door_id')
        a0_emps = a0.employee_ids.mapped('employee_id')
        a0_conts = a0.contact_ids.mapped('contact_id')
        a0_doors_orig = a0.door_ids.mapped('door_id')
        a0_emps_orig = a0.employee_ids.mapped('employee_id')
        a0_conts_orig = a0.contact_ids.mapped('contact_id')

        a1_doors = a1.door_ids.mapped('door_id')
        a1_emps = a1.employee_ids.mapped('employee_id')
        a1_conts = a1.contact_ids.mapped('contact_id')
        a1_doors_orig = a1.door_ids.mapped('door_id')
        a1_emps_orig = a1.employee_ids.mapped('employee_id')
        a1_conts_orig = a1.contact_ids.mapped('contact_id')

        a2_doors = a2.door_ids.mapped('door_id')
        a2_emps = a2.employee_ids.mapped('employee_id')
        a2_conts = a2.contact_ids.mapped('contact_id')
        a2_doors_orig = a2.door_ids.mapped('door_id')
        a2_emps_orig = a2.employee_ids.mapped('employee_id')
        a2_conts_orig = a2.contact_ids.mapped('contact_id')

        a0.inherited_ids = empty_acc_gr
        a0.inheritor_ids = empty_acc_gr
        a1.inherited_ids = empty_acc_gr
        a1.inheritor_ids = empty_acc_gr
        a2.inherited_ids = empty_acc_gr
        a2.inheritor_ids = empty_acc_gr

        a0.inherited_ids += a1
        a0_doors += a1_doors_orig
        a1_emps += a0_emps_orig
        a1_conts += a0_conts_orig
        self.assertEqual(a0.get_all_doors(), a0_doors)
        self.assertEqual(a0.get_all_employees(), a0_emps)
        self.assertEqual(a0.get_all_contacts(), a0_conts)
        self.assertEqual(a1.get_all_doors(), a1_doors)
        self.assertEqual(a1.get_all_employees(), a1_emps)
        self.assertEqual(a1.get_all_contacts(), a1_conts)

        door = a1_doors_orig
        cards = a0_emps.mapped('hr_rfid_card_ids') + a0_conts.mapped('hr_rfid_card_ids')
        for card in cards:
            rel = self.find_card_door_rel(card, door)
            self.assertTrue(rel)

        a1.inherited_ids += a2
        a0_doors += a2_doors_orig
        a1_doors += a2_doors_orig
        a2_emps += a0_emps_orig
        a2_emps += a1_emps_orig
        a2_conts += a0_conts_orig
        a2_conts += a1_conts_orig
        self.assertEqual(a0.get_all_doors(), a0_doors)
        self.assertEqual(a0.get_all_employees(), a0_emps)
        self.assertEqual(a0.get_all_contacts(), a0_conts)
        self.assertEqual(a1.get_all_doors(), a1_doors)
        self.assertEqual(a1.get_all_employees(), a1_emps)
        self.assertEqual(a1.get_all_contacts(), a1_conts)
        self.assertEqual(a2.get_all_doors(), a2_doors)
        self.assertEqual(a2.get_all_employees(), a2_emps)
        self.assertEqual(a2.get_all_contacts(), a2_conts)

        cards = a2_emps.mapped('hr_rfid_card_ids') + a2_conts.mapped('hr_rfid_card_ids')
        for door in a2_doors_orig:
            for card in cards:
                rel = self.find_card_door_rel(card, door)
                self.assertTrue(rel)

        a0.inherited_ids -= a1
        a0_doors -= a1_doors_orig
        a0_doors -= a2_doors_orig
        a1_emps -= a1_emps_orig
        a1_conts -= a0_conts_orig
        a2_emps -= a0_emps_orig
        a2_conts -= a0_conts_orig

        cards = a0_emps.mapped('hr_rfid_card_ids') + a0_conts.mapped('hr_rfid_card_ids')
        for door in a2_doors_orig:
            for card in cards:
                rel = self.find_card_door_rel(card, door)
                self.assertFalse(rel)
