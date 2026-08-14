import logging

import psycopg2
from psycopg2 import errors as pgerrors

from odoo import api, models
from odoo.exceptions import ConcurrencyError
from odoo.tools import SQL, mute_logger

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
        banner can dismiss any onboarding by its route - no per-onboarding
        close action is required.
        """
        onboarding = self.sudo().search([('route_name', '=', route_name)], limit=1)
        if onboarding:
            onboarding.action_close()

    def _rfid_ensure_onboarding_progress(self):
        """Make sure the tracking record behind this panel is readable here.

        Returns ``True`` when it is, ``False`` when another request is
        creating the very same one right now and ours is therefore not
        readable yet.

        Two browser tabs opening the list for the first time both find no
        tracking record and both insert one; the second insert hits the
        unique index on (onboarding, company)
        (odoo/addons/onboarding/models/onboarding_progress.py:28). Until now
        that lost insert surfaced twice in the customer's log - once as a
        PostgreSQL error line, once as our own warning - and cost the user
        the banner for that page load.

        We prevent the collision instead of cleaning up after it, the way
        core keeps two transactions from processing the same incoming mail
        twice: a try-lock on a key derived from what must stay unique
        (odoo/addons/mail/models/mail_thread.py:1470-1475). Whoever does not
        get the lock does not insert at all, so no error is produced.
        """
        self.ensure_one()
        if self.current_progress_id:
            return True

        # Same shape as the unique index: one company at a time for a
        # per-company onboarding, one globally otherwise.
        lock_key = 'hr_rfid.onboarding.progress:%s:%s' % (
            self.id, self.env.company.id if self.is_per_company else 0,
        )
        self.env.cr.execute(SQL('SELECT pg_try_advisory_xact_lock(hashtext(%s))', lock_key))
        if not self.env.cr.fetchone()[0]:
            _logger.debug(
                "Onboarding %s is being started by a concurrent request; "
                "rendering its initial state.", self.id,
            )
            return False

        try:
            # The lock only covers requests that overlap in time. One that
            # finished a moment before we asked for the lock left the row
            # committed, so our insert can still be rejected - a legitimate
            # outcome here, not a fault, which is why the PostgreSQL error
            # line is muted for the duration exactly as core mutes it for
            # its own may-lose-a-race inserts
            # (odoo/addons/base/wizard/base_partner_merge.py:173,
            # odoo/addons/product/models/product_product.py:768,
            # odoo/addons/mail/models/mail_presence.py:70-73). The flush is
            # explicit so the insert - and any rejection of it - happens
            # while both guards are still in place.
            with mute_logger('odoo.sql_db'), self.env.cr.savepoint():
                self._search_or_create_progress()
                self.env.flush_all()
        except pgerrors.UniqueViolation:
            # Read it back: whoever won has committed it, so it is there for
            # every request whose view of the database is newer than that
            # commit. Requests older than it (Odoo runs REPEATABLE READ -
            # odoo/sql_db.py:373) keep looking at a database without it and
            # get the initial state instead; the next page load reads it
            # normally either way.
            self.invalidate_recordset()
        return bool(self.current_progress_id)

    def _rfid_initial_rendering_values(self):
        """Panel content for a first run whose tracking record is not ours.

        Same keys as core's ``_prepare_rendering_values``
        (odoo/addons/onboarding/models/onboarding_onboarding.py:125-134),
        rebuilt here because that one goes through the tracking record and
        ``_get_and_update_onboarding_state`` requires exactly one
        (odoo/addons/onboarding/models/onboarding_progress.py:60).

        Deliberately writes nothing. A panel that has only just been started
        is neither finished nor closed, so this is what the user would see
        anyway - and marking steps done from here would leave step-tracking
        rows behind that belong to nobody, plus repeat the same collision on
        a second unique index
        (odoo/addons/onboarding/models/onboarding_progress_step.py:21).
        """
        self.ensure_one()
        return {
            'close_method': self.panel_close_action_name,
            'close_model': 'onboarding.onboarding',
            'steps': self.step_ids,
            # One entry per step, keyed by step id, like
            # _get_and_update_onboarding_state. No 'onboarding_state' entry,
            # so the "all done" overlay stays hidden - see the t-if in
            # onboarding.onboarding_container.
            'state': {step.id: step.current_step_state for step in self.step_ids},
            'text_completed': self.text_completed,
        }

    @api.model
    def get_onboarding_panel_html(self, route_name):
        """Render Odoo's standard onboarding panel for ``route_name``.

        Reuses core's ``onboarding.onboarding_panel`` QWeb template so the
        in-app banner is pixel-identical to Odoo's native onboarding -
        translated server-side and overflow-safe via the core onboarding
        SCSS - instead of a hand-maintained Bootstrap copy that drifts and
        breaks on longer translations.

        Returns the rendered HTML (``Markup``) for the OWL banner to inject,
        or ``False`` when there is nothing to show (unknown route, or the
        user has closed the panel).
        """
        onboarding = self.sudo().search([('route_name', '=', route_name)], limit=1)
        if not onboarding:
            return False
        try:
            if onboarding._rfid_ensure_onboarding_progress():
                if onboarding.is_onboarding_closed:
                    return False
                values = onboarding._prepare_rendering_values()
            else:
                values = onboarding._rfid_initial_rendering_values()
            return self.env['ir.qweb']._render('onboarding.onboarding_panel', values)
        except (psycopg2.Error, ConcurrencyError):
            # Not ours to answer, for either of two reasons.
            #
            # When two requests collide over the same row, or one cannot take a
            # lock, Odoo does not fail the request - it rolls back and runs it
            # again from the start, up to five times (odoo/service/model.py:192
            # catches IntegrityError, OperationalError and ConcurrencyError,
            # odoo/service/model.py:29 lists the database errors it waits and
            # retries on - a lock it could not take, a deadlock, and two
            # transactions changing the same thing at once - and
            # odoo/service/model.py:216-228 does the waiting). Answering here
            # would spend that second attempt on a page whose banner is quietly
            # missing.
            #
            # Every other database error is worse, not better: PostgreSQL
            # refuses the rest of the transaction once a statement has failed,
            # so from here on nothing else in this request can run either. The
            # only savepoint here covers the insert in
            # _rfid_ensure_onboarding_progress; a failure raised anywhere else -
            # reading the steps, rendering the panel - leaves nothing to fall
            # back to. Reporting that as a hidden banner would
            # tell the operator one small thing was skipped while the whole page
            # is already lost. Core takes the same position wherever a
            # best-effort handler sits over the database
            # (odoo/addons/mail/models/mail_mail.py:918 - "chances are that the
            # cursor ... [is] unusable, causing further errors").
            raise
        except Exception:
            # The onboarding panel is non-critical UI: never let it break the
            # host list view.
            _logger.warning(
                "Could not render onboarding panel %r; hiding it for this load.",
                route_name, exc_info=True,
            )
            onboarding.invalidate_recordset()
            return False
