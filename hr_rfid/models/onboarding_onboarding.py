import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class OnboardingOnboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    @api.model
    def action_close_panel_rfid_setup(self):
        self.sudo().action_close_panel('hr_rfid.onboarding_rfid_setup')

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
    def close_onboarding_panel(self, route_name):
        """Close (hide) the onboarding panel identified by ``route_name``.

        Generic counterpart of :meth:`get_onboarding_panel_html` so the OWL
        banner can dismiss any onboarding by its route — no per-onboarding
        close action is required.
        """
        onboarding = self.sudo().search([('route_name', '=', route_name)], limit=1)
        if onboarding:
            onboarding.action_close()

    @api.model
    def get_onboarding_panel_html(self, route_name):
        """Render Odoo's standard onboarding panel for ``route_name``.

        Reuses core's ``onboarding.onboarding_panel`` QWeb template so the
        in-app banner is pixel-identical to Odoo's native onboarding —
        translated server-side and overflow-safe via the core onboarding
        SCSS — instead of a hand-maintained Bootstrap copy that drifts and
        breaks on longer translations.

        Returns the rendered HTML (``Markup``) for the OWL banner to inject,
        or ``False`` when there is nothing to show (unknown route, or the
        user has closed the panel).
        """
        onboarding = self.sudo().search([('route_name', '=', route_name)], limit=1)
        if not onboarding:
            return False
        # The onboarding panel is non-critical UI: never let it break the
        # host list view. A savepoint also absorbs the rare unique-constraint
        # race when several dashboard tabs create the progress record at once.
        try:
            with self.env.cr.savepoint():
                onboarding._search_or_create_progress()
                if onboarding.is_onboarding_closed:
                    return False
                values = onboarding._prepare_rendering_values()
                return self.env['ir.qweb']._render('onboarding.onboarding_panel', values)
        except Exception:
            _logger.warning(
                "Could not render onboarding panel %r; hiding it for this load.",
                route_name, exc_info=True,
            )
            onboarding.invalidate_recordset()
            return False
