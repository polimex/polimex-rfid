# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Tests for the command queue priority mechanism.

Anti-passback (APB) flag changes must jump ahead of the regular command
backlog of the webstack, otherwise on a busy RS-485 bus (multiple
controllers behind one LAN module) the exit permission reaches the other
door's controller after the person has already walked to it and the
controller denies the pass with an APB error.

Covers:
- a fresh APB D1 command carries PRIORITY_APB;
- the picker (check_for_unsent_cmd) returns the APB command before older
  regular commands of the same webstack;
- merging an APB change into an existing Wait D1 raises the priority of
  the merged command (and never lowers it);
- regular commands keep strict FIFO order among equal priorities.
"""
import logging

from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'command_priority')
class TestCommandPriority(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company_id = self.env['res.company'].create({'name': 'Priority Test Company'}).id
        self.webstack = self.env['hr.rfid.webstack'].create({
            'name': 'Priority Test Stack',
            'serial': '765432',
            'company_id': self.company_id,
            'available': 'a',
            'tz': 'Europe/Sofia',
            'active': True,
        })
        self.ctrl_a = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller A (busy)',
            'ctrl_id': 21,
            'webstack_id': self.webstack.id,
        })
        self.ctrl_b = self.env['hr.rfid.ctrl'].create({
            'name': 'Controller B (APB door)',
            'ctrl_id': 26,
            'webstack_id': self.webstack.id,
        })
        self.door_b = self.env['hr.rfid.door'].create({
            'name': 'APB Door B',
            'number': 1,
            'controller_id': self.ctrl_b.id,
        })
        # The card-door relation requires the door to be in an access group,
        # so wire it the canonical way: access group + door + employee - the
        # relation is created automatically.
        self.access_group = self.env['hr.rfid.access.group'].create({
            'name': 'Priority Test AG',
            'company_id': self.company_id,
        })
        self.access_group.add_doors(self.door_b)
        self.department = self.env['hr.department'].create({
            'name': 'Priority Test Department',
            'company_id': self.company_id,
            'hr_rfid_default_access_group': self.access_group.id,
            'hr_rfid_allowed_access_groups': [(4, self.access_group.id, 0)],
        })
        self.employee = self.env['hr.employee'].create({
            'name': 'Priority Test Employee',
            'company_id': self.company_id,
            'department_id': self.department.id,
        })
        self.card = self.env['hr.rfid.card'].create({
            'number': '1234512345',
            'card_input_type': 'w34',
            'card_reference': 'Priority Badge',
            'employee_id': self.employee.id,
            'company_id': self.company_id,
        })
        self.rel = self.env['hr.rfid.card.door.rel'].search([
            ('card_id', '=', self.card.id),
            ('door_id', '=', self.door_b.id),
        ])
        self.assertTrue(self.rel, 'Fixture: card-door relation must exist')
        self.Command = self.env['hr.rfid.command']
        # Discard whatever the fixtures queued - the tests below control the
        # queue contents explicitly.
        self._clear_queue()

    def _clear_queue(self):
        self.Command.search([
            ('webstack_id', '=', self.webstack.id),
            ('status', 'in', ['Wait', 'Process']),
        ]).unlink()

    def _make_plain_cmd(self, cmd_data=''):
        # D3 is not in the create() merge list, so every call queues a new
        # independent command at the tail - exactly what a busy webstack
        # backlog looks like.
        return self.Command.create([{
            'webstack_id': self.webstack.id,
            'controller_id': self.ctrl_a.id,
            'cmd': 'D3',
            'cmd_data': cmd_data,
        }])

    def _wait_d1(self):
        return self.Command.search([
            ('webstack_id', '=', self.webstack.id),
            ('cmd', '=', 'D1'),
            ('status', '=', 'Wait'),
        ])

    def test_apb_command_carries_apb_priority(self):
        self.door_b.change_apb_flag(self.card, can_exit=True)
        apb_cmd = self._wait_d1()
        self.assertEqual(len(apb_cmd), 1, 'Expected exactly one APB D1 command')
        self.assertEqual(apb_cmd.priority, self.Command.PRIORITY_APB,
                         'APB flag change must carry PRIORITY_APB')
        self.assertEqual(int(apb_cmd.rights_data), 0x40)
        self.assertEqual(int(apb_cmd.rights_mask), 0x40)

    def test_apb_command_jumps_queue(self):
        older = [self._make_plain_cmd('%02d' % i) for i in range(3)]
        self.door_b.change_apb_flag(self.card, can_exit=True)
        apb_cmd = self._wait_d1()
        self.assertTrue(all(apb_cmd.id > c.id for c in older),
                        'Sanity: the APB command is the newest row')

        response = self.webstack.check_for_unsent_cmd(200)
        self.assertIn('cmd', response, 'Expected a command in the response')
        self.assertEqual(response['cmd']['c'], 'D1',
                         'The APB command must be picked before the older backlog')
        self.assertEqual(response['cmd']['id'], self.ctrl_b.ctrl_id)
        self.assertEqual(apb_cmd.status, 'Process')

    def test_merge_into_regular_command_raises_priority(self):
        # A regular access-rights D1 is waiting (e.g. access group change).
        self.Command.add_remove_card(
            card_number=self.card.internal_number,
            ctrl_id=self.ctrl_b.id,
            pin_code='0000',
            ts_code='01000000',
            rights_data=0x01,
            rights_mask=0x01,
            alarm_right=False,
        )
        regular = self._wait_d1()
        self.assertEqual(len(regular), 1)
        self.assertEqual(regular.priority, self.Command.PRIORITY_DEFAULT)

        # The APB flag change merges into it and must raise its priority.
        self.door_b.change_apb_flag(self.card, can_exit=True)
        merged = self._wait_d1()
        self.assertEqual(merged.id, regular.id, 'Merge must reuse the old record')
        self.assertEqual(merged.priority, self.Command.PRIORITY_APB,
                         'Merged command must inherit the APB priority')
        self.assertEqual(int(merged.rights_data), 0x41)
        self.assertEqual(int(merged.rights_mask), 0x41)

    def test_merge_never_lowers_priority(self):
        # APB command first, then a regular change merges into it.
        self.door_b.change_apb_flag(self.card, can_exit=True)
        apb_cmd = self._wait_d1()
        self.assertEqual(apb_cmd.priority, self.Command.PRIORITY_APB)

        self.Command.add_remove_card(
            card_number=self.card.internal_number,
            ctrl_id=self.ctrl_b.id,
            pin_code='0000',
            ts_code='01000000',
            rights_data=0x01,
            rights_mask=0x01,
            alarm_right=False,
        )
        merged = self._wait_d1()
        self.assertEqual(merged.id, apb_cmd.id, 'Merge must reuse the old record')
        self.assertEqual(merged.priority, self.Command.PRIORITY_APB,
                         'A later regular merge must not lower the priority')

    def test_equal_priority_commands_stay_fifo(self):
        created = [self._make_plain_cmd('%02d' % i) for i in range(3)]
        picked_ids = []
        for _unused in range(3):
            response = self.webstack.check_for_unsent_cmd(200)
            self.assertIn('cmd', response)
            processing = self.Command.search([
                ('webstack_id', '=', self.webstack.id),
                ('status', '=', 'Process'),
            ])
            self.assertEqual(len(processing), 1)
            picked_ids.append(processing.id)
            processing.status = 'Success'
        self.assertEqual(picked_ids, sorted(c.id for c in created),
                         'Equal-priority commands must drain in FIFO (id) order')
