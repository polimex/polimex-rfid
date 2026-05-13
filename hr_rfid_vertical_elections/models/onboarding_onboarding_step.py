from odoo import api, models


class OnboardingOnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    @api.model
    def action_open_step_voting_display(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'hr_rfid_vertical_elections.voting_display_action')

    @api.model
    def action_open_step_voting_participants(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'hr_rfid_vertical_elections.voting_participants_action')

    @api.model
    def action_open_step_voting_items(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'hr_rfid_vertical_elections.voting_item_action')

    @api.model
    def action_open_step_voting_session(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'hr_rfid_vertical_elections.vote_session_action')
