from odoo import api, models


class OnboardingOnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    @api.model
    def action_open_step_service_define(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'rfid_service_base.hr_rfid_service_action')

    @api.model
    def action_open_step_service_first_sale(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'rfid_service_base.hr_rfid_service_sale_action')
