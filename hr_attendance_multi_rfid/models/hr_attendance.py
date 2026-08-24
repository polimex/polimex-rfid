import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
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

    def write(self, vals):
        for att in self:
            if vals.get('check_out', False) and not att.check_out and att.in_zone_id:
                if self.env.context.get('from_event', None) is None:
                    att.in_zone_id.person_left(att.employee_id)
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
            taken_over = self.filtered(lambda a: a.in_mode == 'rfid')

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
        tz = pytz.timezone(employee.tz or 'UTC')
        day_start = tz.localize(datetime.combine(
            self.check_in.replace(tzinfo=pytz.utc).astimezone(tz).date(), time.min))
        intervals = list(employee._get_expected_attendances(
            day_start, day_start + timedelta(days=1)))
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

    def _max_allowed_stay_hours(self):
        """The point at which this installation closes a stay by itself.

        The person's own scheduled day plus the company's tolerance - core's
        rule, read from core's own setting. 0.0 when Automatic Check-Out is
        off, or on a day nobody was scheduled for: then no stay here can be
        called forgotten, and the record is left for a person to judge. (An
        evening performance on a Sunday is not a forgotten badge, and would be
        one if the answer were "the tolerance".)
        """
        self.ensure_one()
        company = self.employee_id.company_id
        if not company.auto_check_out:
            return 0.0
        scheduled = self._scheduled_hours_of_the_day()
        if float_compare(scheduled, 0.0, precision_digits=2) <= 0:
            return 0.0
        return scheduled + company.auto_check_out_tolerance

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

        The penalty option takes its hours off that, for companies that treat
        a forgotten badge as time off site. The third credits nothing at all.

        :return: a naive UTC datetime, or False when nothing is to be
                 credited: no schedule that day, the policy says count
                 nothing, or the penalty swallows the whole day.
        """
        self.ensure_one()
        company = self.employee_id.company_id
        if company.forgotten_badge_policy == 'ignore':
            return False
        _hours, span = self._scheduled_day()
        if float_compare(span, 0.0, precision_digits=2) <= 0:
            return False
        if company.forgotten_badge_policy == 'penalty':
            span -= company.forgotten_badge_penalty_hours or 0.0
        if float_compare(span, 0.0, precision_digits=2) <= 0:
            return False
        return self.check_in + timedelta(hours=span)

    def stay_is_not_credible(self):
        """Whether this record is a badge that never happened.

        One criterion for both shapes: the point at which the installation
        would have closed the stay by itself. An OPEN record that has already
        passed it, and a CLOSED one that spans more than it - whoever closed
        that one did so long after the person left, and until it is settled it
        lends its whole length to the day it belongs to.
        """
        self.ensure_one()
        allowed = self._max_allowed_stay_hours()
        if float_compare(allowed, 0.0, precision_digits=2) <= 0:
            return False
        # The same seam the day calculation uses to drive the clock, so a
        # test - and a rebuild of a past period - judges the stay by the
        # moment it is measuring, not by today.
        now = self.env.context.get('attendance_calc_time') or fields.Datetime.now()
        end = self.check_out or now
        stayed = (end - self.check_in).total_seconds() / 3600.0
        return float_compare(stayed, allowed, precision_digits=2) > 0

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
        """
        self.ensure_one()
        policy = self.employee_id.company_id.forgotten_badge_policy
        if policy == 'ignore':
            # The company counts nothing for such a day on purpose: the person
            # has to come and have the real hours entered. The times are left
            # exactly as they are - only the mark is added, so the day reads as
            # unworked and the record can be found.
            self.with_context(rfid_machinery_write=True).write(
                {'forgotten_badge': True})
            return
        settled = self._settled_check_out()
        if not settled:
            _logger.warning(
                "Attendance %s of %s runs from %s to %s and cannot be settled: "
                "the employee has no working schedule for that day to credit. "
                "Set one, or correct the record by hand.",
                self.id, self.employee_id.display_name, self.check_in,
                self.check_out or "(still open)")
            return
        hours = (settled - self.check_in).total_seconds() / 3600.0
        was = self.check_out
        # Stamped with core's own "Automatic Check-Out" mode: the operator's
        # existing filter (hr_attendance_view.xml, "Automatically Checked-Out")
        # then lists these for free, and a record closed by the zone rule is
        # never mistaken for a person's real badge-out. Core's calendar-based
        # cron and this zone sweep work the same pool of open records - either
        # may close first, the other then finds check_out set and moves on.
        self.with_context(rfid_machinery_write=True).write({
            'check_out': settled,
            'out_mode': 'auto_check_out',
            'forgotten_badge': True,
        })
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

    @api.model
    def _cron_auto_check_out(self):
        """Ride core's own check-out task instead of keeping a second one.

        Core already schedules "Attendance: Automatically check-out
        employees" (hr_attendance/data/hr_attendance_data.xml) for exactly
        this business need - closing forgotten open attendance. The zone
        sweep is the same job judged by a different rule (the zone's stay
        limit instead of the calendar), so it runs on the same clock: one
        scheduled task, both rules. The check-out each rule writes is
        computed from check-in, never from the moment the task happens to
        run, so sharing the slower core schedule changes no recorded hours.
        """
        machinery = self.with_context(rfid_machinery_write=True)
        super(HrAttendance, machinery)._cron_auto_check_out()
        machinery.check_for_incomplete_attendances()

    @api.model
    def check_for_incomplete_attendances(self):
        """Settle every forgotten stay - the open ones and the over-long ones.

        Run from core's check-out task (see _cron_auto_check_out above).
        Core settles the OPEN ones on its own rule; this covers the same rule
        applied to records that were closed long after the person left, which
        core never looks at again.
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

        # Still open. Core's own task closes these too, on the same rule; this
        # catches the ones it skips (no working schedule version, a flexible
        # calendar it steps over) and the run where it has not come round yet.
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
        for att in forgotten.filtered(lambda a: a.stay_is_not_credible()):
            # One record that cannot be settled must not cost all the others.
            # Real cause seen on a customer database: two attendances of the
            # same person overlapping on one day, which core's own overtime
            # engine refuses (Expected singleton) the moment either is
            # written. That is the customer's data to put right - and until
            # they do, the rest of the sweep still has to run.
            try:
                with self.env.cr.savepoint():
                    att.autoclose_attendance()
            except Exception:
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

    # bypass validity if old events processed
    def _check_validity(self):
        if self.env.context.get('no_validity_check', None) is None:
            super(HrAttendance, self)._check_validity()
