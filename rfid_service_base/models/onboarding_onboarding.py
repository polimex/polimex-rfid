from odoo import api, models


class OnboardingOnboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    @api.model
    def action_close_panel_service_setup(self):
        self.sudo().action_close_panel('rfid_service_base.onboarding_service_setup')

    def _prepare_rendering_values(self):
        """Auto-complete onboarding steps when the relevant data already
        exists in the current company. Each visitor needs a service
        (catalog entry) and a sale (the actual issued card)."""
        self.ensure_one()
        if self == self.env.ref('rfid_service_base.onboarding_service_setup', raise_if_not_found=False):
            company = self.env.company
            steps_checks = [
                ('rfid_service_base.onboarding_step_service_define',
                 'rfid.service',
                 [('company_id', '=', company.id), ('active', '=', True)]),
                ('rfid_service_base.onboarding_step_service_first_sale',
                 'rfid.service.sale',
                 [('company_id', '=', company.id)]),
            ]
            for step_xmlid, model_name, domain in steps_checks:
                step = self.env.ref(step_xmlid, raise_if_not_found=False)
                if step and step.current_step_state == 'not_done':
                    if self.env[model_name].search_count(domain, limit=1):
                        step.action_set_just_done()
        return super()._prepare_rendering_values()
