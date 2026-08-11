# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Module sharing between companies (webstack.shared_company_ids).

Business oracle (owner-approved, 2026-07-31): one physical module serves TWO
different customer companies at the same time (e.g. two schools sharing one
building entrance - the Laravel-cloud `customer_web_stack` feature). The
sharing companies each manage access for THEIR OWN people on the shared
hardware; a third company must see nothing; the module stays owned and
administered by exactly one company.

Every test below traces to one of those sentences - none of them assert an
implementation detail for its own sake.
"""
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase
from odoo.tests.common import tagged, new_test_user

from odoo.addons.hr_rfid.tests.controller import RFIDController

import logging

_logger = logging.getLogger(__name__)


class SharedModuleCase(RFIDController):
    """Companies A (owner), B (sharing) and C (control) with one restricted
    RFID manager each, plus a B-side person/card/access group."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env['res.company'].browse(cls.test_company_id)
        cls.company_b = cls.env['res.company'].create({'name': 'Sharing School B'})
        cls.company_c = cls.env['res.company'].create({'name': 'Unrelated Co C'})

        def _mgr(login, company):
            return new_test_user(
                cls.env, login=login,
                groups='hr_rfid.hr_rfid_group_manager',
                company_id=company.id,
                company_ids=[(6, 0, [company.id])],
            )
        cls.manager_a = _mgr('share_mgr_a', cls.company_a)
        cls.manager_b = _mgr('share_mgr_b', cls.company_b)
        cls.manager_c = _mgr('share_mgr_c', cls.company_c)
        # Wiring a module to ANOTHER company requires seeing that company —
        # sharing is set up by someone with access to both (e.g. the operator
        # serving both tenants). The single-company owner manager can still
        # REVOKE sharing on their own (no read needed to remove).
        cls.manager_ab = new_test_user(
            cls.env, login='share_mgr_ab',
            groups='hr_rfid.hr_rfid_group_manager',
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id, cls.company_b.id])],
        )

        cls.ag_b = cls.env['hr.rfid.access.group'].create({
            'name': 'B Shared Entrance',
            'company_id': cls.company_b.id,
        })
        cls.department_b = cls.env['hr.department'].create({
            'name': 'B Department',
            'company_id': cls.company_b.id,
            'hr_rfid_default_access_group': cls.ag_b.id,
            'hr_rfid_allowed_access_groups': [(4, cls.ag_b.id, 0)],
        })
        cls.employee_b = cls.env['hr.employee'].create({
            'name': 'Boris From B',
            'company_id': cls.company_b.id,
            'department_id': cls.department_b.id,
        })
        cls.card_b = cls.env['hr.rfid.card'].create({
            'number': '1122334455',
            'card_input_type': 'w34',
            'employee_id': cls.employee_b.id,
            'company_id': cls.company_b.id,
        })
        # The department's default access group auto-enrolls the employee;
        # make sure the fixture really holds (the tests depend on it).
        assert cls.ag_b in cls.employee_b.hr_rfid_access_group_ids.mapped('access_group_id'), \
            'Department default AG must auto-enroll the employee'

    def _ts_b(self, number=0):
        return self.env['hr.rfid.time.schedule'].sudo().search([
            ('company_id', '=', self.company_b.id),
            ('number', '=', number),
        ], limit=1)

    def _make_light_hardware(self):
        """Owner-side controller/door/reader built directly through the ORM -
        for tests that do not exercise the HTTP device flow."""
        self.ctrl = self.env['hr.rfid.ctrl'].create({
            'name': 'Shared Ctrl',
            'ctrl_id': 90,
            'webstack_id': self.test_webstack_10_3_id.id,
        })
        self.door = self.env['hr.rfid.door'].create({
            'name': 'Shared Entrance',
            'number': 9001,
            'controller_id': self.ctrl.id,
        })
        self.reader = self.env['hr.rfid.reader'].create({
            'name': 'R1',
            'number': 1,
            'reader_type': '0',
            'controller_id': self.ctrl.id,
            'door_id': self.door.id,
        })

    def _share_with_b(self):
        self.test_webstack_10_3_id.with_user(self.manager_ab).write({
            'shared_company_ids': [(6, 0, [self.company_b.id])],
        })

    def _grant_b(self, door, ts_number=0, ag=None):
        """B includes the shared door in ITS OWN access group, as B's manager."""
        return self.env['hr.rfid.access.group.door.rel'].with_user(self.manager_b).create({
            'access_group_id': (ag or self.ag_b).id,
            'door_id': door.id,
            'time_schedule_id': self._ts_b(ts_number).id,
        })


