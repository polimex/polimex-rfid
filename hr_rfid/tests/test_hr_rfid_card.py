from odoo import api, exceptions
from odoo.tests import common
from .common import create_webstacks, create_acc_grs_cnt, create_employees, create_contacts, create_card, \
    create_departments, card_door_rels_search, get_ws_doors
from random import randint
from psycopg2 import IntegrityError


def create_unique_cards(env: api.Environment, owners: list = None):
    cards = env['hr.rfid.card']

    if owners is None:
        return cards

    current_numbers = []

    for owner in owners:
        while True:
            new_number = ''
            for __ in range(10):
                new_number += str(randint(0, 9))
            if new_number not in current_numbers:
                current_numbers.append(new_number)
                break
        cards += create_card(env, new_number, owner)

    return cards


class CardTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(CardTests, cls).setUpClass()
        cls._ws = create_webstacks(cls.env, webstacks=1, controllers=[2, 2, 0x22])
        cls._doors = get_ws_doors(cls._ws)
        cls._acc_grs = create_acc_grs_cnt(cls.env, 4)
        cls._departments = create_departments(cls.env, ['Upstairs Office', 'Downstairs Office'])

        cls._employees = create_employees(cls.env,
                                          ['Max', 'Cooler Max', 'Jacob', 'Andrej'],
                                          [cls._departments[0], cls._departments[1]])
        cls._contacts = create_contacts(cls.env, ['Greg', 'Cooler Greg', 'Richard'])

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

    def test_get_owner_fns(self):
        env = self.env
        card = create_card(env, '0000000001', self._employees[0])
        self.assertEqual(card.get_owner(), self._employees[0])
        card = create_card(env, '0000000002', self._contacts[0])
        self.assertEqual(card.get_owner(), self._contacts[0])

    def test_get_potential_access_doors(self):
        env = self.env
        card1 = create_card(env, '0000000001', self._employees[0])
        card2 = create_card(env, '0000000002', self._contacts[2])

        potential_doors = [ (self._doors[0], self._def_ts) ]
        self.assertCountEqual(card1.get_potential_access_doors(), potential_doors)

        potential_doors = [ (self._doors[2], self._def_ts), (self._doors[3], self._def_ts) ]
        self.assertCountEqual(card2.get_potential_access_doors(), potential_doors)

        self._contacts[2].add_acc_gr(self._acc_grs[3])
        potential_doors.append((self._doors[4], self._other_ts))
        self.assertCountEqual(card2.get_potential_access_doors(), potential_doors)

        potential_doors = [ (self._doors[4], self._other_ts) ]
        self.assertCountEqual(card2.get_potential_access_doors(self._acc_grs[3]), potential_doors)

        potential_doors = [ ]
        self.assertCountEqual(card2.get_potential_access_doors(self._acc_grs[0]), potential_doors)

    def test_door_compatible(self):
        env = self.env
        card = create_card(env, '0000000001', self._employees[0])
        door = self._doors[0]

        other_card_type = env.ref('hr_rfid.hr_rfid_card_type_1')

        self.assertTrue(card.door_compatible(door))

        card.card_type = other_card_type
        self.assertFalse(card.door_compatible(door))

        door.card_type = other_card_type
        self.assertTrue(card.door_compatible(door))

        card.cloud_card = False
        self.assertTrue(card.door_compatible(door))

        door.controller_id.external_db = True
        self.assertTrue(card.door_compatible(door))

        card.cloud_card = True
        self.assertFalse(card.door_compatible(door))

    def test_card_ready(self):
        env = self.env
        card = create_card(env, '0000000001', self._employees[0])

        self.assertTrue(card.card_ready())

        card.card_active = False
        self.assertFalse(card.card_ready())

    def test_create(self):
        # Check if creating a card with a length different from 10 adds leading zeroes
        card = create_card(self.env, '123', self._employees[0])
        self.assertEqual(card.number, '0000000123')

        # Check if creating a card with invalid symbols raises
        with self.assertRaises(exceptions.ValidationError):
            create_card(self.env, '123456789a', self._employees[0])

        # Check if creating a card with 2 owners raises
        with self.assertRaises(exceptions.ValidationError):
            self.env['hr.rfid.card'].create({
                'number': '0123456789',
                'employee_id': self._employees[0].id,
                'contact_id': self._contacts[0].id,
            })

        cards = create_unique_cards(self.env, owners=[self._employees[0], self._employees[1],
                                                      self._contacts[0], self._contacts[1]])

        # Check if creating a card with the same number raises
        with self.assertRaises(IntegrityError):
            create_card(self.env, cards[0].number, self._employees[0])

    def test_create_doors_relations(self):
        env = self.env
        card1n = '0000000001'
        card2n = '0000000002'
        rels_env = env['hr.rfid.card.door.rel']

        card = create_card(env, card1n, self._employees[0])
        rels = card_door_rels_search(self.env, card, self._doors[0])
        self.assertNotEqual(rels, rels_env, msg='Relation was not created for door 1 after creating card 1!')

        card = create_card(env, card2n, self._contacts[2])

        rels = card_door_rels_search(self.env, card, self._doors[2])
        self.assertNotEqual(rels, rels_env, msg='Relation was not created for door 3 after creating card 1!')

        rels = card_door_rels_search(self.env, card, self._doors[3])
        self.assertNotEqual(rels, rels_env, msg='Relation was not created for door 4 after creating card 1!')

    def test_write_card_number(self):
        env = self.env
        card1n = '0000000001'
        card2n = '0000000002'

        card = create_card(env, card1n, self._employees[0])
        rel = card_door_rels_search(env, card, self._doors[0])
        self.assertTrue(rel.exists())

        card.write({ 'number': card1n })
        self.assertTrue(rel.exists())

        card.write({ 'number': card2n })
        self.assertTrue(rel.exists())

    def test_write_card_owner(self):
        env = self.env
        card = create_card(env, '0000000001', self._employees[0])

        card.write({ 'employee_id': self._employees[1].id })

        rel = card_door_rels_search(env, card, self._doors[0])
        self.assertEqual(len(rel), 0)
        rel = card_door_rels_search(env, card, self._doors[1])
        self.assertEqual(len(rel), 1)

    def test_write_card_owner_emp_to_cont(self):
        env = self.env
        card = create_card(env, '0000000001', self._employees[0])

        with self.assertRaises(exceptions.ValidationError):
            card.write({ 'contact_id': self._contacts[2].id })

        card.write({ 'employee_id': False, 'contact_id': self._contacts[2].id })

        rel = card_door_rels_search(env, card, self._doors[0])
        self.assertEqual(len(rel), 0)
        rel = card_door_rels_search(env, card, self._doors[2])
        self.assertEqual(len(rel), 1)
        rel = card_door_rels_search(env, card, self._doors[3])
        self.assertEqual(len(rel), 1)

    def test_write_card_active(self):
        env = self.env

        card = create_card(env, '0000000001', self._employees[0])
        rel = card_door_rels_search(env, card, self._doors[0])
        self.assertEqual(len(rel), 1)

        card.write({ 'card_active': False })
        rel = card_door_rels_search(env, card, self._doors[0])
        self.assertEqual(len(rel), 0)

        card.write({ 'card_active': True })
        rel = card_door_rels_search(env, card, self._doors[0])
        self.assertEqual(len(rel), 1)

    def test_write_card_type(self):
        env = self.env

        card = create_card(env, '0000000001', self._employees[0])
        rel = card_door_rels_search(env, card, self._doors[0])
        self.assertEqual(len(rel), 1)

        card.write({ 'card_type': env.ref('hr_rfid.hr_rfid_card_type_1').id })
        rel = card_door_rels_search(env, card, self._doors[0])
        self.assertEqual(len(rel), 0)

        card.write({ 'card_type': env.ref('hr_rfid.hr_rfid_card_type_def').id })
        rel = card_door_rels_search(env, card, self._doors[0])
        self.assertEqual(len(rel), 1)

    def test_write_card_cloud(self):
        env = self.env

        card = create_card(env, '0000000001', self._employees[3])
        rel = card_door_rels_search(env, card, self._doors[4])
        self.assertEqual(len(rel), 0)

        card.write({ 'cloud_card': False })
        rel = card_door_rels_search(env, card, self._doors[4])
        self.assertEqual(len(rel), 1)

        card.write({ 'cloud_card': True })
        rel = card_door_rels_search(env, card, self._doors[4])
        self.assertEqual(len(rel), 0)


class CardDoorRelTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(CardDoorRelTests, cls).setUpClass()
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

    def get_all_rels(self):
        return self._env.search([])

    def test_update_card_rels(self):
        rel_env = self._env

        self.get_all_rels().unlink()
        card = self._cards[0]
        rel_env.update_card_rels(card)
        ret = self.get_all_rels()
        ret = [ (a.door_id, a.time_schedule_id) for a in ret ]
        expected = [ (self._doors[0], self._def_ts) ]
        self.assertCountEqual(ret, expected)

        self.get_all_rels().unlink()
        card = self._cards[3]
        rel_env.update_card_rels(card)
        ret = self.get_all_rels()
        ret = [ (a.door_id, a.time_schedule_id) for a in ret ]
        expected = [ ]
        self.assertCountEqual(ret, expected)

        self.get_all_rels().unlink()
        card = self._cards[5]
        rel_env.update_card_rels(card)
        ret = self.get_all_rels()
        ret = [ (a.door_id, a.time_schedule_id) for a in ret ]
        expected = [
            (self._doors[2], self._def_ts),
            (self._doors[3], self._def_ts),
        ]
        self.assertCountEqual(ret, expected)

        self.get_all_rels().unlink()
        card = self._cards[6]
        rel_env.update_card_rels(card)
        ret = self.get_all_rels()
        ret = [ (a.door_id, a.time_schedule_id) for a in ret ]
        expected = [ ]
        self.assertCountEqual(ret, expected)

        self.get_all_rels().unlink()
        self._doors[4].controller_id.external_db = False
        card = self._cards[6]
        rel_env.update_card_rels(card)
        ret = self.get_all_rels()
        ret = [ (a.door_id, a.time_schedule_id) for a in ret ]
        expected = [ (self._doors[4], self._other_ts) ]
        self.assertCountEqual(ret, expected)

    def test_update_door_rels(self):
        rel_env = self._env

        self.get_all_rels().unlink()
        door = self._doors[0]
        rel_env.update_door_rels(door)
        ret = self.get_all_rels()
        ret = [ (a.card_id, a.time_schedule_id) for a in ret ]
        expected = [
            (self._cards[0], self._def_ts),
            (self._cards[1], self._def_ts),
            (self._cards[4], self._def_ts),
        ]
        self.assertCountEqual(ret, expected)

        self.get_all_rels().unlink()
        door = self._doors[4]
        rel_env.update_door_rels(door)
        ret = self.get_all_rels()
        ret = [ (a.card_id, a.time_schedule_id) for a in ret ]
        expected = [ ]
        self.assertCountEqual(ret, expected)

        self.get_all_rels().unlink()
        door = self._doors[4]
        self._cards[6].cloud_card = False
        rel_env.update_door_rels(door)
        ret = self.get_all_rels()
        ret = [ (a.card_id, a.time_schedule_id) for a in ret ]
        expected = [ (self._cards[6], self._other_ts) ]
        self.assertCountEqual(ret, expected)

        self.get_all_rels().unlink()
        door = self._doors[5]
        rel_env.update_door_rels(door)
        ret = self.get_all_rels()
        ret = [ (a.card_id, a.time_schedule_id) for a in ret ]
        expected = [ ]
        self.assertCountEqual(ret, expected)

    def test_check_relevance_slow(self):
        rel_env = self._env
        card = self._cards[0]
        door = self._doors[0]

        rel_env.check_relevance_slow(card, door)
        ret = self.find_card_door_rel(card, door)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret.time_schedule_id, self._def_ts)

        self.get_all_rels().unlink()
        rel_env.check_relevance_slow(card, door)
        ret = self.find_card_door_rel(card, door)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret.time_schedule_id, self._def_ts)

        self.get_all_rels().unlink()
        card.get_owner().remove_acc_gr(self._acc_grs[0])
        rel_env.check_relevance_slow(card, door)
        ret = self.find_card_door_rel(card, door)
        self.assertEqual(len(ret), 0)

    def test_check_relevance_fast(self):
        rel_env = self._env
        card = self._cards[0]
        door1 = self._doors[0]
        door2 = self._doors[4]

        self.get_all_rels().unlink()
        rel_env.check_relevance_fast(card, door1)
        ret = self.find_card_door_rel(card, door1)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret.time_schedule_id, self._def_ts)

        self.get_all_rels().unlink()
        rel_env.check_relevance_fast(card, door2)
        ret = self.find_card_door_rel(card, door2)
        self.assertEqual(len(ret), 0)

        with self.assertRaises(exceptions.ValidationError):
            self.get_all_rels().unlink()
            card.cloud_card = False
            rel_env.check_relevance_fast(card, door2)
            ret = self.find_card_door_rel(card, door2)
            self.assertEqual(len(ret), 1)
            self.assertEqual(ret.time_schedule_id, self._other_ts)

        self.get_all_rels().unlink()
        rel_env.check_relevance_fast(card, door2, self._other_ts)
        ret = self.find_card_door_rel(card, door2)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret.time_schedule_id, self._other_ts)

        self.get_all_rels().unlink()
        rel_env.check_relevance_fast(card, door2, self._def_ts)
        ret = self.find_card_door_rel(card, door2)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret.time_schedule_id, self._def_ts)

    def test_create_rel(self):
        rel_env = self._env
        card = self._cards[0]
        door = self._doors[0]

        self.get_all_rels().unlink()

        ret = self.find_card_door_rel(card, door)
        self.assertEqual(len(ret), 0)

        rel_env.create_rel(card, door)
        ret = self.find_card_door_rel(card, door)
        self.assertEqual(len(ret), 1)
        self.assertEqual(ret.time_schedule_id, self._def_ts)

        rel_env.create_rel(card, door)
        self.assertTrue(ret.exists())
        self.assertEqual(ret.card_id, card)
        self.assertEqual(ret.door_id, door)
        self.assertEqual(ret.time_schedule_id, self._def_ts)
        self.assertEqual(len(self.get_all_rels()), 1)  # Only 1 relation should exist

    def test_remove_rel(self):
        rel_env = self._env
        card = self._cards[0]
        door = self._doors[0]

        self.get_all_rels().unlink()
        self.assertEqual(len(self.get_all_rels()), 0)

        rel_env.remove_rel(card, door)
        self.assertEqual(len(self.get_all_rels()), 0)

        rel_env.create_rel(card, door)
        self.assertEqual(len(self.get_all_rels()), 1)

        rel_env.remove_rel(card, door)
        self.assertEqual(len(self.get_all_rels()), 0)

    def test_check_rel_relevance(self):
        rel_env = self._env
        card = self._cards[0]
        door = self._doors[0]

        self.get_all_rels().unlink()
        rel_env.create_rel(card, door)
        rel = self.find_card_door_rel(card, door)

        rel.check_rel_relevance()
        self.assertTrue(rel.exists())
        self.assertEqual(rel.card_id, card)
        self.assertEqual(rel.door_id, door)
        self.assertEqual(rel.time_schedule_id, self._def_ts)

        self.get_all_rels().unlink()

        card.employee_id.remove_acc_gr(self._acc_grs[0])
        rel_env.create_rel(card, door, self._def_ts)
        rel = self.find_card_door_rel(card, door)
        rel.check_rel_relevance()
        self.assertFalse(rel.exists())

    def test_time_schedule_changed(self):
        card = self._cards[0]
        door = self._doors[0]

        rel = self.find_card_door_rel(card, door)
        self.assertTrue(rel.exists())
        self.assertEqual(rel.time_schedule_id, self._def_ts)

        rel.time_schedule_changed(self._other_ts)
        self.assertEqual(rel.time_schedule_id, self._other_ts)
        rel.time_schedule_changed(self._other_ts)
        self.assertEqual(rel.time_schedule_id, self._other_ts)
        rel.time_schedule_changed(self._def_ts)
        self.assertEqual(rel.time_schedule_id, self._def_ts)

    def test_pin_code_changed(self):
        card = self._cards[0]
        door = self._doors[0]

        cmd_env = self.env['hr.rfid.command'].sudo()
        cmd_env.search([]).unlink()

        rel = self.find_card_door_rel(card, door)
        self.assertTrue(rel.exists())

        rel.pin_code_changed()

        cmd = cmd_env.search([])
        self.assertTrue(cmd.exists(), 1)
        self.assertEqual(cmd.webstack_id, door.controller_id.webstack_id)
        self.assertEqual(cmd.controller_id, door.controller_id)
        self.assertEqual(cmd.cmd, 'D1')
        self.assertEqual(cmd.card_number, card.number)
        self.assertEqual(cmd.pin_code, card.get_owner().hr_rfid_pin_code)
        self.assertEqual(cmd.ts_code, '00000000')
        self.assertEqual(cmd.rights_data, 1)
        self.assertEqual(cmd.rights_mask, 1)

    def test_card_number_changed(self):
        card = self._cards[0]
        door = self._doors[0]
        new_number = '1000000001'

        cmd_env = self.env['hr.rfid.command'].sudo()
        cmd_env.search([]).unlink()

        rel = self.find_card_door_rel(card, door)
        self.assertTrue(rel.exists())

        rel.card_number_changed(card.number)
        cmds = cmd_env.search([])
        self.assertFalse(cmds.exists())

        rel.card_number_changed(new_number)
        cmds = cmd_env.search([])
        self.assertEqual(len(cmds), 2)

        cmd_del = cmd_env.search([ ('card_number', '=', new_number) ])
        cmd_add = cmd_env.search([ ('card_number', '=', card.number) ])

        self.assertTrue(cmd_del.exists())
        self.assertEqual(cmd_del.webstack_id, door.controller_id.webstack_id)
        self.assertEqual(cmd_del.controller_id, door.controller_id)
        self.assertEqual(cmd_del.cmd, 'D1')
        self.assertEqual(cmd_del.card_number, new_number)
        self.assertEqual(cmd_del.pin_code, card.get_owner().hr_rfid_pin_code)
        self.assertEqual(cmd_del.ts_code, '00000000')
        self.assertEqual(cmd_del.rights_data, 0)
        self.assertEqual(cmd_del.rights_mask, 1)

        self.assertTrue(cmd_add.exists())
        self.assertEqual(cmd_add.webstack_id, door.controller_id.webstack_id)
        self.assertEqual(cmd_add.controller_id, door.controller_id)
        self.assertEqual(cmd_add.cmd, 'D1')
        self.assertEqual(cmd_add.card_number, card.number)
        self.assertEqual(cmd_add.pin_code, card.get_owner().hr_rfid_pin_code)
        self.assertEqual(cmd_add.ts_code, '00000000')
        self.assertEqual(cmd_add.rights_data, 1)
        self.assertEqual(cmd_add.rights_mask, 1)

    def test_reload_add_card_command(self):
        card = self._cards[0]
        door = self._doors[0]

        cmd_env = self.env['hr.rfid.command'].sudo()
        cmd_env.search([]).unlink()

        rel = self.find_card_door_rel(card, door)
        self.assertTrue(rel.exists())

        rel.reload_add_card_command()
        cmd = cmd_env.search([])

        self.assertTrue(cmd.exists())
        self.assertEqual(cmd.webstack_id, door.controller_id.webstack_id)
        self.assertEqual(cmd.controller_id, door.controller_id)
        self.assertEqual(cmd.cmd, 'D1')
        self.assertEqual(cmd.card_number, card.number)
        self.assertEqual(cmd.pin_code, card.get_owner().hr_rfid_pin_code)
        self.assertEqual(cmd.ts_code, '00000000')
        self.assertEqual(cmd.rights_data, 1)
        self.assertEqual(cmd.rights_mask, 1)

    def test_create(self):
        card = self._cards[0]
        door = self._doors[0]

        rel_env = self._env
        self.get_all_rels().unlink()

        cmd_env = self.env['hr.rfid.command'].sudo()
        cmd_env.search([]).unlink()

        rel = rel_env.create([{
            'card_id': card.id,
            'door_id': door.id,
            'time_schedule_id': self._def_ts.id,
        }])

        self.assertTrue(rel.exists())
        self.assertEqual(rel.card_id, card)
        self.assertEqual(rel.door_id, door)
        self.assertEqual(rel.time_schedule_id, self._def_ts)

        cmd = cmd_env.search([])

        self.assertEqual(len(cmd), 1)
        self.assertEqual(cmd.webstack_id, door.controller_id.webstack_id)
        self.assertEqual(cmd.controller_id, door.controller_id)
        self.assertEqual(cmd.cmd, 'D1')
        self.assertEqual(cmd.card_number, card.number)
        self.assertEqual(cmd.pin_code, card.get_owner().hr_rfid_pin_code)
        self.assertEqual(cmd.ts_code, '00000000')
        self.assertEqual(cmd.rights_data, 1)
        self.assertEqual(cmd.rights_mask, 1)

    def test_write_door_id(self):
        card = self._cards[0]
        door1 = self._doors[0]
        door2 = self._doors[1]

        cmd_env = self.env['hr.rfid.command'].sudo()
        cmd_env.search([]).unlink()

        rel = self.find_card_door_rel(card, door1)

        self.assertTrue(rel.exists())
        rel.write({ 'door_id': door2.id })

        cmd = cmd_env.search([])
        self.assertEqual(len(cmd), 1)

        self.assertEqual(cmd.webstack_id, door2.controller_id.webstack_id)
        self.assertEqual(cmd.controller_id, door2.controller_id)
        self.assertEqual(cmd.cmd, 'D1')
        self.assertEqual(cmd.card_number, card.number)
        self.assertEqual(cmd.pin_code, card.get_owner().hr_rfid_pin_code)
        self.assertEqual(cmd.ts_code, '00000000')
        self.assertEqual(cmd.rights_data, 2)
        self.assertEqual(cmd.rights_mask, 3)

    def test_write_card_id(self):
        card1 = self._cards[0]
        card2 = self._cards[1]
        door = self._doors[0]

        cmd_env = self.env['hr.rfid.command'].sudo()
        cmd_env.search([]).unlink()

        rel = self.find_card_door_rel(card1, door)

        self.assertTrue(rel.exists())
        rel.write({ 'card_id': card2.id })

        cmds = cmd_env.search([])
        self.assertEqual(len(cmds), 2)

        cmd_del = cmd_env.search([ ('card_number', '=', card1.number) ])
        cmd_add = cmd_env.search([ ('card_number', '=', card2.number) ])

        self.assertTrue(cmd_del.exists())
        self.assertEqual(cmd_del.webstack_id, door.controller_id.webstack_id)
        self.assertEqual(cmd_del.controller_id, door.controller_id)
        self.assertEqual(cmd_del.cmd, 'D1')
        self.assertEqual(cmd_del.card_number, card1.number)
        self.assertEqual(cmd_del.pin_code, card1.get_owner().hr_rfid_pin_code)
        self.assertEqual(cmd_del.ts_code, '00000000')
        self.assertEqual(cmd_del.rights_data, 0)
        self.assertEqual(cmd_del.rights_mask, 1)

        self.assertTrue(cmd_add.exists())
        self.assertEqual(cmd_add.webstack_id, door.controller_id.webstack_id)
        self.assertEqual(cmd_add.controller_id, door.controller_id)
        self.assertEqual(cmd_add.cmd, 'D1')
        self.assertEqual(cmd_add.card_number, card2.number)
        self.assertEqual(cmd_add.pin_code, card2.get_owner().hr_rfid_pin_code)
        self.assertEqual(cmd_add.ts_code, '00000000')
        self.assertEqual(cmd_add.rights_data, 1)
        self.assertEqual(cmd_add.rights_mask, 1)

    def test_time_schedule_id(self):
        card = self._cards[0]
        door = self._doors[0]
        new_ts = self._other_ts

        cmd_env = self.env['hr.rfid.command'].sudo()
        cmd_env.search([]).unlink()

        rel = self.find_card_door_rel(card, door)

        self.assertTrue(rel.exists())
        rel.write({ 'time_schedule_id': new_ts.id })

        cmd = cmd_env.search([])
        self.assertEqual(len(cmd), 1)

        self.assertEqual(cmd.webstack_id, door.controller_id.webstack_id)
        self.assertEqual(cmd.controller_id, door.controller_id)
        self.assertEqual(cmd.cmd, 'D1')
        self.assertEqual(cmd.card_number, card.number)
        self.assertEqual(cmd.pin_code, card.get_owner().hr_rfid_pin_code)
        self.assertEqual(cmd.ts_code, ('%02X' % new_ts.number) + '000000')
        self.assertEqual(cmd.rights_data, 1)
        self.assertEqual(cmd.rights_mask, 1)

    def test_unlink(self):
        card = self._cards[0]
        door = self._doors[0]

        rel = self.find_card_door_rel(card, door)
        self.assertTrue(rel.exists())

        cmd_env = self.env['hr.rfid.command'].sudo()
        cmd_env.search([]).unlink()

        rel.unlink()

        cmd = cmd_env.search([])
        self.assertEqual(len(cmd), 1)

        self.assertEqual(cmd.webstack_id, door.controller_id.webstack_id)
        self.assertEqual(cmd.controller_id, door.controller_id)
        self.assertEqual(cmd.cmd, 'D1')
        self.assertEqual(cmd.card_number, card.number)
        self.assertEqual(cmd.pin_code, card.get_owner().hr_rfid_pin_code)
        self.assertEqual(cmd.ts_code, '00000000')
        self.assertEqual(cmd.rights_data, 0)
        self.assertEqual(cmd.rights_mask, 1)
