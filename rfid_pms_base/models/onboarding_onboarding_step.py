from odoo import api, models


class OnboardingOnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    @api.model
    def action_open_step_pms_access_group(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'hr_rfid.hr_rfid_access_group_action')

    @api.model
    def action_open_step_pms_first_room(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'rfid_pms_base.action_window_room')