@tagged('standard', 'at_install', 'rfid', 'rfid_sharing')
class TestSharedModuleVisibility(SharedModuleCase):
    """Who sees what: the sharing company sees the shared hardware, the
    control company sees nothing, per-company data stays isolated."""

    def _search_as(self, user, model, domain):
        return self.env[model].with_user(user).search(domain)

    def test_sharing_company_sees_hardware_control_company_does_not(self):
        """B (shared with) can see the controllers, doors and readers of the
        shared module so it can organise its own access; C sees none of it."""
        self._make_light_hardware()
        shared = (('hr.rfid.ctrl', self.ctrl), ('hr.rfid.door', self.door),
                  ('hr.rfid.reader', self.reader))
        # Before sharing: B sees nothing either.
        for model, rec in shared:
            self.assertFalse(self._search_as(self.manager_b, model, [('id', '=', rec.id)]),
                             '%s must be hidden from B before sharing' % model)
        self._share_with_b()
        for model, rec in shared:
            self.assertTrue(self._search_as(self.manager_b, model, [('id', '=', rec.id)]),
                            '%s must be visible to B after sharing' % model)
            self.assertFalse(self._search_as(self.manager_c, model, [('id', '=', rec.id)]),
                             '%s must stay hidden from C' % model)

    def test_module_record_itself_is_never_shared(self):
        """The module record carries the device credentials that authenticate
        the hardware on the public event route - with them anyone can forge
        events or drain the command queue. It stays with the owner alone, and
        so does the command queue (it lists the owner's card numbers)."""
        self._make_light_hardware()
        self._share_with_b()
        self.assertFalse(self._search_as(
            self.manager_b, 'hr.rfid.webstack',
            [('id', '=', self.test_webstack_10_3_id.id)]),
            'The module record (device key, module password) must stay private')
        self.test_ag_employee_1.add_doors(self.door)
        cmds = self.env['hr.rfid.command'].sudo().search([
            ('controller_id', '=', self.ctrl.id)])
        self.assertTrue(cmds, 'The owner grant must have queued commands')
        self.assertFalse(self._search_as(
            self.manager_b, 'hr.rfid.command', [('id', 'in', cmds.ids)]),
            "The command queue carries the owner's card numbers and PIN codes")

    def test_per_company_data_stays_isolated_while_sharing(self):
        """Sharing the hardware shares NOTHING else: A's cards, access groups,
        schedules and A's people stay invisible to B."""
        self._make_light_hardware()
        self._share_with_b()
        self.assertFalse(self._search_as(
            self.manager_b, 'hr.rfid.card', [('id', '=', self.test_card_employee.id)]),
            "A's cards must stay hidden from B")
        self.assertFalse(self._search_as(
            self.manager_b, 'hr.rfid.access.group', [('id', '=', self.test_ag_employee_1.id)]),
            "A's access groups must stay hidden from B")
        ts_a = self.env['hr.rfid.time.schedule'].sudo().search(
            [('company_id', '=', self.company_a.id)], limit=1)
        self.assertFalse(self._search_as(
            self.manager_b, 'hr.rfid.time.schedule', [('id', '=', ts_a.id)]),
            "A's time schedules must stay hidden from B")

    def test_grant_relations_scoped_not_enumerable(self):
        """The card-door / group-door relations follow the same boundaries:
        the owner sees every grant on its hardware, C sees none."""
        self._make_light_hardware()
        self.test_ag_employee_1.add_doors(self.door)
        self._share_with_b()
        rel_b = self._grant_b(self.door)
        # Owner sees B's grant on its own hardware.
        self.assertTrue(self._search_as(
            self.manager_a, 'hr.rfid.access.group.door.rel', [('id', '=', rel_b.id)]),
            "The owner must see every grant on its own hardware")
        # C enumerates nothing.
        self.assertFalse(self._search_as(
            self.manager_c, 'hr.rfid.access.group.door.rel',
            [('door_id', '=', self.door.id)]),
            'C must not enumerate grants on the shared module')
        self.assertFalse(self._search_as(
            self.manager_c, 'hr.rfid.card.door.rel',
            [('door_id', '=', self.door.id)]),
            'C must not enumerate card grants on the shared module')

    def test_grant_by_sharing_company_reaches_the_hardware(self):
        """B's grant must still be delivered to the owner's controller - the
        server queues the command itself, B never touches the queue."""
        self._make_light_hardware()
        self.test_ag_employee_1.add_doors(self.door)
        self._share_with_b()
        self._grant_b(self.door)
        cmd = self.env['hr.rfid.command'].sudo().search([
            ('controller_id', '=', self.ctrl.id), ('cmd', '=', 'D1'),
            ('card_number', '=', self.card_b.internal_number)])
        self.assertTrue(cmd, "B's grant must queue an add-card command")


