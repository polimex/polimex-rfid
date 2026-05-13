# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "voting_onboarding")
class TestVotingOnboarding(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.onboarding = cls.env.ref('hr_rfid_vertical_elections.onboarding_voting_setup')
        cls.step_display = cls.env.ref('hr_rfid_vertical_elections.onboarding_step_voting_display')
        cls.step_participants = cls.env.ref('hr_rfid_vertical_elections.onboarding_step_voting_participants')
        cls.step_items = cls.env.ref('hr_rfid_vertical_elections.onboarding_step_voting_items')
        cls.step_session = cls.env.ref('hr_rfid_vertical_elections.onboarding_step_voting_session')
        cls.onboarding._search_or_create_progress()

    def test_panel_has_four_steps_in_order(self):
        steps = self.onboarding.step_ids.sorted('sequence')
        self.assertEqual(len(steps), 4)
        self.assertEqual(steps[0], self.step_display)
        self.assertEqual(steps[1], self.step_participants)
        self.assertEqual(steps[2], self.step_items)
        self.assertEqual(steps[3], self.step_session)

    def test_all_step_actions_resolve_to_real_windows(self):
        step_model = self.env['onboarding.onboarding.step']
        self.assertEqual(step_model.action_open_step_voting_display()['res_model'], 'voting.display')
        self.assertEqual(step_model.action_open_step_voting_participants()['res_model'], 'voting.participants')
        self.assertEqual(step_model.action_open_step_voting_items()['res_model'], 'voting.item')
        self.assertEqual(step_model.action_open_step_voting_session()['res_model'], 'voting.session')

    def test_each_step_completes_independently(self):
        # Create one record per model and verify only that step flips.
        display = self.env['voting.display'].create({
            'name': 'OnbDisplay', 'company_id': self.company.id,
        })
        self.onboarding._prepare_rendering_values()
        self.assertEqual(self.step_display.current_step_state, 'done')
        self.assertEqual(self.step_participants.current_step_state, 'not_done')

        participants = self.env['voting.participants'].create({
            'name': 'OnbVoters', 'company_id': self.company.id,
        })
        self.onboarding._prepare_rendering_values()
        self.assertEqual(self.step_participants.current_step_state, 'done')
        self.assertEqual(self.step_items.current_step_state, 'not_done')

        self.env['voting.item'].create({
            'name': 'OnbItem', 'short_description': 'Question 1',
            'company_id': self.company.id,
        })
        self.onboarding._prepare_rendering_values()
        self.assertEqual(self.step_items.current_step_state, 'done')
        self.assertEqual(self.step_session.current_step_state, 'not_done')

        self.env['voting.session'].create({
            'name': 'OnbSession',
            'company_id': self.company.id,
            'planned_date': fields.Date.today(),
            'participant_group_id': participants.id,
            'display_id': display.id,
        })
        self.onboarding._prepare_rendering_values()
        self.assertEqual(self.step_session.current_step_state, 'done')
