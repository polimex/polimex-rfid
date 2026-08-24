# -*- coding: utf-8 -*-
"""The app has one menu of each kind, in the order people read them.

Several modules add menus to the Attendances app. Left uncoordinated they
pile up: this module used to add a SECOND top-level "Reports" right next to
the built-in Reporting, and the rebuild log sat as a sixth top-level menu
between them. The operator then has to learn which of two reporting menus
holds what - a question the product should never ask.

The rules asserted here: our reports live UNDER the app's own Reporting menu,
our manager-only tools live under Configuration, and everything carries an
explicit sequence so the next module to arrive lands in a defined place
rather than in the middle.
"""
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'rfid_attendance_menus')
class TestTheAttendanceMenusAreInOrder(TransactionCase):

    def _menu(self, xmlid):
        return self.env.ref(xmlid, raise_if_not_found=False)

    def test_our_reports_sit_under_the_apps_reporting_menu(self):
        """Somebody looking for a report opens Reporting and finds all of
        them there - ours included."""
        reporting = self.env.ref('hr_attendance.menu_hr_attendance_reporting')
        for xmlid in ('hr_attendance_late.menu_hr_attendance_extra',
                      'hr_attendance_late.menu_hr_attendance_self_leave',
                      # From another module in this family. It hung off the
                      # duplicate Reports menu, so removing that menu broke
                      # its INSTALL outright ("External ID not found") on any
                      # database that has it - found by running the suite on a
                      # database where it was installed, not by reading the
                      # module being edited. A menu id another module names is
                      # a promise; asserting the whole family here is what
                      # keeps the promise visible from the place that moves it.
                      'l10n_bg_hr_form_76.menu_wizard_generate_form76_attendance'):
            menu = self._menu(xmlid)
            if not menu:
                continue  # that module is not installed here
            self.assertEqual(
                menu.parent_id, reporting,
                "%s must sit under the app's own Reporting menu, not beside "
                "it - two reporting menus is a question, not a feature"
                % xmlid)

    def test_there_is_only_one_reporting_menu_in_the_app(self):
        """NEGATIVE: the duplicate top-level Reports menu is gone for good."""
        root = self.env.ref('hr_attendance.menu_hr_attendance_root')
        top_level = self.env['ir.ui.menu'].with_context(
            active_test=False).search([('parent_id', '=', root.id)])
        # Counted, not name-matched: the menu names are translated, and on a
        # Bulgarian installation - which is every customer we have - a filter
        # looking for the word "report" matches nothing and passes without
        # asserting anything at all. Core gives the app five top-level menus
        # (odoo/addons/hr_attendance/views/hr_attendance_menus.xml); a sixth is
        # somebody adding one beside them instead of inside them.
        ours = top_level.filtered(
            lambda m: not m.get_external_id().get(m.id, '').startswith(
                'hr_attendance.'))
        self.assertFalse(
            ours,
            "a top-level menu was added beside the app's own instead of under "
            "one of them: %s" % ours.mapped('complete_name'))
        self.assertFalse(
            self._menu('hr_attendance_late.menu_hr_attendance_report'),
            "the old duplicate Reports menu record must be gone")

    def test_manager_tools_sit_under_configuration(self):
        """The rebuild log and the legal rates are things a manager sets up
        or looks back at - they belong together, not among the daily menus."""
        configuration = self.env.ref(
            'hr_attendance.menu_hr_attendance_configuration')
        for xmlid in ('hr_attendance_multi_rfid.hr_attendance_recalc_run_menu',
                      'hr_attendance_late.menu_hr_legal_rate'):
            menu = self._menu(xmlid)
            if not menu:
                continue
            self.assertEqual(
                menu.parent_id, configuration,
                "%s must live under Configuration with the other "
                "manager-only tools" % xmlid)

    def test_every_menu_we_add_declares_where_it_goes(self):
        """NEGATIVE: a menu without a sequence takes the default and lands in
        the middle of somebody else's list."""
        ours = [
            'hr_attendance_late.menu_hr_attendance_extra',
            'hr_attendance_late.menu_hr_attendance_self_leave',
            'hr_attendance_late.menu_hr_legal_rate',
            'hr_attendance_multi_rfid.hr_attendance_recalc_run_menu',
            'l10n_bg_hr_form_76.menu_wizard_generate_form76_attendance',
        ]
        for xmlid in ours:
            menu = self._menu(xmlid)
            if not menu:
                continue
            self.assertTrue(
                menu.sequence and menu.sequence != 10,
                "%s carries no deliberate sequence (%s) - it will land "
                "wherever the default puts it" % (xmlid, menu.sequence))

    def test_the_reports_keep_the_order_they_are_read_in(self):
        """Daily figures first, the exception report after it."""
        daily = self._menu('hr_attendance_late.menu_hr_attendance_extra')
        early = self._menu('hr_attendance_late.menu_hr_attendance_self_leave')
        core_first = self.env.ref(
            'hr_attendance.menu_hr_attendance_attendance_reporting')
        self.assertLess(core_first.sequence, daily.sequence,
                        "the app's own report stays first")
        self.assertLess(daily.sequence, early.sequence)