@tagged('standard', 'at_install', 'rfid', 'rfid_sharing')
class TestSharedModuleGuards(SharedModuleCase):
    """The safety rules of sharing: no duplicate card numbers on the shared
    hardware, foreign grants only 24/7, ownership stays with the owner."""

    def test_duplicate_card_number_blocked_on_shared_module(self):
        """Two people from the two companies cannot carry the same card
        number on the shared module - the controller cannot tell them apart."""
        self._make_light_hardware()
        # A's employee is granted (same number as B will try to use).
        self.test_ag_employee_1.add_doors(self.door)
        self._share_with_b()
        clone_card = self.env['hr.rfid.card'].create({
            'number': self.test_card_employee.number,
            'card_input_type': 'w34',
            'employee_id': self.employee_b.id,
            'company_id': self.company_b.id,
        })
        self.assertTrue(clone_card, 'The same number in another company is fine on its own')
        with self.assertRaises(ValidationError):
            self._grant_b(self.door)

    def test_duplicate_by_number_change_blocked(self):
        """Renumbering an already-granted card into a colliding number is
        refused the same way."""
        self._make_light_hardware()
        self.test_ag_employee_1.add_doors(self.door)
        self._share_with_b()
        self._grant_b(self.door)  # card_b (1122334455) granted OK
        with self.assertRaises(ValidationError):
            self.card_b.sudo().write({'number': self.test_card_employee.number})

    def test_duplicate_allowed_when_not_sharing(self):
        """Regression: without sharing, the same number may exist and be
        granted in both companies - the guard must not fire."""
        self._make_light_hardware()
        self.test_ag_employee_1.add_doors(self.door)
        clone_card = self.env['hr.rfid.card'].create({
            'number': self.test_card_employee.number,
            'card_input_type': 'w34',
            'employee_id': self.employee_b.id,
            'company_id': self.company_b.id,
        })
        # B grants the clone on ITS OWN separate hardware - no shared module involved.
        ws_b = self.env['hr.rfid.webstack'].create({
            'name': 'B Own Stack', 'serial': '765432', 'company_id': self.company_b.id,
            'available': 'a', 'tz': 'Europe/Sofia', 'active': True,
        })
        ctrl_b = self.env['hr.rfid.ctrl'].create({
            'name': 'B Ctrl', 'ctrl_id': 91, 'webstack_id': ws_b.id})
        door_b = self.env['hr.rfid.door'].create({
            'name': 'B Door', 'number': 9101, 'controller_id': ctrl_b.id})
        self.env['hr.rfid.reader'].create({
            'name': 'BR1', 'number': 1, 'reader_type': '0',
            'controller_id': ctrl_b.id, 'door_id': door_b.id})
        rel = self.env['hr.rfid.access.group.door.rel'].sudo().create({
            'access_group_id': self.ag_b.id,
            'door_id': door_b.id,
            'time_schedule_id': self._ts_b(2).id,
        })
        self.assertTrue(rel, 'Unrelated duplicates must not be blocked')

    def test_foreign_grant_only_with_unrestricted_schedule(self):
        """B may only grant 24/7 (schedule 0) on the shared module - the
        controller's schedule slots belong to the owner."""
        self._make_light_hardware()
        self.test_ag_employee_1.add_doors(self.door)
        self._share_with_b()
        with self.assertRaises(ValidationError):
            self._grant_b(self.door, ts_number=2)
        # The owner itself is NOT restricted to schedule 0.
        ts_a2 = self.env['hr.rfid.time.schedule'].sudo().search([
            ('company_id', '=', self.company_a.id), ('number', '=', 2)], limit=1)
        rel_a = self.env['hr.rfid.access.group.door.rel'].sudo().create({
            'access_group_id': self.test_ag_partner_1.id,
            'door_id': self.door.id,
            'time_schedule_id': ts_a2.id,
        })
        self.assertTrue(rel_a, 'The owner may use any of its schedules')

    def test_unshared_door_not_grantable_by_other_company(self):
        """A door whose module is NOT shared with B cannot enter B's access
        groups even when B can technically reach the record (sudo import
        paths) - the guard is server-side, not just visibility."""
        self._make_light_hardware()
        self.test_ag_employee_1.add_doors(self.door)
        with self.assertRaises(ValidationError):
            self.env['hr.rfid.access.group.door.rel'].sudo().create({
                'access_group_id': self.ag_b.id,
                'door_id': self.door.id,
                'time_schedule_id': self._ts_b(0).id,
            })

    def test_ownership_stays_with_owner(self):
        """B operates the shared module but cannot take it over: changing the
        owner, changing the sharing list or deleting the module is refused."""
        self._make_light_hardware()
        self._share_with_b()
        ws = self.test_webstack_10_3_id
        with self.assertRaises(AccessError):
            ws.with_user(self.manager_b).write({'company_id': self.company_b.id})
        with self.assertRaises(AccessError):
            ws.with_user(self.manager_b).write({
                'shared_company_ids': [(6, 0, [self.company_b.id, self.company_c.id])]})
        with self.assertRaises(AccessError):
            ws.with_user(self.manager_b).unlink()
        # The owner-side manager (who sees both companies) CAN manage the
        # sharing list.
        ws.with_user(self.manager_ab).write({
            'shared_company_ids': [(6, 0, [self.company_b.id])]})

    def test_sharing_company_cannot_take_over_or_break_the_hardware(self):
        """The sharing company may READ the owner's hardware, never change it.
        Empirically confirmed attack paths before this was enforced: move the
        controllers onto its own module (taking the doors along), delete the
        owner's controller, and push a raw command to the physical device."""
        self._make_light_hardware()
        self._share_with_b()
        own_ws = self.env['hr.rfid.webstack'].create({
            'name': 'B Own Module', 'serial': '765431',
            'company_id': self.company_b.id, 'available': 'a',
            'tz': 'Europe/Sofia', 'active': True,
        })
        with self.assertRaises(AccessError):
            self.ctrl.with_user(self.manager_b).write({'webstack_id': own_ws.id})
        with self.assertRaises(AccessError):
            self.ctrl.with_user(self.manager_b).unlink()
        with self.assertRaises(AccessError):
            self.door.with_user(self.manager_b).write({'apb_mode': True})
        with self.assertRaises(AccessError):
            self.env['hr.rfid.command'].with_user(self.manager_b).create({
                'webstack_id': self.test_webstack_10_3_id.id,
                'controller_id': self.ctrl.id, 'cmd': 'DB'})
        # The owner is not restricted on its own hardware.
        self.door.with_user(self.manager_a).write({'apb_mode': True})
        self.assertTrue(self.door.apb_mode)

    def test_sharing_company_cannot_remove_the_owners_grants(self):
        """B manages the grants of its OWN people; the owner's grants on the
        shared door are not B's to delete."""
        self._make_light_hardware()
        self.test_ag_employee_1.add_doors(self.door)
        self._share_with_b()
        rel_b = self._grant_b(self.door)
        rel_a = self.env['hr.rfid.access.group.door.rel'].sudo().search([
            ('access_group_id', '=', self.test_ag_employee_1.id),
            ('door_id', '=', self.door.id)])
        self.assertTrue(rel_a)
        with self.assertRaises(AccessError):
            rel_a.with_user(self.manager_b).unlink()
        # Its own grant it may drop.
        rel_b.with_user(self.manager_b).unlink()

    def test_unshare_revokes_access(self):
        """Removing B from the sharing list drops B's grants, queues the
        remove-card commands and hides the hardware from B again."""
        self._make_light_hardware()
        self.test_ag_employee_1.add_doors(self.door)
        self._share_with_b()
        self._grant_b(self.door)
        self.assertTrue(self.env['hr.rfid.card.door.rel'].sudo().search([
            ('card_id', '=', self.card_b.id), ('door_id', '=', self.door.id)]))
        self.test_webstack_10_3_id.with_user(self.manager_a).write({
            'shared_company_ids': [(5, 0, 0)]})
        self.assertFalse(self.env['hr.rfid.access.group.door.rel'].sudo().search([
            ('access_group_id', '=', self.ag_b.id), ('door_id', '=', self.door.id)]),
            "B's group grant must be gone after unsharing")
        self.assertFalse(self.env['hr.rfid.card.door.rel'].sudo().search([
            ('card_id', '=', self.card_b.id), ('door_id', '=', self.door.id)]),
            "B's card grant must be gone after unsharing")
        self.assertTrue(self.env['hr.rfid.command'].sudo().search([
            ('controller_id', '=', self.ctrl.id), ('cmd', '=', 'D1'),
            ('card_number', '=', self.card_b.number)]),
            'A remove-card command must be queued for the controller')
        self.assertFalse(self.env['hr.rfid.ctrl'].with_user(self.manager_b).search(
            [('id', '=', self.ctrl.id)]),
            'B must not see the hardware any more')

    def test_replace_wizard_carries_sharing(self):
        """Swapping a broken module for a new one keeps serving both
        companies without re-configuration."""
        self._make_light_hardware()
        self._share_with_b()
        new_ws = self.env['hr.rfid.webstack'].create({
            'name': 'Replacement Stack', 'serial': '345678',
            'company_id': self.company_a.id, 'available': 'a',
            'tz': 'Europe/Sofia', 'active': False,
        })
        wiz = self.env['hr.rfid.webstack.replace.wiz'].create({
            'source_webstack_id': self.test_webstack_10_3_id.id,
            'destination_webstack_id': new_ws.id,
        })
        wiz.source_controller_ids = [(6, 0, self.test_webstack_10_3_id.controllers.ids)]
        wiz.confirm_transfer()
        self.assertEqual(new_ws.shared_company_ids, self.company_b,
                         'The replacement module must keep the sharing list')


