from odoo import api, models


class OnboardingOnboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    @api.model
    def action_close_panel_voting_setup(self):
        self.sudo().action_close_panel('hr_rfid_vertical_elections.onboarding_voting_setup')

    def _prepare_rendering_values(self):
        """A voting session needs a display, a participants list and at
        least one voting item before it can be opened. Each step is
        auto-completed when the corresponding records exist for the
        current company."""
        self.ensure_one()
        ref = self.env.ref('hr_rfid_vertical_elections.onboarding_voting_setup', raise_if_not_found=False)
        if self == ref:
            company = self.env.company
            steps_checks = [
                ('hr_rfid_vertical_elections.onboarding_step_voting_display',
                 'voting.display', [('company_id', '=', company.id)]),
                ('hr_rfid_vertical_elections.onboarding_step_voting_participants',
                 'voting.participants', [('company_id', '=', company.id)]),
                ('hr_rfid_vertical_elections.onboarding_step_voting_items',
                 'voting.item', [('company_id', '=', company.id)]),
                ('hr_rfid_vertical_elections.onboarding_step_voting_session',
                 'voting.session', [('company_id', '=', company.id)]),
            ]
            for step_xmlid, model_name, domain in steps_checks:
                step = self.env.ref(step_xmlid, raise_if_not_found=False)
                if step and step.current_step_state == 'not_done':
                    if self.env[model_name].search_count(domain, limit=1):
                        step.action_set_just_done()
        return super()._prepare_rendering_values()
