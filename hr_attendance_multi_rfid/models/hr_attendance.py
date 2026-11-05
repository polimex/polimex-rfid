import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.date_utils import sum_intervals
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)

# What counts as a forgotten badge is not a number chosen here, and it is
# asked in exactly ONE place: Settings -> Attendances -> Automatic Check-Out,
# with its tolerance (res.company.auto_check_out / auto_check_out_tolerance,
# core). Per person: the hours their own schedule says for THAT day, plus the
# tolerance. What is then recorded is the company's Forgotten Badge policy,
# right beside it (owner's decision, 24.08.2026).
#
# The zones used to carry a second pair of hours answering the same question
# with a different number - 12 against core's 10 on the installation this came
# from - and neither the operator nor the code could say which one was in
# force. Those fields are gone; the migration carries what they said onto the
# company. Crossing midnight is never the criterion: it is ordinary work.

# Why old data can make a settling write fail: core's overlap check (a
# ValidationError, which is a UserError), or its overtime engine on a day with
# overlapping stays ("Expected singleton", a ValueError). Concurrency errors must
# stay out of this list: Odoo retries the request or the task only if they reach
# it (odoo/service/model.py, retrying), and a passage or a stay absorbed here
# would simply be lost.
SETTLING_REFUSED = (UserError, ValueError)


def stay_outlasts(start, end, allowed, earlier=0.0):
    """Whether a stay from start to end ran past what the person's day allows.

    The one comparison behind every verdict on a stay: the record the sweep
    looks at, the passage that finds a stay still open, and the replay of old
    passages, which has no record yet.

    :param allowed: hr.attendance._max_allowed_stay_hours(); 0.0 means nothing
                    here can call this stay forgotten
    :param earlier: hours the person's earlier stays of that day already took
                    from it, as core's own check-out rule counts them
    """
    if float_compare(allowed, 0.0, precision_digits=2) <= 0:
        return False
    stayed = (end - start).total_seconds() / 3600.0 + earlier
    return float_compare(stayed, allowed, precision_digits=2) > 0