@tagged('standard', 'at_install', 'rfid', 'rfid_sharing')
class TestSharedModuleWorkcodes(SharedModuleCase):
    """Work codes of the badging person's company are recognised on the
    shared module (with the owner's codes as fallback)."""

    def test_workcode_of_badging_persons_company_is_recognised(self):
        # Work code VALUES are globally unique; each company defines its own
        # set of codes. The regression under test: the module used to look up
        # codes ONLY in its owner's company, so a sharing company's code
        # entered on the shared module was silently dropped to raw text.
        self._share_with_b()
        wc_b = self.env['hr.rfid.workcode'].create({
            'name': 'B Shift Start', 'workcode': '0007',
            'company_id': self.company_b.id,
        })
        wc_a = self.env['hr.rfid.workcode'].create({
            'name': 'A Shift Start', 'workcode': '0008',
            'company_id': self.company_a.id,
        })
        event_dict = {}
        self.test_webstack_10_3_id._hw_resolve_workcode(event_dict, '0007', self.card_b)
        self.assertEqual(event_dict.get('workcode_id'), wc_b.id,
                         "The badging person's own work code must be recognised")
        event_dict = {}
        self.test_webstack_10_3_id._hw_resolve_workcode(
            event_dict, '0008', self.test_card_employee)
        self.assertEqual(event_dict.get('workcode_id'), wc_a.id,
                         "The owner's work code keeps working for the owner's people")
        event_dict = {}
        self.test_webstack_10_3_id._hw_resolve_workcode(event_dict, '9999', self.card_b)
        self.assertEqual(event_dict.get('workcode'), '9999',
                         'An unknown code is kept as raw text, as before')


