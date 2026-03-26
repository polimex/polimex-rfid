import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class OnboardingOnboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    @api.model
    def action_close_panel_rfid_setup(self):
        self.action_close_panel('hr_rfid.onboarding_rfid_setup')

    def _prepare_rendering_values(self):
        """Auto-complete onboarding steps based on existing data."""
        self.ensure_one()
        if self == self.env.ref('hr_rfid.onboarding_rfid_setup', raise_if_not_found=False):
            company = self.env.company
            steps_checks = [
                ('hr_rfid.onboarding_step_add_webstack',
                 'hr.rfid.webstack', [('company_id', '=', company.id), ('active', '=', True)]),
                ('hr_rfid.onboarding_step_scan_controllers',
                 'hr.rfid.ctrl', [('webstack_id.company_id', '=', company.id)]),
                ('hr_rfid.onboarding_step_create_access_group',
                 'hr.rfid.access.group', [('company_id', '=', company.id), ('door_ids', '!=', False)]),
                ('hr_rfid.onboarding_step_register_card',
                 'hr.rfid.card', [('company_id', '=', company.id), ('active', '=', True)]),
            ]
            for step_xmlid, model_name, domain in steps_checks:
                step = self.env.ref(step_xmlid, raise_if_not_found=False)
                if step and step.current_step_state == 'not_done':
                    if self.env[model_name].search_count(domain, limit=1):
                        step.action_set_just_done()
        return super()._prepare_rendering_values()

    @api.model
    def action_fetch_rfid_onboarding(self):
        """Fetch RFID onboarding step data for the frontend banner."""
        onboarding = self.search([('route_name', '=', 'hr_rfid_setup')], limit=1)
        if not onboarding:
            return {'closed': True}
        # Use a savepoint to handle concurrent progress creation gracefully.
        # When multiple browser tabs or requests load the RFID dashboard
        # simultaneously, _search_or_create_progress can raise a
        # UniqueViolation on the onboarding_progress_onboarding_company_uniq
        # constraint. The savepoint allows us to roll back only the failed
        # INSERT while keeping the rest of the transaction intact.
        try:
            with self.env.cr.savepoint():
                onboarding._search_or_create_progress()
        except Exception:
            _logger.debug("Concurrent onboarding progress creation, re-reading existing record.")
            onboarding.invalidate_recordset()
        if onboarding.is_onboarding_closed or onboarding.current_onboarding_state == 'done':
            return {'closed': True}
        values = onboarding._prepare_rendering_values()
        return {
            'closed': False,
            'onboarding_state': onboarding.current_onboarding_state,
            'steps': [
                self._prepare_step_data(step, values)
                for step in values['steps']
            ],
        }

    def _prepare_step_data(self, step, values):
        """Build step dict with optional extra actions based on user rights."""
        data = {
            'id': step.id,
            'title': step.title,
            'description': step.description,
            'button_text': step.button_text,
            'done_text': step.done_text,
            'done_icon': step.done_icon,
            'state': values['state'].get(step.id, 'not_done'),
            'action': step.panel_step_open_action_name,
        }
        # Add "Discover" extra action for webstack step if user has discovery rights
        add_webstack_step = self.env.ref('hr_rfid.onboarding_step_add_webstack', raise_if_not_found=False)
        if step == add_webstack_step and self.env.user.has_group('hr_rfid.hr_rfid_view_module_discovery'):
            data['extra_action'] = {
                'label': 'Discover',
                'method': 'action_open_step_scan_controllers',
            }
        return data
