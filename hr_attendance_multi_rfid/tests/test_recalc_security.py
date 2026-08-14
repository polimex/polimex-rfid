# -*- coding: utf-8 -*-
"""Who may rebuild attendance, and whose rebuilds they may see.

Rebuilding deletes a period of somebody's attendance and replays it from the
door events. That is the payroll record of a real person, so the two questions
below are worth answering out loud:

* Who may start one? The people who answer for attendance - the administrator.
  An officer keeps an eye on the day-to-day and may look at what a rebuild
  did, but starting or altering one is not theirs to do.
* Whose may they see? Only their own company's. A holding runs several
  companies out of one system, and the attendance of one company's staff -
  including who rebuilt it and when - is not the business of another's.

Both are stated as what must NOT be possible, because that is the half that
fails silently: rights that are too wide look exactly like rights that are
right until somebody uses them.
"""
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install", "rfid_attendance_recalc",
        "rfid_attendance_multi_company")
class TestWhoMayRebuildAttendance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create(
            {'name': 'Rebuild Rights Co B'})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Rebuild Rights Employee',
            'company_id': cls.company_a.id,
        })
        cls.employee_elsewhere = cls.env['hr.employee'].create({
            'name': 'Rebuild Rights Employee Elsewhere',
            'company_id': cls.company_b.id,
        })
        # Everybody here can also read staff records. That is how the job
        # actually works - a rebuild is started by picking people out of the
        # employee list - and it keeps the refusals below about the rebuild
        # itself rather than about somebody who could not see the list in the
        # first place.
        cls.officer = new_test_user(
            cls.env,
            login='rebuild_rights_officer',
            groups='base.group_user,hr.group_hr_user,'
                   'hr_attendance.group_hr_attendance_officer',
            name='Rebuild Rights Officer',
            company_id=cls.company_a.id,
            company_ids=[Command.set([cls.company_a.id])],
        )
        cls.manager = new_test_user(
            cls.env,
            login='rebuild_rights_manager',
            groups='base.group_user,hr.group_hr_user,'
                   'hr_attendance.group_hr_attendance_manager',
            name='Rebuild Rights Manager',
            company_id=cls.company_a.id,
            company_ids=[Command.set([cls.company_a.id])],
        )
        cls.manager_elsewhere = new_test_user(
            cls.env,
            login='rebuild_rights_manager_b',
            groups='base.group_user,hr.group_hr_user,'
                   'hr_attendance.group_hr_attendance_manager',
            name='Rebuild Rights Manager Elsewhere',
            company_id=cls.company_b.id,
            company_ids=[Command.set([cls.company_b.id])],
        )

    def _a_rebuild(self, company=None):
        company = company or self.company_a
        whose = (self.employee if company == self.company_a
                 else self.employee_elsewhere)
        return self.env['hr.attendance.recalc.run'].create({
            'employee_ids': [Command.set(whose.ids)],
            'date_from': fields.Date.today() - timedelta(days=7),
            'date_to': fields.Date.today(),
            'company_id': company.id,
        })

    def _a_line_of(self, run):
        return self.env['hr.attendance.recalc.log'].create({
            'run_id': run.id,
            'employee_id': run.employee_ids[0].id,
            'status': 'done',
        })

    def _seen_by(self, user, record):
        return record.with_user(user).search([('id', '=', record.id)])

    # ── who may start one ─────────────────────────────────────

    def test_an_officer_may_look_at_what_a_rebuild_did(self):
        """Someone who watches attendance day to day can see why yesterday's
        figures changed - that is the point of keeping the account."""
        run = self._a_rebuild()
        line = self._a_line_of(run)

        self.assertEqual(self._seen_by(self.officer, run), run,
                         "an attendance officer must be able to read a rebuild")
        self.assertEqual(self._seen_by(self.officer, line), line,
                         "and the line saying what happened to each person")

    def test_an_officer_may_not_start_a_rebuild(self):
        """Deleting and replaying somebody's payroll record is not a
        day-to-day job, and the button that does it is not offered to
        somebody who only keeps an eye on attendance."""
        with self.assertRaises(AccessError):
            self.env['hr.attendance.recalc.wizard'].with_user(
                self.officer).create({
                    'employee_ids': [Command.set(self.employee.ids)],
                    'start_date': fields.Date.today() - timedelta(days=7),
                    'end_date': fields.Date.today(),
                })

    def test_an_officer_may_not_ask_for_a_rebuild_by_writing_one_down(self):
        """Nor by going round the button and recording the request itself."""
        with self.assertRaises(AccessError):
            self.env['hr.attendance.recalc.run'].with_user(self.officer).create({
                'employee_ids': [Command.set(self.employee.ids)],
                'date_from': fields.Date.today() - timedelta(days=7),
                'date_to': fields.Date.today(),
            })

    def test_an_officer_may_not_set_a_finished_rebuild_going_again(self):
        """A rebuild that is over stays over. Starting it again replays a
        period that has already been settled and paid."""
        run = self._a_rebuild()
        run.state = 'done'

        with self.assertRaises(AccessError):
            run.with_user(self.officer).action_start()

    def test_an_officer_may_not_rewrite_the_account_of_what_happened(self):
        """The lines are the account of what a rebuild did to whose
        attendance. Somebody who may not run one may not edit that either."""
        line = self._a_line_of(self._a_rebuild())

        with self.assertRaises(AccessError):
            line.with_user(self.officer).write({'status': 'error'})

    def test_an_officer_may_not_erase_a_rebuild(self):
        """Nor make it as though it never happened."""
        run = self._a_rebuild()

        with self.assertRaises(AccessError):
            run.with_user(self.officer).unlink()

    def test_the_attendance_administrator_may_start_one(self):
        """The other half: the person who does answer for attendance must be
        able to do the job. Rights locked down too far are as broken as
        rights left too wide, and they look the same from here."""
        wizard = self.env['hr.attendance.recalc.wizard'].with_user(
            self.manager).create({
                'employee_ids': [Command.set(self.employee.ids)],
                'start_date': fields.Date.today() - timedelta(days=7),
                'end_date': fields.Date.today(),
            })

        shown = wizard.execute()

        run = self.env['hr.attendance.recalc.run'].browse(
            shown['params']['next']['res_id'])
        self.assertEqual(run.state, 'queued',
                         "the administrator's request must be written down")
        self.assertEqual(run.user_id, self.manager,
                         "and recorded as theirs")

    # ── whose they may see ────────────────────────────────────

    def test_a_rebuild_of_another_company_is_not_visible(self):
        """One company's payroll history is not another's business, even
        between people who are administrators in their own."""
        run = self._a_rebuild(self.company_a)
        line = self._a_line_of(run)

        self.assertFalse(
            self._seen_by(self.manager_elsewhere, run),
            "a rebuild started for one company must not be visible to "
            "somebody working in another")
        self.assertFalse(
            self._seen_by(self.manager_elsewhere, line),
            "and neither must the line naming whose attendance it touched - "
            "that is a person's name in another company's payroll")

    def test_a_rebuild_of_my_own_company_is_visible(self):
        """The other half, so that "invisible to everybody" cannot pass as
        company isolation."""
        run = self._a_rebuild(self.company_b)
        line = self._a_line_of(run)

        self.assertEqual(
            self._seen_by(self.manager_elsewhere, run), run,
            "an administrator must see the rebuilds of their own company")
        self.assertEqual(
            self._seen_by(self.manager_elsewhere, line), line,
            "and the lines that belong to them")