@tagged('standard', 'at_install', 'rfid', 'rfid_sharing', 'rfid_sharing_e2e')
class TestSharedModuleE2E(SharedModuleCase, HttpCase):
    """Full walk of the real flow through the device HTTP endpoint: share ->
    grant -> command delivery -> badge -> event lands in the right company ->
    system events visible to both -> unshare."""

    _registry_readonly_enabled = False

    def test_shared_module_full_lifecycle(self):
        # Phase 0/1 - owner provisions the hardware through the real device
        # flow and shares the module with B.
        self._add_iCon110()
        door = self.c_110.door_ids[0]
        self.test_ag_employee_1.add_doors(door)
        self._share_with_b()

        # Phase 2 - B grants its own person on the shared door (24/7).
        self._grant_b(door)
        rel = self.env['hr.rfid.card.door.rel'].sudo().search([
            ('card_id', '=', self.card_b.id), ('door_id', '=', door.id)])
        self.assertTrue(rel, "B's card must be granted on the shared door")
        # The add-card command reaches the physical controller.
        response = self._hearbeat(self.test_webstack_10_3_id)
        delivered = []
        while response != {}:
            delivered.append(response['cmd']['c'])
            response = self._send_cmd_response(response)
        self.assertIn('D1', delivered, 'The controller must receive the add-card command')

        # Phase 3 - B's person badges on the shared door.
        events_before = self.env['hr.rfid.event.user'].sudo().search([])
        self._make_event(self.c_110, card=self.card_b.number, reader=1, event_code=3)
        event = self.env['hr.rfid.event.user'].sudo().search([]) - events_before
        self.assertEqual(len(event), 1, 'Exactly one user event must be recorded')
        self.assertEqual(event.employee_id, self.employee_b,
                         'The event must belong to the person from B')
        # The event is B's private business: visible to B, not to A, not to C.
        self.assertTrue(self.env['hr.rfid.event.user'].with_user(self.manager_b)
                        .search([('id', '=', event.id)]))
        self.assertFalse(self.env['hr.rfid.event.user'].with_user(self.manager_a)
                         .search([('id', '=', event.id)]),
                         "A must not see B's personal events")
        self.assertFalse(self.env['hr.rfid.event.user'].with_user(self.manager_c)
                         .search([('id', '=', event.id)]))

        # Phase 4 - an unknown card on the shared door raises a system event
        # that BOTH companies see (it is their common entrance), C sees nothing.
        self._make_event(self.c_110, card='9988776655', reader=1,
                         event_code=4, system_event=True)
        sys_event = self.env['hr.rfid.event.system'].sudo().search(
            [('card_number', '=', '9988776655')], limit=1)
        self.assertTrue(sys_event, 'The unknown card must produce a system event')
        for user, expected in ((self.manager_a, True), (self.manager_b, True),
                               (self.manager_c, False)):
            found = bool(self.env['hr.rfid.event.system'].with_user(user)
                         .search([('id', '=', sys_event.id)]))
            self.assertEqual(found, expected,
                             'System event visibility wrong for %s' % user.login)

        # Phase 5 - attribution stays deterministic when the other company
        # holds the same number on an UNGRANTED card (allowed - only granted
        # duplicates are blocked): the granted card wins.
        visitor_a = self.env['hr.employee'].create({
            'name': 'A Visitor Without Access',
            'company_id': self.company_a.id,
        })
        self.env['hr.rfid.card'].create({
            'number': self.card_b.number,
            'card_input_type': 'w34',
            'employee_id': visitor_a.id,
            'company_id': self.company_a.id,
        })
        events_before = self.env['hr.rfid.event.user'].sudo().search([])
        # A minute-earlier timestamp so the duplicate-event guard (same
        # card/reader/second) does not swallow this second badge.
        self._make_event(self.c_110, card=self.card_b.number, reader=1,
                         event_code=3, time=self._time_10_3(120))
        event2 = self.env['hr.rfid.event.user'].sudo().search([]) - events_before
        self.assertEqual(event2.employee_id, self.employee_b,
                         'The granted card must win the attribution')

        # Phase 6 - unshare: grants drop, removal reaches the controller,
        # B loses sight of the hardware.
        self.test_webstack_10_3_id.with_user(self.manager_a).write({
            'shared_company_ids': [(5, 0, 0)]})
        self.assertFalse(self.env['hr.rfid.card.door.rel'].sudo().search([
            ('card_id', '=', self.card_b.id), ('door_id', '=', door.id)]))
        response = self._hearbeat(self.test_webstack_10_3_id)
        delivered = []
        while response != {}:
            delivered.append(response['cmd']['c'])
            response = self._send_cmd_response(response)
        self.assertIn('D1', delivered, 'The controller must receive the removal')
        self.assertFalse(self.env['hr.rfid.ctrl'].with_user(self.manager_b)
                         .search([('id', '=', self.c_110.id)]))

        # Final invariant - C never saw any of THIS module's hardware. Scoped
        # to the records this test created: a database with demo data also
        # holds controller-less readers and company-less rows that a pre-existing
        # rule branch shows to everyone, which has nothing to do with sharing
        # and would make this sweep fail for the wrong reason.
        webstack = self.test_webstack_10_3_id
        for model, domain in (
            ('hr.rfid.webstack', [('id', '=', webstack.id)]),
            ('hr.rfid.ctrl', [('webstack_id', '=', webstack.id)]),
            ('hr.rfid.door', [('controller_id.webstack_id', '=', webstack.id)]),
            ('hr.rfid.reader', [('controller_id.webstack_id', '=', webstack.id)]),
            ('hr.rfid.command', [('webstack_id', '=', webstack.id)]),
            ('hr.rfid.card.door.rel', [('door_id.controller_id.webstack_id', '=', webstack.id)]),
            ('hr.rfid.access.group.door.rel', [('door_id.controller_id.webstack_id', '=', webstack.id)]),
        ):
            self.assertFalse(
                self.env[model].with_user(self.manager_c).search(domain),
                'C must see no %s of the shared module' % model)
