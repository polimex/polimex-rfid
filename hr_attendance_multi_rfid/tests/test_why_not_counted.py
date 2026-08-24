# -*- coding: utf-8 -*-
"""A passage that changes no attendance has to say why.

Three customers wrote in with the same complaint, in their own words: people
walk through the door, the event list says "No Info", and nobody can tell
whether that is normal or whether something is set up wrong. Measured on one of
those installations: of 1420 granted entries with no attendance behind them,
1417 happened while the person already had an open record - ordinary, harmless,
and completely invisible as such.

So every decision NOT to touch attendance now leaves the reason on the passage,
in words the operator reads. And the two machines that make attendance - the
live one that runs as people walk through, and the rebuild that replays the
same doors afterwards - must give the same answer about the same passage.
"""
from datetime import timedelta

from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'rfid_attendance_reason')
class TestWhyAPassageWasNotCounted(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # One door with an entry and an exit reader, in a zone that counts
        # towards attendance. Same shape as test_recalc_background.
        cls.webstack = cls.env['hr.rfid.webstack'].create({
            'name': 'Reason WS', 'serial': '884501', 'key': '1234',
            'hw_version': '100.1', 'version': '1.44', 'active': True,
            'tz': 'Europe/Sofia', 'company_id': cls.company.id})
        cls.ctrl = cls.env['hr.rfid.ctrl'].create({
            'name': 'Reason CTRL', 'ctrl_id': 11, 'serial_number': '8845',
            'webstack_id': cls.webstack.id, 'hw_version': '9', 'sw_version': '740',
            'max_cards_count': 100, 'max_events_count': 100, 'readers': 2,
            'mode': 2, 'inputs': 0, 'outputs': 0, 'input_states': 0,
            'output_states': 0, 'alarm_lines': 0, 'io_table_lines': 0,
            'io_table': ''})
        card_type = cls.env.ref('hr_rfid.hr_rfid_card_type_def')
        cls.door = cls.env['hr.rfid.door'].with_context(
            no_hardware_commands=True).create({
                'name': 'Reason Door', 'number': 1,
                'controller_id': cls.ctrl.id, 'card_type': card_type.id})
        cls.reader_in = cls.env['hr.rfid.reader'].with_context(
            no_hardware_commands=True).create({
                'name': 'Reason Reader In', 'number': 1, 'reader_type': '0',
                'controller_id': cls.ctrl.id,
                'door_ids': [Command.link(cls.door.id)]})
        cls.reader_out = cls.env['hr.rfid.reader'].with_context(
            no_hardware_commands=True).create({
                'name': 'Reason Reader Out', 'number': 2, 'reader_type': '1',
                'controller_id': cls.ctrl.id,
                'door_ids': [Command.link(cls.door.id)]})
        # The customer's setting exactly: the zone counts attendance and keeps
        # the first entry of the day (it does not move the check-in when
        # somebody badges again).
        cls.zone = cls.env['hr.rfid.zone'].create({
            'name': 'Reason Zone', 'company_id': cls.company.id,
            'attendance': True,
            'overwrite_check_in': False,
            'overwrite_check_out': False,
            'door_ids': [Command.link(cls.door.id)]})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Reason Employee', 'company_id': cls.company.id})

        cls.yesterday = fields.Datetime.now() - timedelta(days=1)
        cls.morning = cls.yesterday.replace(hour=6, minute=0, second=0,
                                            microsecond=0)
        cls.period_start = fields.Date.to_date(cls.yesterday) - timedelta(days=1)
        cls.period_end = fields.Date.today()

    # ── helpers ───────────────────────────────────────────────

    def _passage(self, reader, moment, employee=None):
        """Somebody walks through the door and is let in."""
        return self.env['hr.rfid.event.user'].create({
            'employee_id': (employee or self.employee).id,
            'door_id': self.door.id,
            'reader_id': reader.id,
            'event_time': moment,
            'event_action': '1',  # granted
        })

    def _attendance_of(self, employee=None):
        return self.env['hr.attendance'].search([
            ('employee_id', '=', (employee or self.employee).id)])

    def _rebuild(self, employee=None):
        (employee or self.employee).recalc_attendance(
            self.period_start, self.period_end)

    # ── the live machinery ────────────────────────────────────

    def test_a_second_badge_while_already_inside_says_so(self):
        """The complaint, in one test.

        The person is already checked in and badges at the entry again - going
        out for a smoke, letting a colleague through, whatever people do. The
        attendance rightly does not move. What was wrong is that the passage
        then stood in the list as an unexplained blank; it now says the person
        was already inside.
        """
        self._passage(self.reader_in, self.morning)
        second = self._passage(self.reader_in, self.morning + timedelta(hours=1))

        self.assertEqual(len(self._attendance_of()), 1,
                         "the second entry must not open a second attendance")
        self.assertEqual(self._attendance_of().check_in, self.morning,
                         "and it must not move the check-in either - this zone "
                         "keeps the first entry of the day")
        self.assertEqual(second.no_attendance_reason, 'already_inside',
                         "the passage must say why it counted for nothing")

    def test_an_exit_with_nothing_open_says_so(self):
        """Somebody badges out of a stay the system never saw begin.

        Their entry was lost - a card not read, a reader offline, a period
        rebuilt without it. The exit cannot close anything and this zone does
        not reopen the previous stay, so nothing happens; the operator must
        still be able to see that this is what happened.
        """
        leaving = self._passage(self.reader_out, self.morning + timedelta(hours=8))

        self.assertFalse(self._attendance_of(),
                         "an exit alone cannot make an attendance")
        self.assertEqual(leaving.no_attendance_reason, 'nothing_to_close')

    def test_a_zone_that_does_not_follow_this_person_says_so(self):
        """The zone follows one department; this person is in another.

        Sales walking through the workshop door is not the workshop's
        attendance. The passage is not counted - and now it says which of the
        two settings on the zone form decided that.
        """
        workshop = self.env['hr.department'].create({
            'name': 'Reason Workshop', 'company_id': self.company.id})
        self.zone.permitted_department_ids = [Command.set(workshop.ids)]
        outsider = self.env['hr.employee'].create({
            'name': 'Reason Outsider', 'company_id': self.company.id})

        arriving = self._passage(self.reader_in, self.morning, employee=outsider)

        self.assertFalse(self._attendance_of(outsider),
                         "a zone limited to a department must not open "
                         "attendance for somebody outside it")
        self.assertEqual(arriving.no_attendance_reason, 'not_tracked_here')

    def test_a_passage_that_counts_carries_no_reason(self):
        """The negative half: the column must stay empty when it should.

        A reason on a passage that DID make attendance would turn the new
        column into noise the operator learns to ignore - which is exactly
        what the blank "No Info" already was.
        """
        arriving = self._passage(self.reader_in, self.morning)
        leaving = self._passage(self.reader_out, self.morning + timedelta(hours=8))

        self.assertEqual(arriving.in_or_out, 'in')
        self.assertFalse(arriving.no_attendance_reason,
                         "an entry that opened attendance has nothing to explain")
        self.assertEqual(leaving.in_or_out, 'out')
        self.assertFalse(leaving.no_attendance_reason,
                         "nor has the exit that closed it")

    def test_a_door_in_two_zones_keeps_the_zone_that_counted(self):
        """One door, two zones: the workshop zone follows only the workshop,
        the building zone follows everybody. A sales visitor walking through
        is counted by the building - and the workshop's refusal must not
        take that away, whichever of the two is answered first.
        """
        workshop = self.env['hr.department'].create({
            'name': 'Reason Workshop 3', 'company_id': self.company.id})
        self.zone.permitted_department_ids = [Command.set(workshop.ids)]
        building = self.env['hr.rfid.zone'].create({
            'name': 'Reason Building Zone', 'company_id': self.company.id,
            'attendance': True,
            'door_ids': [Command.link(self.door.id)]})
        self.assertIn(building, self.door.zone_ids)

        arriving = self._passage(self.reader_in, self.morning)
        self._passage(self.reader_out, self.morning + timedelta(hours=8))

        self.assertEqual(len(self._attendance_of()), 1,
                         "the zone that does follow this person counted it")
        self.assertEqual(arriving.in_or_out, 'in')
        self.assertFalse(
            arriving.no_attendance_reason,
            "the other zone's refusal must not overwrite a counted passage")

        # And the same day survives a rebuild. Asking both zones at once for
        # one setting raised "Expected singleton", which the background worker
        # reported as "Something went wrong" for EVERY person in the rebuild -
        # one shared door was enough to lose the whole job.
        self._rebuild()

        attendance = self._attendance_of()
        self.assertEqual(len(attendance), 1,
                         "the day is rebuilt once, not once per zone")
        self.assertEqual((attendance.check_in, attendance.check_out),
                         (self.morning, self.morning + timedelta(hours=8)))

    # ── the rebuild ───────────────────────────────────────────

    def test_the_rebuild_does_not_hand_out_attendance_the_door_never_gave(self):
        """The two machines must tell the same story about the same day.

        A zone limited to one department ignores everybody else as they walk
        through. The rebuild replayed the very same passages without ever
        asking that question, so pressing Recalculate CREATED the attendance
        the door had refused to create - the same day meant one thing on
        Monday and another after a rebuild on Tuesday.
        """
        workshop = self.env['hr.department'].create({
            'name': 'Reason Workshop 2', 'company_id': self.company.id})
        outsider = self.env['hr.employee'].create({
            'name': 'Reason Outsider 2', 'company_id': self.company.id})
        # The passages happen while the zone still follows everybody, so the
        # attendance below is the one the machine really made. Restricting
        # afterwards is what a real installation does - and it means the
        # assertions measure the REBUILD, not the live pass that came first.
        arriving = self._passage(self.reader_in, self.morning, employee=outsider)
        leaving = self._passage(self.reader_out, self.morning + timedelta(hours=8),
                                employee=outsider)
        self.assertTrue(self._attendance_of(outsider),
                        "the premise: the day was counted before the zone "
                        "was narrowed")
        self.zone.permitted_department_ids = [Command.set(workshop.ids)]

        self._rebuild(outsider)

        self.assertFalse(
            self._attendance_of(outsider),
            "a zone that no longer follows this person must not keep giving "
            "them attendance - and the rebuild is how that correction lands")
        self.assertEqual(arriving.no_attendance_reason, 'not_tracked_here')
        self.assertEqual(leaving.no_attendance_reason, 'not_tracked_here')

    def test_the_rebuild_still_gives_the_permitted_person_their_day(self):
        """The other half, and the one that matters most.

        Narrowing a zone to a department must take attendance away from
        nobody who IS in it. Without this, a rebuild that refused everybody
        would make every other test in this file greener, not redder.
        """
        workshop = self.env['hr.department'].create({
            'name': 'Reason Workshop 4', 'company_id': self.company.id})
        insider = self.env['hr.employee'].create({
            'name': 'Reason Insider', 'company_id': self.company.id,
            'department_id': workshop.id})
        self.zone.permitted_department_ids = [Command.set(workshop.ids)]
        arriving = self._passage(self.reader_in, self.morning, employee=insider)
        self._passage(self.reader_out, self.morning + timedelta(hours=8),
                      employee=insider)

        self._rebuild(insider)

        attendance = self._attendance_of(insider)
        self.assertEqual(len(attendance), 1,
                         "the workshop's own person keeps their workshop day")
        self.assertEqual((attendance.check_in, attendance.check_out),
                         (self.morning, self.morning + timedelta(hours=8)))
        self.assertFalse(arriving.no_attendance_reason,
                         "and their passages carry nothing to explain")

    def test_a_second_entry_replaces_the_first_where_the_zone_says_so(self):
        """A zone set to keep the LATER entry does exactly that.

        The morning badge stops standing for anything once the person badges
        again, so it says it was replaced - otherwise the list shows two
        check-ins for one attendance and neither of them says which is which.
        """
        self.zone.overwrite_check_in = True
        first = self._passage(self.reader_in, self.morning)
        second = self._passage(self.reader_in, self.morning + timedelta(hours=1))
        self._passage(self.reader_out, self.morning + timedelta(hours=8))

        self._rebuild()

        attendance = self._attendance_of()
        self.assertEqual(len(attendance), 1)
        self.assertEqual(attendance.check_in, self.morning + timedelta(hours=1),
                         "the zone keeps the later entry")
        self.assertEqual(first.no_attendance_reason, 'superseded')
        self.assertEqual(second.in_or_out, 'in')
        self.assertFalse(second.no_attendance_reason)

    def test_a_zone_that_keeps_the_later_entry_does_not_invent_one(self):
        """Same zone, live this time, and nothing to move.

        The person is already inside and there is no later record saying they
        started too early, so the check-in stays where it is. The passage must
        say the person was already inside rather than report a check-in that
        never happened - measured before this: the event read "Check In" while
        the attendance had not moved a second.
        """
        self.zone.overwrite_check_in = True
        self._passage(self.reader_in, self.morning)
        again = self._passage(self.reader_in, self.morning + timedelta(hours=1))

        attendance = self._attendance_of()
        self.assertEqual(len(attendance), 1)
        self.assertEqual(attendance.check_in, self.morning,
                         "nothing moved the check-in")
        self.assertEqual(again.no_attendance_reason, 'already_inside')
        self.assertNotEqual(again.in_or_out, 'in',
                            "a passage that moved nothing must not read as a "
                            "check-in")

    def test_a_day_the_operator_wrote_down_by_hand_says_so(self):
        """The operator's word stands, and the passages under it say why.

        Somebody forgot to badge, the operator typed the day in. The rebuild
        leaves that record alone - it always did - but the door events falling
        inside it used to end up as blanks, indistinguishable from a fault.
        """
        arriving = self._passage(self.reader_in, self.morning)
        leaving = self._passage(self.reader_out, self.morning + timedelta(hours=8))
        # The operator judges the machine's version of the day wrong, throws
        # it away and types in the hours themselves - the ordinary correction.
        self._attendance_of().unlink()
        by_hand = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': self.morning - timedelta(hours=1),
            'check_out': self.morning + timedelta(hours=10),
        })

        self._rebuild()

        self.assertTrue(by_hand.exists(), "what a person typed in is never replayed away")
        self.assertEqual(self._attendance_of(), by_hand,
                         "and no machine record may be built beside it")
        self.assertEqual(arriving.no_attendance_reason, 'manual_record')
        self.assertEqual(leaving.no_attendance_reason, 'manual_record')

    def test_the_reason_goes_when_the_passage_starts_to_count(self):
        """A stale reason next to a real check-out would be worse than a blank.

        These controllers deliver events out of order: the exit can arrive
        before the entry it belongs to. Live, that exit closed nothing and said
        so. Once the entry turns up and the day is rebuilt, the same passage IS
        the check-out - and must stop claiming otherwise.
        """
        leaving = self._passage(self.reader_out, self.morning + timedelta(hours=8))
        self.assertEqual(leaving.no_attendance_reason, 'nothing_to_close',
                         "the premise: on its own the exit explained itself")

        self._passage(self.reader_in, self.morning)
        self._rebuild()

        self.assertEqual(leaving.in_or_out, 'out')
        self.assertFalse(leaving.no_attendance_reason,
                         "the passage now closes a real attendance, so the old "
                         "explanation must be gone")
        attendance = self._attendance_of()
        self.assertEqual(len(attendance), 1)
        self.assertEqual((attendance.check_in, attendance.check_out),
                         (self.morning, self.morning + timedelta(hours=8)))
