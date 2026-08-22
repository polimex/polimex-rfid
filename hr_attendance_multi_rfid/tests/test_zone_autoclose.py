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
