# -*- coding: utf-8 -*-
"""A forgotten badge-out is settled by the zone that saw the person come in.

Every test states what a real person gets: the HR officer finds no attendance
still hanging open days later; the settled record carries the hours the zone
form promises; and nothing the zone never touched is closed on the zone's
behalf.

The regression these tests guard: the old code asked "which zone is the
employee in NOW" (employee_id.in_zone_ids) instead of "which zone was this
attendance opened in" (in_zone_id). A person who had already left the zone
had nothing there, so their forgotten open attendance could never be closed -
measured on a real customer database as 41 of 44 records stuck open.
"""
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'rfid_attendance_autoclose')
class TestZoneAutoClose(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # The zone form promises: after 12 hours the stay is abandoned, and
        # the person is credited 7 worked hours.
        cls.zone = cls.env['hr.rfid.zone'].create({
            'name': 'Autoclose Zone',
            'company_id': cls.company.id,
            'attendance': True,
            'max_time_in_zone': 12.0,
            'auto_close_time_for_zone': 7.0,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Forgetful Employee',
            'company_id': cls.company.id,
        })

    def _open_attendance(self, hours_ago, zone=None):
        """An attendance session opened some hours ago and never closed."""
        return self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': fields.Datetime.now() - timedelta(hours=hours_ago),
            'in_zone_id': zone.id if zone else False,
        })

    def test_a_person_who_already_left_the_zone_is_still_closed(self):
        """HR finds no attendance hanging open days after the person left.

        The person badged in, walked out without badging, and is long gone -
        the zone does not list them any more. Their attendance still knows
        which zone it was opened in, and that is what settles it: the sweep
        closes it with the 7 hours the zone promises (check-out = check-in +
        Auto-close Worked Hours).
        """
        attendance = self._open_attendance(hours_ago=20, zone=self.zone)
        self.assertNotIn(self.employee, self.zone.employee_ids,
                         "the person is no longer in the zone - exactly the "
                         "situation the old code could not close")

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertTrue(attendance.check_out,
                        "the forgotten attendance must be closed even though "
                        "the person is no longer in the zone")
        self.assertEqual(
            attendance.check_out,
            attendance.check_in + timedelta(hours=7),
            "and it must credit the zone's Auto-close Worked Hours (7h), "
            "not the 12h abandonment limit and not any built-in number")

    def test_a_zone_without_auto_close_hours_settles_at_the_maximum(self):
        """Where the zone promises no worked-hours figure, the limit is used.

        The zone form says: set Auto-close Worked Hours to 0 and the closure
        credits Maximum Hours in Zone instead. A 12-hour zone with no
        auto-close figure settles the record at check-in + 12 hours.
        """
        no_figure_zone = self.env['hr.rfid.zone'].create({
            'name': 'No Figure Zone',
            'company_id': self.company.id,
            'attendance': True,
            'max_time_in_zone': 12.0,
            'auto_close_time_for_zone': 0.0,
        })
        attendance = self._open_attendance(hours_ago=20, zone=no_figure_zone)

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertEqual(
            attendance.check_out,
            attendance.check_in + timedelta(hours=12),
            "with no Auto-close Worked Hours set, the person is credited "
            "the zone's Maximum Hours in Zone")

    def test_a_stay_within_the_limit_is_left_alone(self):
        """A person still legitimately at work is not checked out early.

        Five hours into a 12-hour zone there is nothing to settle: the sweep
        must not touch the open attendance.
        """
        attendance = self._open_attendance(hours_ago=5, zone=self.zone)

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertFalse(attendance.check_out,
                         "an attendance still within the zone's limit must "
                         "stay open - the person may simply still be at work")

    def test_a_record_without_a_zone_is_never_closed_by_the_zone_sweep(self):
        """What the zone never saw is not the zone's to settle.

        An attendance carrying no zone - typed in by HR, or made by a kiosk -
        has no zone limit to be measured against. However old it grows, the
        zone sweep leaves it alone; closing it is a person's decision.
        """
        attendance = self._open_attendance(hours_ago=30, zone=None)

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertFalse(attendance.check_out,
                         "a record without a zone must never be closed by "
                         "the zone auto-close sweep")

    def test_a_zone_with_no_limit_never_closes_anybody(self):
        """A zone that sets no maximum promises no automatic closure.

        The zone form says: set Maximum Hours in Zone to 0 to disable
        automatic closure. Records in such a zone stay open until a person
        or a badge closes them.
        """
        unlimited_zone = self.env['hr.rfid.zone'].create({
            'name': 'Unlimited Zone',
            'company_id': self.company.id,
            'attendance': True,
            'max_time_in_zone': 0.0,
            'auto_close_time_for_zone': 7.0,
        })
        attendance = self._open_attendance(hours_ago=48, zone=unlimited_zone)

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertFalse(attendance.check_out,
                         "a zone with Maximum Hours in Zone = 0 promises no "
                         "automatic closure, however old the record grows")

    def test_walking_into_a_zone_makes_a_record_stamped_as_the_machines(self):
        """What the badge makes is marked as the machine's, from the start.

        An employee walks into an attendance zone: the record that appears is
        stamped as made by the RFID machinery (mode 'rfid'), so a later
        rebuild knows it may take it back and replay it.
        """
        self.zone.person_entered(self.employee, False)

        attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee.id),
            ('check_out', '=', False),
        ])
        self.assertEqual(len(attendance), 1,
                         "walking in must open exactly one attendance")
        self.assertEqual(attendance.in_zone_id, self.zone)
        self.assertEqual(attendance.in_mode, 'rfid',
                         "the record the badge makes is the machine's own")

    def test_a_record_typed_in_by_hand_is_not_stamped_as_the_machines(self):
        """What a person types in stays theirs.

        HR creating an attendance through the form gets the standard manual
        mode - never 'rfid'. This is what keeps their entry safe from any
        rebuild that takes back only the machine's own records.
        """
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': fields.Datetime.now() - timedelta(hours=2),
        })
        self.assertEqual(attendance.in_mode, 'manual',
                         "a hand-made record must keep the standard manual "
                         "mode, or a rebuild could mistake it for the "
                         "machine's and delete it")

    def test_the_zone_sweep_rides_the_core_check_out_task(self):
        """One scheduled task closes forgotten attendance, not one per rule.

        Core already schedules "Automatically check-out employees"; the zone
        sweep runs from that same task. A site that never touches the
        company's Automatic Check-Out setting still gets its zone limits
        enforced - and no second cron exists to fall out of step. The module
        must ship NO cron record of its own any more.
        """
        attendance = self._open_attendance(hours_ago=20, zone=self.zone)

        # The core task's entry point - not our own method - must close it,
        # even with the company's calendar-based auto check-out switched off.
        self.assertFalse(self.env.company.auto_check_out)
        self.env['hr.attendance']._cron_auto_check_out()

        self.assertTrue(attendance.check_out,
                        "the core check-out task must run the zone sweep")
        self.assertFalse(
            self.env.ref(
                'hr_attendance_multi_rfid.hr_attendance_multi_rfid_autoclose_cron',
                raise_if_not_found=False),
            "the module's own cron record must be gone - one task, not two")


