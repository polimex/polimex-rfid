from datetime import datetime, time, timedelta

from odoo import models, exceptions, _, api, fields
from pytz import timezone, utc

import logging

_logger = logging.getLogger(__name__)

# An attendance without a check-out has not ended yet: for the rebuild's
# overlap arithmetic it runs to the end of time.
STILL_OPEN = datetime.max


class HrEmployee(models.Model):
    _name = "hr.employee"
    _inherit = "hr.employee"

    def _last_open_checkin(self, zone_id=None, before_dt=None):
        """Find the last open check-in for this employee.
        
        :param zone_id: Optional zone to filter by
        :param before_dt: Optional datetime to find check-ins before this time
        :return: hr.attendance record or False
        """
        self.ensure_one()
        if zone_id is not None:
            domain = [
                ('employee_id', '=', self.id),
                ('check_out', '=', False),
                ('in_zone_id', '=', zone_id),
            ]
            if before_dt is not None:
                domain.append(('check_in', '<=', before_dt))
            _last = self.env['hr.attendance'].search(domain, limit=1)
            if _last:
                return _last
        domain = [
            ('employee_id', '=', self.id),
            ('check_out', '=', False),
        ]
        if before_dt is not None:
            domain.append(('check_in', '<', before_dt))
        return self.env['hr.attendance'].search(domain, limit=1)

    def attendance_action_change_with_date(self, action_date, zone_id=None):
        """ Check In/Check Out action with support for out-of-order events.
        
        This method handles both real-time and historical attendance events:
        - Check In: Creates a new attendance record
        - Check Out: Finds and updates the appropriate attendance record
        
        For out-of-order events:
        - Check In: Always creates new attendance (may be inserted between existing ones)
        - Check Out: Finds the correct open attendance based on event time
        
        :param action_date: The datetime of the attendance action
        :param zone_id: Optional zone ID for the attendance
        :return: The created or modified attendance record
        """
        self.ensure_one()

        # First, look for an open attendance that could be closed by this event
        # This handles out-of-order check-outs properly
        open_attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
            ('check_out', '=', False),
            ('check_in', '<', action_date)  # Check-in must be before this event
        ], order='check_in desc', limit=1)
        
        # Determine if this should be a check-out based on:
        # 1. Existence of an open attendance that started before this event
        # 2. Current attendance state (for real-time events)
        should_check_out = open_attendance and (
            self.attendance_state == 'checked_in' or 
            self.env.context.get('force_check_out', False)
        )
        
        if should_check_out:
            # Validate that check_out is after check_in
            if action_date < open_attendance.check_in:
                _logger.warning(
                    'Attempted to set check_out (%s) before check_in (%s) for employee %s. '
                    'Setting check_out to check_in + 1 minute to maintain data integrity.',
                    action_date, open_attendance.check_in, self.name
                )
                # Set check_out to check_in + 1 minute to maintain valid record
                action_date = open_attendance.check_in + timedelta(minutes=1)
            
            # A machinery write, so the record stays rebuildable. The
            # no_validity_check a historical replay sets travels along on its
            # own: with_context ADDS to the context this code already runs
            # under, it does not replace it.
            open_attendance.with_context(
                rfid_machinery_write=True).check_out = action_date
            return open_attendance
        
        # For check-in or when no suitable open attendance found
        if self.attendance_state != 'checked_in' or not open_attendance:
            # Create new attendance record, stamped as made by the RFID
            # machinery so a rebuild can tell it from a typed-in one.
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
                'in_zone_id': zone_id,
                'in_mode': 'rfid',
            }

            # A historical event's no_validity_check is already in the context
            # this create runs under, so the constraints are bypassed without
            # it having to be re-stated here.
            return self.env['hr.attendance'].create(vals)
        
        # If we get here, something went wrong
        raise exceptions.UserError(
            _('Cannot perform check out on %(empl_name)s, '
              'could not find corresponding check in. Your '
              'attendances have probably been modified manually '
              'by human resources.') % {'empl_name': self.name}
        )

    def _recalc_window(self, from_date, to_date):
        """The two days the operator chose, as the moments that bound them.

        The operator picks days; door events and attendance records are
        moments. A day is only a day somewhere, so it is measured where the
        person works: their last day ends when midnight passes for them, not
        when it passes in London. Core reads an employee's day off their own
        timezone the same way
        (odoo/addons/hr_attendance/models/hr_attendance.py:273), and turns a
        chosen day into a moment the same way
        (odoo/addons/hr_holidays/wizard/hr_leave_generate_multi_wizard.py:77-78).

        The chosen last day is included whole, so the window ends where the
        next day begins and the bound is "before", not "up to".

        :return: (start, end) - naive UTC datetimes, as stored in the database
        """
        self.ensure_one()
        from_date = fields.Date.to_date(from_date) or fields.Date.today()
        to_date = fields.Date.to_date(to_date) or fields.Date.today()
        tz = timezone(self.tz or self.env.user.tz or 'UTC')
        start = tz.localize(datetime.combine(from_date, time.min))
        end = tz.localize(datetime.combine(to_date + timedelta(days=1), time.min))
        return (start.astimezone(utc).replace(tzinfo=None),
                end.astimezone(utc).replace(tzinfo=None))

    def _recalc_clear_domain(self, period_start, period_end):
        """Which of this person's attendance a rebuild is asking to remove.

        What the RFID machinery itself made for the period (in_mode 'rfid'),
        inside it and nothing outside it - never what somebody typed in. A
        record entered by hand (manual, kiosk, systray, or anything else)
        cannot be worked out again from the door events, so deleting it would
        lose it for good; it is never asked for.
        """
        self.ensure_one()
        return [
            ('check_in', '>=', period_start),
            ('check_in', '<', period_end),
            ('employee_id', '=', self.id),
            ('in_mode', '=', 'rfid'),
        ]

    @api.model
    def _recalc_attendance_context(self):
        """Resolve, once, what counts as an attendance door.

        Every employee in a rebuild is measured against the same zones and the
        same readers; reading them again for each person would repeat the same
        searches for nothing.
        """
        att_zone_ids = self.env['hr.rfid.zone'].search([('attendance', "=", True)])
        doors_with_attendance = att_zone_ids.mapped('door_ids')
        readers_ids = doors_with_attendance.mapped('reader_ids')
        return {
            'zones': att_zone_ids,
            'doors': doors_with_attendance,
            'in_readers': readers_ids.filtered(lambda r: r.reader_type == '0'),
            'out_readers': readers_ids.filtered(lambda r: r.reader_type == '1'),
            # Does ANY attendance zone follow only certain departments or
            # tags? Asked once here so that the installations which have none
            # - most of them - skip the per-employee question below entirely.
            'has_restricted_zones': bool(att_zone_ids.filtered(
                lambda z: z.permitted_department_ids or z.permitted_employee_category_ids)),
        }

    def recalc_attendance(self, from_date=None, to_date=None):
        """Recalculate attendance records from RFID events.

        This method processes RFID events to recreate attendance records,
        handling out-of-order events and various edge cases.

        Everything is done in one transaction here. A rebuild covering more
        than a handful of people belongs in the background - see
        hr.attendance.recalc.run, which drives the same per-employee work one
        committed person at a time.

        :param from_date: Start date for recalculation (default: 30 days ago)
        :param to_date: End date for recalculation (default: today)
        """
        if from_date is None:
            from_date = fields.Date.today() - timedelta(days=30)
        to_date = to_date or fields.Date.today()

        # The real chokepoint: every caller passes through here, so this is
        # where a module that forbids rebuilding gets its say. The hook itself
        # is declared in hr_rfid, which every module in this family depends on,
        # so no load order can leave a do-nothing version of it in front of the
        # one that actually refuses.
        self._check_recalc_allowed(from_date, to_date)

        ctx = self._recalc_attendance_context()
        for employee_id in self:
            employee_id._recalc_attendance_one(from_date, to_date, ctx)

    def _recompute_daily_figures(self, from_date, to_date):
        """The daily measurements of the period a rebuild has just replayed.

        Nothing to do here - this module makes attendance, it does not measure
        it. hr_attendance_late overrides this and recomputes its daily rows.

        It exists because rebuilding the attendance is only half of what the
        operator asked for. The measurements are recomputed by the write hooks
        of the records the rebuild touches, so the days that HAVE attendance
        come out right - and every other day in the period keeps whatever it
        was last told. Measured on a customer database after a rebuild of one
        June: 83 of 148 daily rows still carried the old figures, all of them
        days with no passage at all, which is what the operator was looking at
        and rightly called wrong.
        """
        return

    def _recalc_attendance_one(self, from_date, to_date, ctx):
        """Rebuild attendance for ONE employee, from the events in the period.

        Split out of recalc_attendance unchanged, so the background job can do
        one person, commit, and carry on. Deleting the period and replaying it
        is only consistent as a whole, which makes one person the smallest
        piece of work that can safely be committed on its own.

        :param ctx: the zones and readers from _recalc_attendance_context()
        :return: what was done, for the rebuild's report
        """
        self.ensure_one()
        # Asked again here: the background job calls this method directly, and
        # a rebuild that became forbidden while it was queued must not run.
        self._check_recalc_allowed(from_date, to_date)

        att_zone_ids = ctx['zones']
        doors_with_attendance = ctx['doors']
        in_readers_ids = ctx['in_readers']
        out_readers_ids = ctx['out_readers']
        # Kept under its old name so the rebuilding code below reads exactly as
        # it did when it was the body of a loop over several employees.
        employee_id = self
        attendance_count = 0

        # The period the operator asked for, and nothing outside it. Both the
        # events replayed and the attendance deleted are cut to the same two
        # moments: anything else would delete a day it never replays, or
        # replay a day it never cleared.
        period_start, period_end = self._recalc_window(from_date, to_date)

        # Get all relevant events for this employee
        event_ids = self.env['hr.rfid.event.user'].search([
            ('employee_id', '=', employee_id.id),
            ('door_id', 'in', doors_with_attendance.mapped('id')),
            ('event_time', '>=', period_start),
            ('event_time', '<', period_end),
            ('event_action', '=', '1')  # Only granted access events
        ], order='event_time')

        if not event_ids:  # no events for processing
            # Still their period, still asked for: the figures are recomputed
            # even where there was nothing to replay.
            self._recompute_daily_figures(from_date, to_date)
            return {'event_count': 0, 'attendance_count': 0}

        # Which of those doors actually follow THIS person. A zone limited to
        # certain departments or tags is skipped on every live passage
        # (hr.rfid.zone._check_employee_permit), so a rebuild that ignored the
        # limit handed people attendance in zones that never tracked them -
        # the same day told two different stories depending on which machine
        # wrote it. A door shared with a zone that does follow them stays in,
        # exactly as the live loop over zones leaves it in.
        permitted_doors = doors_with_attendance
        if ctx['has_restricted_zones']:
            permitted_doors = att_zone_ids.filtered(
                lambda z: z._check_employee_permit(employee_id)).door_ids
        # Asked once per event below, and a big tenant replays hundreds of
        # thousands of them, so all three questions are set lookups rather
        # than scans of a recordset.
        permitted_door_ids = set(permitted_doors.ids)
        in_reader_ids = set(in_readers_ids.ids)
        out_reader_ids = set(out_readers_ids.ids)

        # Remove the attendance this system made for the period, and only
        # that - what a person typed in by hand is theirs, not ours to replay.
        self.env['hr.attendance'].search(
            self._recalc_clear_domain(period_start, period_end)).unlink()

        # What survived the clearing is a person's word - records typed in or
        # taken over by an operator. The replay treats each as settled ground:
        # door events falling under one are consumed (the person's record
        # already accounts for them), and no machine record may overlap one.
        # Without this, the operator's 9:00-17:30 next to that day's door
        # events replayed into a SECOND overlapping record: the day counted
        # twice, and the overlap crashes core's overtime engine besides
        # (hr_attendance_overtime_rule.py, singleton per day). An OPEN
        # preserved record (no check-out yet) owns everything from its
        # check-in on: the human's standing statement wins until they close
        # or remove it and rebuild again.
        preserved = self.env['hr.attendance'].search([
            ('check_in', '>=', period_start),
            ('check_in', '<', period_end),
            ('employee_id', '=', employee_id.id),
            # Core's absence detection plants a one-second record at local
            # midnight for every no-show. It is bookkeeping, not a person's
            # word - and treating it as one would hand it the whole night:
            # a 22:00-06:00 shift straddles that midnight second and would
            # never be replayed again.
            ('in_mode', '!=', 'technical'),
        ])
        # An open record (no check-out) runs to STILL_OPEN, so both questions
        # below are ordinary interval arithmetic on closed spans.
        preserved_spans = [(a.check_in, a.check_out or STILL_OPEN)
                           for a in preserved]

        def settled_by_a_person(moment):
            return any(start <= moment <= stop for start, stop in preserved_spans)

        def collides_with_a_person(start, stop):
            stop = stop or STILL_OPEN
            return any(start <= p_stop and p_start <= stop
                       for p_start, p_stop in preserved_spans)

        def zone_of(event):
            """The attendance zone this passage happened in.

            A door can belong to more than one; the first is taken, because
            everything asked of it here (does it move the check-in, does it
            reopen the last stay, which zone is written on the record) needs
            one answer. Reading a field off the whole set raised "Expected
            singleton" and the background worker turned that into
            "Something went wrong" for EVERY person in the rebuild - one
            shared door was enough.
            """
            return att_zone_ids.filtered(
                lambda z: event.door_id in z.door_ids)[:1]

        # Process events to create attendance records
        presence = [None, None]  # [check_in, check_out]
        in_zone = self.env['hr.rfid.zone']
        previous_attendance_id = None
        # The passage that opened the presence currently being built. Kept so
        # that when it turns out to stand for nothing, the reason lands on THE
        # ENTRY itself rather than on whatever event happened to come last.
        # The empty recordset, not None, so every marker call below is safe
        # whether or not an entry is open.
        checkin_event = self.env['hr.rfid.event.user']
        # Passages nothing could be made of because they carry no direction.
        # Counted, and said once at the end - a line per passage would drown
        # the log of a rebuild that reads hundreds of thousands of them.
        without_direction = 0

        for e in event_ids:
            if e.door_id.id not in permitted_door_ids:
                e._rewrite_no_attendance('not_tracked_here')
                continue

            # Events already accounted for by a person's record are consumed.
            if settled_by_a_person(e.event_time):
                e._rewrite_no_attendance('manual_record')
                continue

            # Handle check-in events (entry readers)
            if e.reader_id.id in in_reader_ids:
                # Create new check-in or override existing based on zone settings
                if not presence[0] or in_zone.overwrite_check_in:
                    # A later entry replaces this one; the earlier passage no
                    # longer stands for any attendance.
                    checkin_event._rewrite_no_attendance('superseded')
                    presence[0] = e.event_time
                    checkin_event = e
                    e._mark_attendance('in')
                    in_zone = zone_of(e)
                else:
                    # Already checked in and this zone keeps the first entry.
                    # By far the commonest silent discard: measured on a live
                    # installation, 1417 of 1420 unexplained passages were this.
                    e._rewrite_no_attendance('already_inside')

            # Handle check-out events (exit readers)
            elif e.reader_id.id in out_reader_ids:
                if presence[0]:
                    # Normal check-out for open attendance
                    presence[1] = e.event_time
                    e._mark_attendance('out')
                elif previous_attendance_id:
                    # Out-of-order check-out - update previous attendance if allowed
                    in_zone = zone_of(e)
                    if in_zone.overwrite_check_out and previous_attendance_id.check_out and (
                            e.event_time - previous_attendance_id.check_out) < timedelta(hours=8):
                        previous_attendance_id.with_context(no_validity_check=True, rfid_machinery_write=True).check_out = e.event_time
                        e._mark_attendance('out')
                    else:
                        e._rewrite_no_attendance('nothing_to_close')
                else:
                    e._rewrite_no_attendance('nothing_to_close')

            else:
                # Neither an entry nor an exit: the passage carries no reader
                # at all (the events are found by door, not by reader), so
                # there is no direction to read it as. Named rather than left
                # blank - and note the live machinery does NOT agree here: it
                # treats anything that is not an entry reader as an exit
                # (hr_rfid/models/hr_rfid_event_user.py, in create()), so such
                # a passage reads differently before and after a rebuild.
                without_direction += 1
                e._rewrite_no_attendance('direction_unknown')

            # Create attendance record when we have both check-in and check-out
            if all(presence):
                if collides_with_a_person(presence[0], presence[1]):
                    # The pair straddles a person's record (in-event before
                    # it, out-event after): their statement stands, the
                    # machine does not write over or around it.
                    e._rewrite_no_attendance('manual_record')
                    checkin_event._rewrite_no_attendance('manual_record')
                    presence = [None, None]
                    checkin_event = self.env['hr.rfid.event.user']
                    continue
                previous_attendance_id = self.env['hr.attendance'].with_context(no_validity_check=True).create({
                    'check_in': presence[0],
                    'check_out': presence[1],
                    'employee_id': employee_id.id,
                    'in_zone_id': in_zone and in_zone.id,
                    'in_mode': 'rfid',
                })
                attendance_count += 1
                presence = [None, None]
                checkin_event = self.env['hr.rfid.event.user']

        # Handle last open attendance (check-in without check-out). Replayed
        # historical events bypass validity the same way the paired-create
        # above does - an open check-in inserted into the past would
        # otherwise be refused.
        if presence[0] and not presence[1]:
            if collides_with_a_person(presence[0], None):
                # The last entry runs into attendance a person entered by
                # hand: theirs stands, and the passage says so instead of
                # ending the day as an unexplained blank.
                checkin_event._rewrite_no_attendance('manual_record')
            else:
                self.env['hr.attendance'].with_context(no_validity_check=True).create({
                    'check_in': presence[0],
                    'in_zone_id': in_zone and in_zone.id,
                    'employee_id': employee_id.id,
                    'in_mode': 'rfid',
                })
                attendance_count += 1

        if without_direction:
            _logger.warning(
                "%s passages of %s could not be read as an arrival or a "
                "departure and were left out of the attendance: they carry no "
                "reader. Each one says so in Why Not Counted.",
                without_direction, employee_id.display_name)

        # The whole period the operator asked for, not only the days this
        # replay happened to touch.
        self._recompute_daily_figures(from_date, to_date)

        return {'event_count': len(event_ids), 'attendance_count': attendance_count}
