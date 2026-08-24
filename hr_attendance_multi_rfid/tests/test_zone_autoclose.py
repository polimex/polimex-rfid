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
        # One setting, in one place: a stay is settled once it runs four hours
        # past the person's schedule, and they are credited the day that
        # schedule says - seven hours here.
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Autoclose Calendar 7h', 'company_id': cls.company.id,
            'tz': 'UTC', 'hours_per_day': 7.0,
            'attendance_ids': [(0, 0, {
                'name': '%s' % day, 'dayofweek': day,
                'hour_from': 8.0, 'hour_to': 15.0, 'day_period': 'morning'})
                for day in ('0', '1', '2', '3', '4', '5', '6')],
        })
        cls.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 4.0,
            'forgotten_badge_policy': 'credit_schedule',
        })
        cls.zone = cls.env['hr.rfid.zone'].create({
            'name': 'Autoclose Zone',
            'company_id': cls.company.id,
            'attendance': True,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Forgetful Employee',
            'company_id': cls.company.id,
            'resource_calendar_id': cls.calendar.id,
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
        the zone does not list them any more. The sweep settles the record all
        the same, crediting the seven hours their own schedule says for that
        day. Where they happen to be now was never the question; the old code
        asked it and could not close anybody who had walked away.
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
            "and it must credit the scheduled day (7h), not the twelve hours "
            "the stay was allowed to run and not any built-in number")

    def test_the_company_can_take_hours_off_for_forgetting(self):
        """Some companies treat a forgotten badge as time off site.

        The setting says so out loud: credit the scheduled day, less a
        penalty. Seven scheduled hours, two off, and the person is credited
        five - they were here, but nobody can say until when.
        """
        self.company.write({'forgotten_badge_policy': 'penalty',
                            'forgotten_badge_penalty_hours': 2.0})
        attendance = self._open_attendance(hours_ago=20, zone=self.zone)

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertEqual(
            attendance.check_out,
            attendance.check_in + timedelta(hours=5),
            "seven scheduled hours less the two-hour penalty")

    def test_the_company_can_count_nothing_at_all(self):
        """Others want the person to come and explain.

        Nothing is credited and the times are left exactly as they are: the
        stay is only MARKED as a forgotten badge, so it can be found, and the
        real hours have to be entered by hand.
        """
        self.company.write({'forgotten_badge_policy': 'ignore'})
        attendance = self._open_attendance(hours_ago=20, zone=self.zone)

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertFalse(attendance.check_out,
                         "nothing was credited, so nothing was closed")
        self.assertTrue(attendance.forgotten_badge,
                        "but it is marked, or nobody would ever find it")

    def test_a_stay_within_the_limit_is_left_alone(self):
        """A person still legitimately at work is not checked out early.

        Five hours into a seven-hour day with four hours of tolerance there
        is nothing to settle: the sweep must not touch the open attendance.
        """
        attendance = self._open_attendance(hours_ago=5, zone=self.zone)

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertFalse(attendance.check_out,
                         "an attendance still within the zone's limit must "
                         "stay open - the person may simply still be at work")

    def test_a_record_without_a_zone_is_settled_the_same_way(self):
        """The zone was never the question - the person's schedule is.

        An attendance carrying no zone at all (typed in, made by a kiosk, or
        brought over from an older system) is judged exactly like any other:
        the schedule says seven hours, the tolerance four, and a stay of
        thirty hours is a badge-out that never happened. The old code let
        these grow forever, and a customer database ended up with 1827 of
        them, the longest 361 days.
        """
        attendance = self._open_attendance(hours_ago=30, zone=None)

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertEqual(attendance.check_out,
                         attendance.check_in + timedelta(hours=7),
                         "settled on the person's own schedule, zone or no zone")

    def test_switching_the_setting_off_closes_nobody(self):
        """NEGATIVE: with Automatic Check-Out off, nothing is ever settled.

        The company has not asked for it, so no record is touched however old
        it grows - and nothing here invents a limit of its own.
        """
        self.company.auto_check_out = False
        attendance = self._open_attendance(hours_ago=48, zone=self.zone)

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertFalse(attendance.check_out,
                         "Automatic Check-Out is off: nothing may be settled")
        self.assertFalse(attendance.forgotten_badge)

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

    def test_one_scheduled_task_settles_forgotten_stays(self):
        """One task closes forgotten attendance, not one per rule.

        Core already schedules "Automatically check-out employees" and our
        sweep runs from that same task - it covers what core leaves behind,
        the records closed long after the person left. One clock, one setting,
        and no second cron to fall out of step with the first.
        """
        attendance = self._open_attendance(hours_ago=20, zone=self.zone)

        # The core task's entry point, not our own method.
        self.env['hr.attendance']._cron_auto_check_out()

        self.assertTrue(attendance.check_out,
                        "the core check-out task must settle it")
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
            'tz': 'UTC', 'hours_per_day': 8.0,
            # With a real unpaid break, so the tests can show that Worked
            # Hours reads UNDER the span of the record - which is why the
            # search is on the two timestamps and not on that field.
            'attendance_ids': [(0, 0, {
                'name': '%s %s' % (day, period), 'dayofweek': day,
                'hour_from': start, 'hour_to': stop, 'day_period': period})
                for day in ('0', '1', '2', '3', '4', '5', '6')
                for period, start, stop in (('morning', 8.0, 12.0),
                                            ('lunch', 12.0, 13.0),
                                            ('afternoon', 13.0, 17.0))]})
        # Eight scheduled hours and two of tolerance: a stay is settled once
        # it runs past ten, and is credited the eight the schedule says.
        cls.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 2.0,
            'forgotten_badge_policy': 'credit_schedule'})
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

        self.assertEqual(forgotten.check_out, start + timedelta(hours=9),
                         "credited the working day - eight hours of work and "
                         "the unpaid break between them - not the 300 days "
                         "it stood")
        self.assertEqual(forgotten.out_mode, 'auto_check_out',
                         "and it reads as settled by the system, not by a person")
        # Every message on the record, not just the newest: the write itself
        # also posts a tracking line, and which of the two lands last is not
        # ours to depend on.
        note = ' '.join(forgotten.message_ids.mapped('body'))
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

        self.assertEqual(forgotten.check_out, start + timedelta(hours=9),
                         "and it is settled all the same, because the RECORD "
                         "spans more than the schedule allows - credited the "
                         "working day, break included, as any other day is")

    def test_a_stay_that_cannot_be_judged_is_left_for_a_person(self):
        """NEGATIVE: with no working schedule for the day, hands off.

        There is nothing to measure the stay against and nothing to credit;
        guessing would put a made-up number into somebody's hours. The record
        stays as it is and the log says why.
        """
        empty = self.env['resource.calendar'].create({
            'name': 'Nothing Scheduled', 'company_id': self.company.id,
            'tz': 'UTC', 'hours_per_day': 0.0, 'attendance_ids': []})
        nobody = self.env['hr.employee'].create({
            'name': 'No Schedule Worker', 'company_id': self.company.id,
            'resource_calendar_id': empty.id})
        start = fields.Datetime.now() - timedelta(days=100)
        record = self.env['hr.attendance'].with_context(
            no_validity_check=True).create({
                'employee_id': nobody.id, 'check_in': start,
                'check_out': start + timedelta(days=100)})

        self.env['hr.attendance'].check_for_incomplete_attendances()

        self.assertEqual(record.check_out, start + timedelta(days=100),
                         "nothing may be invented for a record nobody can judge")