@tagged('post_install', '-at_install', 'rfid_attendance_autoclose')
class TestAStayNobodyCouldHaveHad(TransactionCase):
    """Crossing midnight is work. Staying for a week is a missed badge-out.

    The theatre's people are on shift at midnight, so a night that runs to
    01:00 must be left exactly as it is. But the same database holds records
    running for months - 1906 of them past 24 hours, the longest 361 days -
    because somebody forgot to badge out and the record was closed much later.
    Those are not stays, and while they stand they lend their whole length to
    every day they touch.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Settle Calendar', 'company_id': cls.company.id,
            'tz': 'UTC', 'hours_per_day': 8.0})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Night Worker', 'company_id': cls.company.id,
            'resource_calendar_id': cls.calendar.id})

    def _stay(self, start, hours):
        return self.env['hr.attendance'].with_context(
            no_validity_check=True).create({
                'employee_id': self.employee.id,
                'check_in': start,
                'check_out': start + timedelta(hours=hours),
            })

    def test_a_night_shift_is_left_alone(self):
        """NEGATIVE: 22:00 to 06:00 crosses midnight and is ordinary work.

        Nothing about it may be settled, moved or shortened.
        """
        start = fields.Datetime.now().replace(
            hour=22, minute=0, second=0, microsecond=0) - timedelta(days=2)
        night = self._stay(start, 8)

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertEqual(night.check_out, start + timedelta(hours=8),
                         "a shift across midnight is work, not a fault")
        self.assertFalse(night.out_mode == 'auto_check_out',
                         "and it is nobody's administrative closure")

    def test_a_stay_of_months_is_settled_at_the_schedule(self):
        """The record closed long after the person left is put right.

        No zone on it - everything brought over from an older system is like
        that - so the day they were supposed to work is what they are
        credited: eight hours, from their own working schedule.
        """
        start = fields.Datetime.now() - timedelta(days=300)
        forgotten = self._stay(start, 300 * 24)
        was = forgotten.check_out

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertEqual(forgotten.check_out, start + timedelta(hours=8),
                         "credited the working day, not the 300 days it stood")
        self.assertEqual(forgotten.out_mode, 'auto_check_out',
                         "and it reads as settled by the system, not by a person")
        note = forgotten.message_ids[:1].body or ''
        self.assertIn(str(was.year), note,
                      "the chatter must keep what the record used to say - a "
                      "number nobody can explain is worse than one somebody "
                      "changed on purpose")

    def test_a_settled_stay_is_not_settled_again(self):
        """NEGATIVE: running the sweep twice changes nothing the second time.

        It runs on a scheduled task, so it will pass over these records again
        and again for as long as the installation lives.
        """
        start = fields.Datetime.now() - timedelta(days=40)
        forgotten = self._stay(start, 40 * 24)
        self.env['hr.attendance'].check_for_incomplete_attendances()
        settled = forgotten.check_out
        notes = len(forgotten.message_ids)

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertEqual(forgotten.check_out, settled)
        self.assertEqual(len(forgotten.message_ids), notes,
                         "and it does not write a second note about it")

    def test_a_stay_just_over_a_day_is_found_too(self):
        """The one the search used to walk past.

        A person badges in at 11:14 and the next day's badge closes the record
        at 11:56 - a day and three quarters of an hour. Odoo's Worked Hours
        takes the unpaid break off and reports 23.7, so a search on THAT field
        called it a normal day and left it standing. Measured on a customer
        database: 1827 such records, of which that search found nothing.
        """
        start = fields.Datetime.now().replace(
            hour=11, minute=14, second=0, microsecond=0) - timedelta(days=10)
        forgotten = self._stay(start, 24.7)
        self.assertLess(forgotten.worked_hours, 24,
                        "the premise: paid hours read under a day")

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertEqual(forgotten.check_out, start + timedelta(hours=8),
                         "and it is settled all the same, because the RECORD "
                         "spans more than a day")

    def test_a_stay_that_cannot_be_judged_is_left_for_a_person(self):
        """NEGATIVE: with no zone limit and no working schedule, hands off.

        Guessing a duration here would put a made-up number into somebody's
        hours. The record stays as it is and the log says why.
        """
        nobody = self.env['hr.employee'].create({
            'name': 'No Schedule Worker', 'company_id': self.company.id,
            'resource_calendar_id': False})
        start = fields.Datetime.now() - timedelta(days=100)
        record = self.env['hr.attendance'].with_context(
            no_validity_check=True).create({
                'employee_id': nobody.id, 'check_in': start,
                'check_out': start + timedelta(days=100)})

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertEqual(record.check_out, start + timedelta(days=100),
                         "nothing may be invented for a record nobody can judge")
