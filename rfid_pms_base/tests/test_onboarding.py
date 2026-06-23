# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_pms", "rfid_pms_onboarding")
class TestRfidPmsOnboarding(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.onboarding = cls.env.ref('rfid_pms_base.onboarding_pms_setup')
        cls.step_ag = cls.env.ref('rfid_pms_base.onboarding_step_pms_access_group')
        cls.step_room = cls.env.ref('rfid_pms_base.onboarding_step_pms_first_room')
        cls.onboarding._search_or_create_progress()

    def test_panel_has_two_steps_in_order(self):
        steps = self.onboarding.step_ids.sorted('sequence')
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0], self.step_ag)
        self.assertEqual(steps[1], self.step_room)

    def test_step_actions_resolve_to_real_windows(self):
        step_model = self.env['onboarding.onboarding.step']
        ag_action = step_model.action_open_step_pms_access_group()
        room_action = step_model.action_open_step_pms_first_room()
        self.assertEqual(ag_action['res_model'], 'hr.rfid.access.group')
        self.assertEqual(room_action['res_model'], 'rfid_pms_base.room')

    def test_panel_html_renders_for_route(self):
        # The Hotel Rooms kanban wires the banner via this route_name; the
        # shared renderer (hr_rfid) must produce the native onboarding markup.
        html = self.env['onboarding.onboarding'].get_onboarding_panel_html('rfid_pms_base_setup')
        self.assertTrue(html, "The PMS onboarding route must render a panel")
        self.assertIn('o_onboarding_main', html)

    def test_ag_step_completes_when_ag_with_door_exists(self):
        # Build the minimum hardware for an AG to have at least one door.
        webstack = self.env["hr.rfid.webstack"].create({
            "name": "OnbWS", "serial": "ONB001",
            "company_id": self.company.id,
            "available": "a", "tz": "Europe/Sofia",
        })
        controller = self.env["hr.rfid.ctrl"].create({
            "name": "OnbC", "ctrl_id": 77, "webstack_id": webstack.id,
        })
        door = self.env["hr.rfid.door"].create({
            "name": "OnbDoor", "number": 7777,
            "controller_id": controller.id, "company_id": self.company.id,
        })
        ag = self.env["hr.rfid.access.group"].create({
            "name": "OnbAG", "company_id": self.company.id,
        })
        ag.write({"door_ids": [(0, 0, {"door_id": door.id})]})

        self.onboarding._prepare_rendering_values()
        self.assertEqual(self.step_ag.current_step_state, 'done')
        # Room step must NOT be triggered by AG presence alone.
        self.assertEqual(self.step_room.current_step_state, 'not_done')

    def test_room_step_completes_when_room_exists(self):
        webstack = self.env["hr.rfid.webstack"].create({
            "name": "OnbWS2", "serial": "ONB002",
            "company_id": self.company.id,
            "available": "a", "tz": "Europe/Sofia",
        })
        controller = self.env["hr.rfid.ctrl"].create({
            "name": "OnbC2", "ctrl_id": 78, "webstack_id": webstack.id,
        })
        door = self.env["hr.rfid.door"].create({
            "name": "OnbDoor2", "number": 7778,
            "controller_id": controller.id, "company_id": self.company.id,
        })
        ag = self.env["hr.rfid.access.group"].create({
            "name": "OnbAG2", "company_id": self.company.id,
        })
        self.env["rfid_pms_base.room"].create({
            "name": "OnbRoom", "number": 7779,
            "company_id": self.company.id,
            "access_group_id": ag.id, "door_id": door.id,
        })
        self.onboarding._prepare_rendering_values()
        self.assertEqual(self.step_room.current_step_state, 'done')
