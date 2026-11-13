"""A rebuild that starts while somebody is inside counts them in once.

The complaint behind this: an attendance rebuild started on the 2nd of a month
reported two people as "Not rebuilt". Both had been inside since the 1st: their
stay began before the rebuild's first day and ended on it. The rebuild kept
that stay, because it began before the period, and then replayed the passages
it already accounts for - an entry while they were inside and the exit that
ended it - into a second record over the first. The day held two overlapping
records, and the overtime calculation gave up on the person.

The operator who rebuilds from a given day expects the days before it to stay
as the doors told them, and the days from it on to come back the same way.
"""

from datetime import timedelta

from odoo import fields
from odoo.tests.common import tagged

from .test_a_new_entry_after_a_forgotten_badge import ForgottenBadgeCase


@tagged("post_install", "-at_install", "rfid_attendance_zone")
class TestARebuildThatStartsInsideAStay(ForgottenBadgeCase):
    def _rebuild_from_tuesday(self):
        self.employee.recalc_attendance(
            fields.Date.to_date(self.tuesday),
            fields.Date.to_date(self.wednesday) + timedelta(days=1),
        )

    def _verdicts(self):
        passages = self.env["hr.rfid.event.user"].search(
            [("employee_id", "=", self.employee.id)], order="event_time"
        )
        return [(p.in_or_out, p.no_attendance_reason) for p in passages]

    def test_a_night_that_ends_on_the_first_morning_is_counted_once(self):
        """The night worker's Monday night stays one night after a rebuild from Tuesday.

        They came in on Monday evening, badged in again at half past five
        while still inside, and left ten minutes later. A rebuild from
        Tuesday leaves that night as the doors told it - one record, the
        second entry "Already inside", the exit the end of the night - and
        gives Tuesday's day back.
        """
        self._in(self.at(self.monday, 20))
        self._in(self.at(self.tuesday, 5.5))
        self._out(self.at(self.tuesday, 5 + 40 / 60))
        self._in(self.at(self.tuesday, 8))
        self._out(self.at(self.tuesday, 16))
        live = self._story()
        live_verdicts = self._verdicts()
        self.assertEqual(
            live,
            [
                (self.at(self.monday, 20), self.at(self.tuesday, 5 + 40 / 60), False),
                (self.at(self.tuesday, 8), self.at(self.tuesday, 16), False),
            ],
        )

        self._rebuild_from_tuesday()

        self.assertEqual(self._story(), live)
        self.assertEqual(self._verdicts(), live_verdicts)

    def test_an_exit_an_earlier_rebuild_wrote_off_reads_true_again(self):
        """The night's exit says it ended the night, after an earlier rebuild said otherwise.

        A rebuild from Tuesday that ran before this was put right wrote the
        night's own exit off as "Nothing open to close" and the entry inside
        the night as a check-in. The next rebuild gives both passages back
        the reading the doors gave them.
        """
        self._in(self.at(self.monday, 20))
        entry_inside = self._in(self.at(self.tuesday, 5.5))
        night_exit = self._out(self.at(self.tuesday, 5 + 40 / 60))
        live_verdicts = self._verdicts()
        night_exit._rewrite_no_attendance("nothing_to_close")
        entry_inside._mark_attendance("in")

        self._rebuild_from_tuesday()

        self.assertEqual(self._verdicts(), live_verdicts)
        self.assertEqual(night_exit.in_or_out, "out")

    def test_somebody_still_inside_when_the_rebuild_starts_is_settled_as_the_doors_did(
        self,
    ):
        """A stay left open before the first day is settled at the next entry.

        The worker forgot to badge out on Monday. The doors settle Monday at
        Tuesday's entry and begin Tuesday's day. An older machinery left
        Monday open instead; a rebuild from Tuesday must end up where the
        doors do, not leave Monday open under every day that follows.
        """
        self._in(self.at(self.monday, 8))
        self._in(self.at(self.tuesday, 8))
        self._out(self.at(self.tuesday, 17))
        live = self._story()
        self.assertEqual(len(live), 2)
        self.assertTrue(live[0][2], "Monday is the forgotten badge-out")

        self._stays().unlink()
        self._machine_stay(self.at(self.monday, 8), zone=self.zone)

        self._rebuild_from_tuesday()

        self.assertEqual(self._story(), live)

    def test_a_stay_that_ended_before_the_first_day_is_not_touched(self):
        """NEGATIVE: a rebuild from Tuesday changes nothing about Monday.

        The record of a day the operator did not ask to rebuild keeps its
        identity and its times.
        """
        self._in(self.at(self.monday, 8))
        self._out(self.at(self.monday, 17))
        self._in(self.at(self.tuesday, 8))
        self._out(self.at(self.tuesday, 17))
        monday = self._stays()[0]
        before = (monday.check_in, monday.check_out, monday.write_date)

        self._rebuild_from_tuesday()

        self.assertTrue(monday.exists())
        self.assertEqual((monday.check_in, monday.check_out, monday.write_date), before)
        self.assertEqual(len(self._stays()), 2)