class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _inherit = 'hr.attendance'

    department_id = fields.Many2one(
        store=True,
        help="Employee's department at the time of this attendance record. This field is stored "
             "to maintain historical accuracy even if the employee later changes departments."
    )

    check_in = fields.Datetime(
        index=True,
        help="Date and time when the employee checked in to work. This is automatically recorded "
             "when entering an RFID attendance zone or can be manually set by HR managers."
    )

    check_out = fields.Datetime(
        index=True,
        help="Date and time when the employee checked out from work. This is automatically recorded "
             "when leaving an RFID attendance zone or can be manually set by HR managers."
    )
    in_zone_id = fields.Many2one(
        'hr.rfid.zone',
        help="The RFID zone where this attendance session is taking place. Set when checking in "
             "and cleared when checking out. Used to track which area the employee is working in.",
    )
    forgotten_badge = fields.Boolean(
        string="Forgotten Badge",
        readonly=True, index=True,
        help="Set by the system when this stay outlasted what the working "
             "schedule and the tolerance allow, so somebody clearly forgot to "
             "badge. What was then recorded depends on the company's "
             "Forgotten Badge setting: the hours may have been settled (the "
             "record also reads Automatically Checked-Out), or nothing was "
             "counted for that day and the real hours have to be entered by "
             "hand.",
    )

    # Every attendance the RFID machinery creates is stamped 'rfid', so a
    # rebuild can tell its own records from what a person typed in by hand
    # (manual/kiosk/systray). On uninstall the records fall back to the
    # field's default ('manual') rather than being deleted.
    in_mode = fields.Selection(
        selection_add=[('rfid', "RFID")],
        ondelete={'rfid': 'set default'},
    )

    def _update_overtime(self, attendance_domain=None):
        """Core's overtime run, made to leave every figure of the day right.

        Two gaps, both found on a customer database (customer case,
        12.10.2026), and neither is a policy of ours - each makes the record
        agree with core's own formula:

        * Worked hours never computed. A transfer from an older system writes
          attendance straight into the table, past the ORM, and leaves
          worked_hours empty: more than half of the closed stays there read 0
          hours worked. Core's overtime run reads only check-in and check-out,
          so it never fills them. They are marked here exactly as the ORM
          marks a record whose times changed (``modified`` on the two fields
          _compute_worked_hours depends on - the idiom core uses after its own
          raw updates, l10n_gcc_invoice/models/account_move.py:61).
        * Regular hours left behind. expected_hours is stored and equals
          worked minus overtime (hr_attendance.py, _compute_expected_hours),
          but the overtime run marked only overtime for recomputation until
          odoo/odoo 17577a1f9c6 (in 19.0 since 30.03.2026). On a server older
          than that a day built record by record keeps the regular hours each
          record had when it was alone - about a third of the records on the
          same database. Marking it here is what that commit does; on a newer
          server it is the same mark twice.

        Core's own "Regenerate overtimes" button on the overtime ruleset runs
        this method, so data from the earliest version that carries the
        ruleset on is put right from the screen, with no script
        (hr_attendance_overtime_ruleset.py, _attendances_to_regenerate_for).
        Older history is not reached by that button; a transfer puts its own
        history right when it runs again (hr_rfid_odoo_import,
        _settle_attendance_figures).
        """
        if not attendance_domain:
            attendance_domain = self._get_overtimes_to_update_domain()
        attendances = self | self.search(attendance_domain)
        never_figured = attendances.filtered(
            lambda att: att.check_out and not att.worked_hours)
        never_figured.modified(['check_in', 'check_out'])
        result = super()._update_overtime(attendance_domain)
        self.env.add_to_compute(self._fields['expected_hours'], attendances)
        return result

    def write(self, vals):
        for att in self:
            if vals.get('check_out', False) and not att.check_out and att.in_zone_id:
                if self.env.context.get('from_event', None) is None and not self.search_count([
                    ('employee_id', '=', att.employee_id.id),
                    ('check_out', '=', False),
                    ('in_zone_id', '=', att.in_zone_id.id),
                    ('id', '!=', att.id),
                ], limit=1):
                    # THIS record is being closed, by this very write: the zone
                    # only has to take the person off its list, and only when
                    # no other stay of theirs is still open there. It must not
                    # look for "the open stay" itself: that would be the newest
                    # one, closed at the current time.
                    att.in_zone_id.with_context(stay_being_closed=True).person_left(att.employee_id)
                vals['in_zone_id'] = False

        # A person editing the times of a machine-born record takes it over:
        # the operator who types the check-out a worker forgot is stating a
        # fact the door events do not hold, and a rebuild must never replay
        # that fact away. The record becomes theirs (in_mode 'manual') - the
        # one kind the rebuild's delete-domain preserves. Machinery writes
        # carry rfid_machinery_write (or the zone flow's from_event) and keep
        # the record rebuildable: an administrative close is not a human
        # statement.
        touched_times = 'check_in' in vals or 'check_out' in vals
        by_a_person = not (self.env.context.get('rfid_machinery_write')
                           or self.env.context.get('from_event'))
        taken_over = self.browse()
        if touched_times and by_a_person and 'in_mode' not in vals:
            taken_over = self.filtered(lambda a: a.in_mode in ('rfid', False))
        if touched_times and by_a_person:
            # Their hours replace the guess: the mark says the system settled
            # this stay, and the measurement caps a marked stay at that.
            vals['forgotten_badge'] = False

        res = super(HrAttendance, self).write(vals)
        if taken_over:
            super(HrAttendance, taken_over).write({'in_mode': 'manual'})
        return res

    def _scheduled_day(self):
        """This person's own schedule for the day they came in.

        Core's own answer (hr.employee._get_expected_attendances), so leaves,
        public holidays and two-week calendars are read exactly as the rest of
        Odoo reads them.

        :return: (hours, span) - the hours of work the day is worth, and how
                 long it lasts from its first minute to its last, unpaid break
                 included. (0.0, 0.0) on a day they were not scheduled, which
                 is not a small number but NO answer, and every caller treats
                 it as such.
        """
        self.ensure_one()
        employee = self.employee_id
        # The day the stay belongs to, handed to core in the person's own
        # zone (hr.employee._local_days_bounds).
        day = employee._local_day(self.check_in)
        intervals = list(employee._get_expected_attendances(
            *employee._local_days_bounds(day, day)))
        if not intervals:
            return 0.0, 0.0
        hours = sum_intervals(intervals)
        first = min(start for start, _stop, _meta in intervals)
        last = max(stop for _start, stop, _meta in intervals)
        return hours, (last - first).total_seconds() / 3600.0

    def _scheduled_hours_of_the_day(self):
        """Just the hours of work - see _scheduled_day."""
        self.ensure_one()
        return self._scheduled_day()[0]

    def _working_day_of_the_person(self):
        """The day a stay is judged by, in hours, and how long it lasts.

        Normally the day their schedule describes. On a day they were NOT
        scheduled - a Sunday performance, a call-out - there is no such day,
        and their calendar's ordinary working day stands in for it. Without
        the stand-in a badge forgotten on a Sunday could never be settled at
        all: measured on a fixture, one open Saturday stay was lending 66
        hours to that Saturday and growing by the day.

        The stand-in is never harsher than the real thing: a five-hour evening
        performance stays well inside an ordinary day plus the tolerance and
        is not touched.

        :return: (hours, span). (0.0, 0.0) when even the calendar says
                 nothing, and then no stay is ever settled here.
        """
        self.ensure_one()
        hours, span = self._scheduled_day()
        if float_compare(hours, 0.0, precision_digits=2) > 0:
            return hours, span
        ordinary = self.employee_id.resource_calendar_id.hours_per_day or 0.0
        return ordinary, ordinary

    def _max_allowed_stay_hours(self):
        """The point at which this installation closes a stay by itself.

        The person's own working day plus the company's tolerance - core's
        rule, read from core's own setting. 0.0 when Automatic Check-Out is
        off, or when not even the calendar can say what an ordinary working
        day is for this person: then no stay here can be called forgotten and
        the record is left for a person to judge.

        On a day nobody was scheduled for, the yardstick is that person's
        ordinary working day, NOT the bare tolerance: an evening performance
        on a Sunday is not a forgotten badge, and would read as one if it were.
        """
        self.ensure_one()
        company = self.employee_id.company_id
        if not company.auto_check_out:
            return 0.0
        working_day, span = self._working_day_of_the_person()
        if float_compare(working_day, 0.0, precision_digits=2) <= 0:
            return 0.0
        # Not before the working day itself is over, its break included: with a
        # tolerance smaller than the break, an ordinary day would read as forgotten.
        return max(working_day + company.auto_check_out_tolerance, span)

    def _hours_earlier_that_day(self):
        """What the person's earlier stays of the same day are worth already.

        Core's check-out rule counts them too (hr_attendance.py,
        _cron_auto_check_out): back from lunch, the day is not starting over.
        """
        self.ensure_one()
        employee = self.employee_id
        day = employee._local_day(self.check_in)
        start, _end = employee._local_days_window(day, day)
        return sum(self.search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start),
            ('check_in', '<', self.check_in),
            ('check_out', '!=', False),
            # Core's absence bookkeeping is no stay of the person's.
            ('in_mode', '!=', 'technical'),
        ]).mapped('worked_hours'))

    def _settled_check_out(self):
        """When a settled stay is taken to have ended - the company's policy.

        "Credit the scheduled day" means the person is treated as having
        stayed for as long as their working day lasts, counted from the moment
        they came in - the unpaid break included, exactly as it would be on a
        day they had badged out properly. Somebody who came at eight on a
        08:00-12:00 / 13:00-17:00 schedule is credited to five, and the day
        measures the eight hours it was supposed to hold. Counting only the
        paid hours would leave every settled day an hour short of a normal
        one, and the payroll clerk would have to explain why.

        Measured FROM THE CHECK-IN rather than to the end of the schedule, so
        that somebody who came in for an evening performance - after their
        schedule had ended - is credited a working day too, instead of
        nothing.

        After an earlier stay the same day, only what is left of the day's
        hours is credited: a day is worth what a normal one is worth, however
        many stays it took. Somebody in from eight to twelve who came back at
        one and forgot is credited until five.

        The penalty option takes its hours off that, for companies that treat
        a forgotten badge as time off site. The third credits nothing at all.

        A stay never ends after the moment it is judged at, nor after the
        person's next stay began: with a small tolerance the limit can pass
        before the working day, break included, is over, and a credited day
        must not run into the next entry.

        :return: a naive UTC datetime, or False when nothing is to be
                 credited: no schedule that day, the policy says count
                 nothing, or the penalty swallows the whole day.
        """
        self.ensure_one()
        company = self.employee_id.company_id
        if company.forgotten_badge_policy == 'ignore':
            return False
        hours, span = self._working_day_of_the_person()
        if float_compare(span, 0.0, precision_digits=2) <= 0:
            return False
        earlier = self._hours_earlier_that_day()
        credit = hours - earlier if earlier else span
        if company.forgotten_badge_policy == 'penalty':
            credit -= company.forgotten_badge_penalty_hours or 0.0
        if float_compare(credit, 0.0, precision_digits=2) <= 0:
            return False
        return min(self.check_in + timedelta(hours=credit), self._latest_end_of_stay())

    def _judged_at(self):
        """The moment an open stay is judged at.

        The same seam the day calculation uses to drive the clock, so a test -
        and a rebuild of a past period - judges the stay by the moment it is
        measuring, not by today.
        """
        return self.env.context.get('attendance_calc_time') or fields.Datetime.now()

    def _latest_end_of_stay(self):
        """The last moment this stay can be said to have ended.

        Core's absence mark counts as a next stay here too: its overtime engine
        refuses a record across one (Expected singleton), so a stay credited
        past the mark could never be closed at all.
        """
        self.ensure_one()
        latest = self.check_out or self._judged_at()
        following = self.search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>', self.check_in),
        ], order='check_in', limit=1)
        return min(latest, following.check_in) if following else latest

    def stay_is_not_credible(self):
        """Whether this record is a badge that never happened.

        One criterion for both shapes: the point at which the installation
        would have closed the stay by itself. An OPEN record that has already
        passed it, counted with the person's earlier stays of that day as core
        counts them. And a CLOSED one that spans more than it: whoever closed
        that one did so long after the person left, and until it is settled it
        lends its whole length to the day it belongs to.

        A check-out an operator entered is not that. It is their word on when
        the person left, however long the stay (in_mode 'manual', see write).
        """
        self.ensure_one()
        if not self.check_out:
            return stay_outlasts(self.check_in, self._judged_at(),
                                 self._max_allowed_stay_hours(),
                                 self._hours_earlier_that_day())
        if self.in_mode == 'manual':
            return False
        return stay_outlasts(self.check_in, self.check_out, self._max_allowed_stay_hours())

    def needs_autoclose(self):
        """Kept under its old name for callers outside this module."""
        self.ensure_one()
        return not self.check_out and self.stay_is_not_credible()

    def autoclose_attendance(self):
        """Settle a forgotten stay the way the company says to.

        Credit the scheduled day, that day less a penalty, or nothing at all -
        the Forgotten Badge setting. Either way the stay is MARKED as one, so
        it can be found and asked about.

        A record that was already closed - far too late - is moved back the
        same way, and the chatter keeps what it used to say: a number nobody
        can explain is worse than a number somebody changed on purpose.

        Nothing to credit (Count nothing, or a penalty larger than what is left
        of the day) still has to end an open stay: core keeps one open stay per
        person, refuses to close an open stay behind a later one, and would
        close this one itself for hours nobody credited. It ends where it
        began, worth no hours, and the operator enters the real check-out. A
        record already closed under Count nothing keeps its times and only gets
        the mark, so the day reads as unworked and the record can be found.
        """
        self.ensure_one()
        was = self.check_out
        settled = self._settled_check_out()
        # The credited end stops at the person's next stay, so there is nothing
        # new here for the overlap check to refuse, and old data around the
        # record must not stop it being put right.
        stay = self.with_context(rfid_machinery_write=True, no_validity_check=True)
        if was and self.employee_id.company_id.forgotten_badge_policy == 'ignore':
            stay.write({'forgotten_badge': True})
            return
        # Stamped with core's own "Automatic Check-Out" mode: the operator's
        # existing filter (hr_attendance_view.xml, "Automatically Checked-Out")
        # then lists these for free, and a record closed by the zone rule is
        # never mistaken for a person's real badge-out.
        stay.write({
            'check_out': settled or self.check_in,
            'out_mode': 'auto_check_out',
            'forgotten_badge': True,
        })
        hours = (self.check_out - self.check_in).total_seconds() / 3600.0
        if was:
            # Only the already-closed case leaves a note: an open record being
            # closed is the ordinary end of a stay, while MOVING a check-out
            # that was already there changes a number somebody may have read.
            self.message_post(body=self.env._(
                "Check-out moved back to %(new)s: the stay ran from %(start)s "
                "to %(old)s, longer than the working schedule and the "
                "tolerance allow, so the badge-out never happened. Credited "
                "%(hours).2f hours.",
                new=self.check_out, start=self.check_in, old=was, hours=hours))

    def _at_new_entry(self, moment):
        """This stay, as judged and written when the person badges in again.

        from_event: this is not the person leaving, so neither the zone's list
        nor anti-passback on the doors may change because of it.
        """
        return self.with_context(attendance_calc_time=moment, from_event=True)

    def _settle_before_new_entry(self, moment):
        """The person badged in at a door while this stay still stands open.

        Inside the person's day nothing happens: they simply came back through
        the door. Past it, the badge-out never happened, and the stay is
        settled the way the company says, so that this entry can begin the new
        day. Without it the new day has no record of its own, and the next exit
        closes one stay across both days. A rebuild follows the same rule.

        A door passage is never refused because of old data, so a stay that
        cannot be settled here leaves things as they were.

        :param moment: when the person came in, naive UTC
        :return: True when the stay is out of the way
        """
        self.ensure_one()
        stay = self._at_new_entry(moment)
        if not stay.stay_is_not_credible():
            return False
        # cr.savepoint() flushes before the savepoint exists: somebody else's
        # pending write must fail here, not inside the guard below.
        self.env.cr.flush()
        try:
            with self.env.cr.savepoint():
                stay.autoclose_attendance()
        except SETTLING_REFUSED:
            _logger.warning(
                "Could not settle attendance %s of %s (from %s) when the person "
                "came in again at %s; the passage is kept as already inside.",
                self.id, self.employee_id.display_name, self.check_in, moment,
                exc_info=True)
            return False
        return True

    @api.model
    def _cron_auto_check_out(self):
        """Core's own check-out task, with the rule this module settles by.

        Core schedules "Attendance: Automatically check-out employees"
        (hr_attendance/data/hr_attendance_data.xml) for this business need, and
        the task stays. Core's rule does not run: the owner's decision of
        05.11.2026, a deliberate departure from reuse. check_for_incomplete_attendances
        applies the same measure on a working day, and differs where core's rule
        harms the customer:

        * Core reads no schedule on a day off, so a person at work on a Sunday
          is closed after the bare tolerance while still in the building.
        * Core credits the working day plus the tolerance, whatever the company's
          Forgotten Badge setting says.
        * Core writes all its records in one unprotected loop, so one it cannot
          close stops it for every person of every company.
        """
        self.with_context(rfid_machinery_write=True).check_for_incomplete_attendances()

    @api.model
    def check_for_incomplete_attendances(self):
        """Settle every forgotten stay - the open ones and the over-long ones.

        Run from core's check-out task (see _cron_auto_check_out above). It also
        covers records that were closed long after the person left, history
        brought over from another system included (owner's decision, 05.11.2026).

        Inside the task every settled record is committed: a long first run
        holds no row of attendance against the doors, and what it did survives
        the task's time limit. The scheduler runs the task again while work is
        left (ir.cron, _commit_progress).
        """
        # The shortest day anybody could be held to, plus the smallest
        # tolerance in use. Nothing shorter than that can be over ANY person's
        # limit, so it is what the database is asked for; each record is then
        # judged against the schedule of the person it belongs to.
        companies = self.env['res.company'].sudo().search([
            ('auto_check_out', '=', True)])
        if not companies:
            # Automatic Check-Out is off everywhere: there is no criterion, and
            # inventing one would put a made-up duration into people's hours.
            return
        calendars = self.env['resource.calendar'].sudo().search([
            ('hours_per_day', '>', 0.0)])
        shortest = (min(calendars.mapped('hours_per_day'), default=0.0)
                    + min(companies.mapped('auto_check_out_tolerance')))
        if float_compare(shortest, 0.0, precision_digits=2) <= 0:
            return

        # Still open.
        #
        # Records already judged are left out of both searches: a stay that
        # was settled is within its limit anyway, and one that could NOT be
        # settled must not be tried again every four hours forever. Measured
        # on a customer database: 60 records fail on a defect in core's
        # overtime engine, and retrying them cost the sweep minutes and the
        # log sixty tracebacks per run.
        forgotten = self.search([
            ('check_out', '=', False),
            ('forgotten_badge', '=', False),
            ('employee_id.company_id', 'in', companies.ids),
        ])
        # Closed, but only long after the person left.
        #
        # Asked of the two timestamps, NOT of worked_hours: that field is what
        # the person is PAID for, with the unpaid break already taken off, so
        # it reads under the limit for a record that really spans more than it.
        # Measured on a customer database: 1827 records ran past 24 hours and
        # worked_hours reported 0 of them - a search on it settled 122 and
        # walked past the rest without a word.
        self.env.cr.execute(
            "SELECT id FROM hr_attendance "
            " WHERE check_out IS NOT NULL "
            "   AND forgotten_badge IS NOT TRUE "
            "   AND check_out - check_in > %s * interval '1 hour'",
            (shortest,),
        )
        forgotten |= self.browse(row[0] for row in self.env.cr.fetchall())
        to_settle = forgotten.filtered(lambda a: a.stay_is_not_credible()).sorted('check_in').ids
        in_the_task = bool(self.env.context.get('ir_cron_progress_id'))
        cron = self.env['ir.cron']
        if in_the_task:
            cron._commit_progress(remaining=len(to_settle))
        # Browsed one at a time: a commit empties the cache, and walking a
        # recordset across it reads the whole remainder again each time.
        for att_id in to_settle:
            att = self.browse(att_id)
            # One record that cannot be settled must not cost all the others.
            # Real cause seen on a customer database: two attendances of the
            # same person overlapping on one day, which core's own overtime
            # engine refuses (Expected singleton) the moment either is
            # written. That is the customer's data to put right - and until
            # they do, the rest of the sweep still has to run.
            self.env.cr.flush()
            try:
                with self.env.cr.savepoint():
                    att.autoclose_attendance()
            except SETTLING_REFUSED:
                _logger.warning(
                    "Could not settle attendance %s of %s (%s to %s); it is "
                    "marked as a forgotten badge for somebody to correct by "
                    "hand, and the sweep carries on. More than one attendance "
                    "on the same day is the usual cause.",
                    att.id, att.employee_id.display_name, att.check_in,
                    att.check_out or "(still open)", exc_info=True)
                # Judged, even though it could not be settled - so it is
                # findable, and so the next sweep does not spend itself on it
                # again.
                att.with_context(rfid_machinery_write=True).write(
                    {'forgotten_badge': True})
            if in_the_task and cron._commit_progress(processed=1) <= 0:
                return

    # Core's check that a person's stays do not overlap, skipped where the
    # machinery writes (no_validity_check): a door passage is never refused. The
    # decorator is repeated on purpose: an override without it is no constraint
    # at all, because Odoo collects constraints from the final class member
    # (odoo/orm/models.py:519-535, _constraint_methods).
    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        if self.env.context.get('no_validity_check', None) is None:
            super()._check_validity()
