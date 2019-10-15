from odoo import api, exceptions
from odoo.tests import Form, common
from .common import create_webstacks, create_acc_grs_cnt, create_employees, create_contacts, create_card, \
    create_departments, card_door_rels_search
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


def get_ws_doors(webstacks):
    return webstacks.mapped('controllers').mapped('door_ids')


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

        cls._acc_grs[0].add_doors(cls._doors[0])
        cls._acc_grs[1].add_doors(cls._doors[1])
        cls._acc_grs[2].add_doors(cls._doors[2])
        cls._acc_grs[2].add_doors(cls._doors[3])
        cls._acc_grs[3].add_doors(cls._doors[4])

    def test_card_creation(self):
        # Check if creating a card with a length different from 10 raises
        with self.assertRaises(exceptions.ValidationError):
            create_card(self.env, '123', self._employees[0])

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

    def test_create_cards_relations(self):
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
        # TODO: The cmd_env part of this test belongs in the CardDoorRelTests class.
        #       Should only confirm that relation still exists in here
        card_old_number = '0000000001'
        card_new_number = '0000000002'
        env = self.env
        cmd_env = env['hr.rfid.command'].sudo()
        card = create_card(env, card_old_number, self._employees[0])
        cmd_env.search([]).unlink()

        self.assertEqual(cmd_env.search([]), cmd_env)
        card.write({ 'number': card_old_number })
        self.assertEqual(cmd_env.search([]), cmd_env)
        card.write({ 'number': card_new_number })

        cmds = cmd_env.search([])
        self.assertEqual(len(cmds), 2)

        cmd_add = cmd_env.search([ ('card_number', '=', card_new_number) ])
        cmd_del = cmd_env.search([ ('card_number', '=', card_old_number) ])

        self.assertEqual(cmd_add.rights_data, 1)
        self.assertEqual(cmd_add.rights_mask, 1)

        self.assertEqual(cmd_del.rights_data, 0)
        self.assertEqual(cmd_del.rights_mask, 1)

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

        cls._acc_grs[0].add_doors(cls._doors[0])
        cls._acc_grs[1].add_doors(cls._doors[1])
        cls._acc_grs[2].add_doors(cls._doors[2])
        cls._acc_grs[2].add_doors(cls._doors[3])
        cls._acc_grs[3].add_doors(cls._doors[4])

