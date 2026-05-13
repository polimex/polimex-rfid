from odoo import api, models


class OnboardingOnboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    @api.model
    def action_close_panel_pms_setup(self):
        self.sudo().action_close_panel('rfid_pms_base.onboarding_pms_setup')

    def _prepare_rendering_values(self):
        """Auto-complete onboarding steps when the relevant data already
        exists in the current company. The checks mirror the real
        prerequisites for opening a reservation: the room records the
        operator will work from need an access group with doors and a
        door of their own."""
        self.ensure_one()
        if self == self.env.ref('rfid_pms_base.onboarding_pms_setup', raise_if_not_found=False):
            company = self.env.company
            steps_checks = [
                ('rfid_pms_base.onboarding_step_pms_access_group',
                 'hr.rfid.access.group',
                 [('company_id', '=', company.id), ('door_ids', '!=', False)]),
                ('rfid_pms_base.onboarding_step_pms_first_room',
                 'rfid_pms_base.room',
                 [('company_id', '=', company.id)]),
            ]
            for step_xmlid, model_name, domain in steps_checks:
                step = self.env.ref(step_xmlid, raise_if_not_found=False)
                if step and step.current_step_state == 'not_done':
                    if self.env[model_name].search_count(domain, limit=1):
                        step.action_set_just_done()
        return super()._prepare_rendering_values()
