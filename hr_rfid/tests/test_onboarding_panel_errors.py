# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""The setup banner may hide itself, but only when the page survives without it.

Hiding the banner when something goes wrong is right: it is a piece of help
above a list, and nobody should lose the list over it.

It is wrong whenever the database is the thing that said no. Odoo answers some
of those by running the whole request again - two visitors changing the same
thing at the same instant, or a row that was momentarily locked - and answering
here would use up that second attempt. It refuses the rest after any other one,
so from that point on the page cannot be built at all. In both cases a hidden
banner is a comforting message about a page the visitor is not going to get.
"""
from unittest.mock import patch

from psycopg2 import errors as pgerrors

from odoo.exceptions import ConcurrencyError
from odoo.tests import TransactionCase, tagged

BANNER_LOG = 'odoo.addons.hr_rfid.models.onboarding_onboarding'


@tagged('post_install', '-at_install', 'rfid_onboarding')
class TestOnboardingPanelFailures(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Onboarding = self.env['onboarding.onboarding']

    def _render_with(self, failure):
        """Render the banner while the work behind it fails with ``failure``."""

        def _fail(records):
            raise failure

        with patch.object(
            type(self.Onboarding), '_rfid_ensure_onboarding_progress', _fail,
        ):
            return self.Onboarding.get_onboarding_panel_html('hr_rfid_setup')

    def _assert_passed_on(self, failure):
        """The failure travels on - and is never dressed up as a hidden banner.

        assertRaises is on the inside on purpose: it takes the exception, so
        the surrounding check gets to look at what was written to the log.
        """
        with self.assertNoLogs(BANNER_LOG, level='WARNING'):
            with self.assertRaises(type(failure)):
                self._render_with(failure)

    # ── Odoo will run the request again: do not answer in its place ───

    def test_two_visitors_changing_the_same_thing_is_passed_on(self):
        self._assert_passed_on(pgerrors.SerializationFailure('could not serialize access'))

    def test_a_row_that_could_not_be_locked_is_passed_on(self):
        self._assert_passed_on(pgerrors.LockNotAvailable('could not obtain lock'))

    def test_a_deadlock_is_passed_on(self):
        self._assert_passed_on(pgerrors.DeadlockDetected('deadlock detected'))

    def test_odoos_own_signal_to_run_the_request_again_is_passed_on(self):
        self._assert_passed_on(ConcurrencyError('retry this request'))

    # ── The database refused: the page is already lost, say so ───────

    def test_a_column_the_database_does_not_know_is_passed_on(self):
        self._assert_passed_on(
            pgerrors.UndefinedColumn('column "x" does not exist'),
        )

    def test_a_value_the_database_will_not_accept_is_passed_on(self):
        self._assert_passed_on(
            pgerrors.InvalidTextRepresentation('invalid input syntax for type integer'),
        )

    def test_work_attempted_after_the_transaction_died_is_passed_on(self):
        self._assert_passed_on(
            pgerrors.InFailedSqlTransaction('current transaction is aborted'),
        )

    # ── Anything else: the page is fine, keep it ─────────────────────

    def test_anything_else_only_costs_the_banner(self):
        with self.assertLogs(BANNER_LOG, level='WARNING'):
            rendered = self._render_with(ValueError('something unrelated went wrong'))
        self.assertFalse(
            rendered,
            'A fault in the setup banner must hide the banner, not break the '
            'page it sits on',
        )

    def test_a_missing_template_only_costs_the_banner(self):
        with self.assertLogs(BANNER_LOG, level='WARNING'):
            rendered = self._render_with(KeyError('onboarding.onboarding_panel'))
        self.assertFalse(
            rendered,
            'A fault in the setup banner must hide the banner, not break the '
            'page it sits on',
        )

    def test_the_hidden_banner_is_named_in_the_log(self):
        """Whoever reads the log can tell which help panel went missing."""
        with self.assertLogs(BANNER_LOG, level='WARNING') as captured:
            self._render_with(ValueError('something unrelated went wrong'))
        self.assertTrue(
            any('hr_rfid_setup' in line for line in captured.output),
            'Hiding the banner without naming it leaves nobody able to find out '
            'why the help disappeared',
        )
