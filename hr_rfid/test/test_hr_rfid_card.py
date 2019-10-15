from odoo import api, exceptions
from odoo.tests import Form, common
from .common import create_webstacks, create_acc_grs_cnt, create_employees, create_contacts, create_card, \
    create_departments
from random import randint
from functools import reduce, partial

import operator


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


def get_ws_doors(env: api.Environment, webstack):
    return reduce(lambda a, b: a.door_ids + b.door_ids, webstack.controllers, env['hr.rfid.door'])


class Test(common.SavepointCase):
    def setUpClass(self):
        self._ws = create_webstacks(self.env, webstacks=1, controllers=[2, 2])
        self._doors = get_ws_doors(self.env, self._ws)
        self._acc_grs = create_acc_grs_cnt(self.env, 3)
        self._departments = create_departments(self.env, ['Upstairs Office', 'Downstairs Office'])
        self._employees = create_employees(self.env,
                                           ['Max', 'Cooler Max', 'Jacob'],
                                           [self._departments[0], self._departments[1]])
        self._contacts = create_contacts(self.env, ['Greg', 'Cooler Greg', 'Richard'])
        self._departments[0].hr_rfid_allowed_access_groups = self._acc_grs[0] + self._acc_grs[1]
        self._departments[1].hr_rfid_allowed_access_groups = self._acc_grs[1] + self._acc_grs[2]
        self._employees[0].add_acc_gr(self._acc_grs[0])
        self._employees[1].add_acc_gr(self._acc_grs[1])
        self._contacts[0].add_acc_gr(self._acc_grs[0])
        self._contacts[1].add_acc_gr(self._acc_grs[1])
        self._contacts[2].add_acc_gr(self._acc_grs[0] + self._acc_grs[2])
        self._acc_grs[0].add_doors(self._doors[0])
        self._acc_grs[1].add_doors(self._doors[1])
        self._acc_grs[2].add_doors(self._doors[2])
        self._acc_grs[2].add_doors(self._doors[3])

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
        with self.assertRaises(exceptions.ValidationError):
            create_card(self.env, cards[0].number, self._employees[0])

    def test_create_cards_commands(self):
        env = self.env
        cmd_env = env['hr.rfid.command']
        card1n = '0000000001'
        card2n = '0000000002'
        create_card(env, card1n, self._employees[0])
        cmd = cmd_env.search([
            ('webstack_id', '=', self._ws.id),
            ('controller_id', '=', self._ws.controller_ids[0].id),
            ('cmd', '=', 'D1'),
            ('card_number', '=', card1n),
            ('ts_code', '=', '0'),
            ('rights_data', '=', '01'),
            ('rights_mask', '=', '01'),
            ('status', '=', '')
        ])
        self.assertGreater(len(cmd), 0, msg='Command was not created for controller 1 after creating card 1!')
        create_card(env, card2n, self._contacts[2])
        cmd = cmd_env.search([
            ('webstack_id', '=', self._ws.id),
            ('controller_id', '=', self._ws.controller_ids[0].id),
            ('cmd', '=', 'D1'),
            ('card_number', '=', card2n),
            ('ts_code', '=', '0'),
            ('rights_data', '=', '01'),
            ('rights_mask', '=', '01'),
            ('status', '=', 'Wait')
        ])
        self.assertGreater(len(cmd), 0, msg='Command was not created for controller 1 after creating card 2!')
        cmd = cmd_env.search([
            ('webstack_id', '=', self._ws.id),
            ('controller_id', '=', self._ws.controller_ids[1].id),
            ('cmd', '=', 'D1'),
            ('card_number', '=', card2n),
            ('ts_code', '=', '0'),
            ('rights_data', '=', '03'),
            ('rights_mask', '=', '03'),
            ('status', '=', 'Wait')
        ])
        self.assertGreater(len(cmd), 0, msg='Command was not created for controller 2 after creating card 2!')
