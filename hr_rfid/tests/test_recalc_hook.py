# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""An add-on that refuses to rebuild attendance is always heard.

Attendance can be rebuilt from the door events. Some of it must never be:
records brought over from an older installation are a transcript of what that
installation decided, and rebuilding them destroys both the numbers and the
note of where each row came from - so the next transfer brings the same rows
over a second time.

The add-on holding such records refuses the rebuild. These tests are about the
refusal getting through: whichever add-ons a customer happens to have, and in
whatever order they were installed, an objection raised by one of them reaches
the operator instead of being lost on the way.
"""
from datetime import date, timedelta

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

# Where the refusal point has to live for no add-on to be able to displace it:
# the module every RFID add-on already builds on.
COMMON_ANCESTOR = 'odoo.addons.hr_rfid.models.hr_employee'


@tagged('post_install', '-at_install', 'rfid_recalc_hook')
class TestRecalcRefusalIsHeard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].with_context(
            no_hardware_commands=True,
        ).create({'name': 'Recalculation Test Person'})
        cls.end_date = date.today()
        cls.start_date = cls.end_date - timedelta(days=30)

    def _ask(self, employee=None):
        employee = self.employee if employee is None else employee
        return employee._check_recalc_allowed(self.start_date, self.end_date)

    # ── Nothing installed objects ─────────────────────────────

    def test_nobody_objects_so_the_rebuild_goes_ahead(self):
        """With no add-on protecting anything, asking must simply be allowed."""
        self.assertIsNone(
            self._ask(),
            'An installation where nothing is protected must be able to '
            'rebuild attendance without being refused',
        )

    def test_asking_about_nobody_is_allowed(self):
        """Selecting no one is not an error - there is nothing to protect."""
        self.assertIsNone(self._ask(self.env['hr.employee']))

    # ── An add-on objects ─────────────────────────────────────

    def test_an_objection_reaches_the_operator(self):
        """An add-on that refuses stops the rebuild, whoever loaded last.

        This is what the customer experiences: the refusal, with its reason,
        instead of silently destroyed records.
        """
        refusal = 'These records came from another system and cannot be rebuilt.'
        Employee = self.registry['hr.employee']
        # Whatever is outermost today - i.e. what an add-on installed after
        # every other one would reach through super().
        underneath = Employee._check_recalc_allowed
        reached = []

        def _objecting_add_on(records, start_date, end_date):
            underneath(records, start_date, end_date)
            reached.append((start_date, end_date))
            raise UserError(refusal)

        self.patch(Employee, '_check_recalc_allowed', _objecting_add_on)

        with self.assertRaises(UserError) as caught:
            self._ask()

        self.assertEqual(str(caught.exception), refusal)
        self.assertEqual(
            reached, [(self.start_date, self.end_date)],
            'The objecting add-on must be reached, and told which period is '
            'about to be rebuilt',
        )

    def test_an_add_on_that_allows_does_not_silence_the_one_underneath(self):
        """Two add-ons, and only one of them objects: the refusal still wins.

        This is the failure this fix exists to prevent. When each add-on
        brought its own base, whichever the customer's installation happened
        to load last decided the answer for both - so an add-on that merely
        allows could cancel the one refusing, and the rebuild destroyed the
        protected records with nothing raised and nothing logged.
        """
        Employee = self.registry['hr.employee']
        beneath_everything = Employee._check_recalc_allowed

        def _add_on_that_refuses(records, start_date, end_date):
            beneath_everything(records, start_date, end_date)
            raise UserError('Protected records in this period.')

        self.patch(Employee, '_check_recalc_allowed', _add_on_that_refuses)
        refusing = Employee._check_recalc_allowed

        def _add_on_that_only_allows(records, start_date, end_date):
            refusing(records, start_date, end_date)

        self.patch(Employee, '_check_recalc_allowed', _add_on_that_only_allows)

        with self.assertRaises(UserError):
            self._ask()

    # ── Why it stays heard ────────────────────────────────────

    def test_the_refusal_point_belongs_to_the_shared_module(self):
        """No add-on can take the place of the refusal point and drop it.

        An add-on can only ever be layered on top of the shared module, never
        underneath it, so an objection raised anywhere above always has
        somewhere to hand off to.
        """
        declared_by = [
            cls.__module__
            for cls in self.registry['hr.employee'].mro()
            if '_check_recalc_allowed' in vars(cls)
        ]
        self.assertIn(
            COMMON_ANCESTOR, declared_by,
            'The refusal point must be declared in the module every RFID '
            'add-on builds on; declared anywhere else it can be displaced by '
            'an add-on that allows everything',
        )
        self.assertEqual(
            declared_by[-1], COMMON_ANCESTOR,
            'The shared module must sit underneath every add-on that extends '
            'the refusal point, so no add-on ends up beneath it',
        )
