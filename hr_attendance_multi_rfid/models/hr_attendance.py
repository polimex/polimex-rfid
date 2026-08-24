import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)

#: Longer than this and it is not a stay any more. Crossing midnight is
#: ordinary work - plenty of people are on shift at midnight - but nobody is
#: on site for more than a whole day, so a span longer than one is a badge-out
#: that never happened. Measured on a customer database: 1906 records ran past
#: 24 hours and 356 past a week, the longest 361 days, each of them counting
#: its whole length towards every day it touched.
MAX_PLAUSIBLE_STAY_HOURS = 24.0


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

    def _get_zone_settings(self):
        """Auto-close settings of the zone THIS attendance was opened in.

        The zone is read from the record's own in_zone_id - the zone the
        session belongs to - never from employee_id.in_zone_ids, which says
        where the person is NOW. A person who already left the zone has
        nothing there, which made their forgotten open attendance impossible
        to close.

        :return: (max_time_in_zone, auto_close_time_for_zone) of the
                 session's zone, or (False, False) when the record carries no
                 attendance zone or the zone sets no limit
                 (max_time_in_zone == 0).
        """
        self.ensure_one()
        zone = self.in_zone_id
        if not zone or not zone.attendance:
            return False, False
        if float_compare(zone.max_time_in_zone, 0.0, precision_digits=2) <= 0:
            return False, False
        return zone.max_time_in_zone, zone.auto_close_time_for_zone

    def _settled_stay_hours(self):
        """How long a forgotten stay is credited when it is settled.

        The zone answers first, exactly as its own fields promise: Auto-close
        Worked Hours, and where that is not set, Maximum Hours in Zone. A
        record that carries no zone - everything brought over from an older
        system does - is credited the day the person was supposed to work,
        from their own working schedule. Never a number invented here.

        :return: hours, or 0.0 when neither can say and the record is left
                 alone rather than settled on a guess.
        """
        self.ensure_one()
        max_time, autoclose = self._get_zone_settings()
        if float_compare(autoclose or 0.0, 0.0, precision_digits=2) > 0:
            return autoclose
        if max_time:
            return max_time
        return self.employee_id.resource_calendar_id.hours_per_day or 0.0

    def stay_is_not_credible(self):
        """Whether this record is a badge-out that never happened.

        Two shapes, one meaning. An OPEN record that has outstayed its zone's
        limit - the zone says how long anybody may be inside. And a CLOSED one
        longer than a whole day: whoever or whatever closed it did so long
        after the person left, and until it is settled it lends its entire
        length to every day it touches.
        """
        self.ensure_one()
        if self.check_out:
            stayed = (self.check_out - self.check_in).total_seconds() / 3600.0
            return float_compare(stayed, MAX_PLAUSIBLE_STAY_HOURS,
                                 precision_digits=2) > 0
        max_time, _autoclose = self._get_zone_settings()
        if not max_time:
            return False
        open_worked_hours = (fields.Datetime.now() - self.check_in).total_seconds() / 3600.0
        return float_compare(open_worked_hours, max_time, precision_digits=2) > 0

    def needs_autoclose(self):
        """Kept under its old name for callers outside this module."""
        self.ensure_one()
        return not self.check_out and self.stay_is_not_credible()

    def autoclose_attendance(self):
        """Settle a forgotten stay with the hours the zone or schedule says.

        check_out = check_in + the settled duration. A record that was already
        closed - far too late - is moved back to the same duration, and the
        chatter keeps what it used to say, because a number nobody can explain
        is worse than a number somebody changed on purpose.
        """
        self.ensure_one()
        hours = self._settled_stay_hours()
        if float_compare(hours, 0.0, precision_digits=2) <= 0:
            _logger.warning(
                "Attendance %s of %s runs from %s to %s and cannot be settled: "
                "its zone sets no limit and the employee has no working "
                "schedule to credit. Set one, or correct the record by hand.",
                self.id, self.employee_id.display_name, self.check_in,
                self.check_out or "(still open)")
            return
        was = self.check_out
        # Stamped with core's own "Automatic Check-Out" mode: the operator's
        # existing filter (hr_attendance_view.xml, "Automatically Checked-Out")
        # then lists these for free, and a record closed by the zone rule is
        # never mistaken for a person's real badge-out. Core's calendar-based
        # cron and this zone sweep work the same pool of open records - either
        # may close first, the other then finds check_out set and moves on.
        self.with_context(rfid_machinery_write=True).write({
            'check_out': self.check_in + timedelta(hours=hours),
            'out_mode': 'auto_check_out',
        })
        if was:
            # Only the already-closed case leaves a note: an open record being
            # closed is the ordinary end of a stay, while MOVING a check-out
            # that was already there changes a number somebody may have read.
            self.message_post(body=self.env._(
                "Check-out moved back to %(new)s: the stay ran from %(start)s "
                "to %(old)s, which is longer than a day and therefore a "
                "badge-out that never happened. Credited %(hours).2f hours.",
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
        Only records carrying a zone can be measured against a zone limit,
        so only those are read; whether the limit has passed still depends
        on each zone's own settings.
        """
        # Still open, and the zone says how long that may last.
        forgotten = self.search([
            ('check_out', '=', False),
            ('in_zone_id', '!=', False),
        ])
        # Closed, but only long after the person left. No zone needed: a stay
        # longer than a day is not a stay whatever recorded it.
        #
        # Asked of the two timestamps, NOT of worked_hours: that field is what
        # the person is PAID for, with the unpaid break already taken off, so
        # it reads under a day for a record that really spans more than one.
        # Measured on a customer database: 1827 records ran past 24 hours and
        # worked_hours reported 0 of them - a search on it settled 122 and
        # walked past the rest without a word.
        self.env.cr.execute(
            "SELECT id FROM hr_attendance "
            " WHERE check_out IS NOT NULL "
            "   AND check_out - check_in > %s * interval '1 hour'",
            (MAX_PLAUSIBLE_STAY_HOURS,),
        )
        forgotten |= self.browse(row[0] for row in self.env.cr.fetchall())
        for att in forgotten.filtered(lambda a: a.stay_is_not_credible()):
            att.autoclose_attendance()

    # bypass validity if old events processed
    def _check_validity(self):
        if self.env.context.get('no_validity_check', None) is None:
            super(HrAttendance, self)._check_validity()
