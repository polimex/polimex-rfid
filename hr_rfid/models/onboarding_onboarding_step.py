from odoo import _, api, models


class OnboardingOnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    @api.model
    def action_open_step_rfid_settings(self):
        return self.env['ir.actions.act_window']._for_xml_id('hr_rfid.action_hr_rfid_configuration')

    @api.model
    def action_open_step_add_webstack(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'hr_rfid.hr_rfid_webstack_manual_create_action')

    @api.model
    def action_open_step_scan_controllers(self):
        return self.env['ir.actions.act_window']._for_xml_id(
            'hr_rfid.hr_rfid_webstack_discovery_action')

    @api.model
    def action_open_step_create_access_group(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Access Group'),
            'res_model': 'hr.rfid.access.group',
            'views': [(False, 'form')],
            'target': 'new',
        }

    @api.model
    def action_open_step_register_card(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Register Card'),
            'res_model': 'hr.rfid.card',
            'views': [(False, 'form')],
            'target': 'new',
        }
