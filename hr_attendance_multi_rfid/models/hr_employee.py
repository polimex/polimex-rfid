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
            return {'event_count': 0, 'attendance_count': 0}

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

        # Process events to create attendance records
        presence = [None, None]  # [check_in, check_out]
        in_zone = None
        previous_attendance_id = None
        previous_event_id = None

        for e in event_ids:
            # Events already accounted for by a person's record are consumed.
            if settled_by_a_person(e.event_time):
                e.in_or_out = 'no_info'
                continue

            e.in_or_out = 'no_info'

            # Handle check-in events (entry readers)
            if e.reader_id in in_readers_ids:
                # Create new check-in or override existing based on zone settings
                if not presence[0] or (presence[0] and in_zone.overwrite_check_in):
                    if presence[0] and in_zone.overwrite_check_in and previous_event_id:
                        previous_event_id.in_or_out = 'no_info'
                    presence[0] = e.event_time
                    e.in_or_out = 'in'
                    in_zone = att_zone_ids.filtered(lambda z: e.door_id in z.door_ids)

            # Handle check-out events (exit readers)
            if e.reader_id in out_readers_ids:
                if presence[0]:
                    # Normal check-out for open attendance
                    presence[1] = e.event_time
                    e.in_or_out = 'out'
                elif not presence[0] and previous_attendance_id:
                    # Out-of-order check-out - update previous attendance if allowed
                    in_zone = att_zone_ids.filtered(lambda z: e.door_id in z.door_ids)
                    if in_zone.overwrite_check_out and previous_attendance_id.check_out and (
                            e.event_time - previous_attendance_id.check_out) < timedelta(hours=8):
                        previous_attendance_id.with_context(no_validity_check=True, rfid_machinery_write=True).check_out = e.event_time
                        e.in_or_out = 'out'

            # Create attendance record when we have both check-in and check-out
            if all(presence):
                if collides_with_a_person(presence[0], presence[1]):
                    # The pair straddles a person's record (in-event before
                    # it, out-event after): their statement stands, the
                    # machine does not write over or around it.
                    presence = [None, None]
                    previous_event_id = e
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

            previous_event_id = e

        # Handle last open attendance (check-in without check-out). Replayed
        # historical events bypass validity the same way the paired-create
        # above does - an open check-in inserted into the past would
        # otherwise be refused.
        if presence[0] and not presence[1] \
                and not collides_with_a_person(presence[0], None):
            self.env['hr.attendance'].with_context(no_validity_check=True).create({
                'check_in': presence[0],
                'in_zone_id': in_zone and in_zone.id,
                'employee_id': employee_id.id,
                'in_mode': 'rfid',
            })
            attendance_count += 1

        return {'event_count': len(event_ids), 'attendance_count': attendance_count}
