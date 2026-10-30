# -*- coding: utf-8 -*-
import logging
import time
from datetime import datetime, time as day_start

import psycopg2
from pytz import timezone, utc

from odoo import fields
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from odoo.tools import SQL
from odoo.tools.misc import format_date

from .base_importer import EXTERNAL_ID_MODULE, IMPORT_CONTEXT
from .phase import PhaseImporter

_logger = logging.getLogger(__name__)

#: Where the attendance read got to. Working out the figures waits for it.
ATTENDANCE_CURSOR = 'attendance:hr.attendance'
#: Where working out the figures got to, and what it found - kept with the
#: cursors so it survives the pass.
FIGURES_KEY = 'attendance:figures'
#: Hours. Regular hours further than this from worked minus extra do not hold
#: (under two seconds - below what any report rounds to).
FIGURE_TOLERANCE = 0.0005
#: Regular hours that are not worked minus extra, on the attendance aliased
#: ``a`` - one definition for finding a person and for splitting their rows,
#: so a person found always has rows to put right. Null on a row without
#: worked hours, which is why it is asked together with that.
REGULAR_HOURS_DISAGREE = SQL(
    "abs(COALESCE(a.expected_hours, 0)"
    " - (a.worked_hours - COALESCE(a.overtime_hours, 0))) > %s",
    FIGURE_TOLERANCE,
)
#: People named in a protocol line before "and N more".
PEOPLE_NAMED = 5
#: What a person's own records can make core's overtime run refuse. Anything
#: else - a ValueError included - is a fault in the code, and it must show as
#: one rather than be counted as a problem in somebody's days.
FIGURES_DATA_ERRORS = (UserError, psycopg2.IntegrityError, psycopg2.DataError)
#: The two times a row's hours are worked out from (hr_attendance.py,
#: _compute_worked_hours depends on them alone).
FIGURES_TIMES = ['check_in', 'check_out']
#: Kept with the attendance cursor's totals, by source id - so a page read a
#: second time (after a write that failed) changes nothing: stays of the other
#: system this system already holds, to the second - {source id: company}.
SAME_HERE_KEY = 'same_here'
#: Kept the same way: stays left out because a DIFFERENT stay of the person is
#: recorded here at that time - {source id: [person here, company, check-in,
#: check-out, the check-in and check-out recorded here]}.
DIFFERS_KEY = 'differs'


def refused_beside(start, stop, other_start, other_stop):
    """Whether core refuses a stay of a person beside another of theirs.

    hr.attendance._check_validity (odoo/addons/hr_attendance/models/
    hr_attendance.py:206-246), asked of the new stay AND of an open one at the
    moment somebody closes it:

    * two open stays (no check-out) may not sit side by side (:224-234);
    * a stay may not begin while another is running (:219);
    * a closed stay may not have another begin inside it (:238-246).

    An open stay runs until somebody closes it, so it holds all the time from
    its check-in on. Core lets a closed stay be written after an open one has
    begun, and then refuses to close the open one (:238-246) - or, where the
    check is bypassed, counts that time twice. So here the open stay is taken
    for what it will become: a closed stay may not begin after it, and it may
    not begin before a stay that ends after it.
    """
    if stop is None and other_stop is None:
        return True
    if stop is None:
        return start < other_stop
    if other_stop is None:
        return other_start < stop
    return other_start <= start < other_stop or start < other_start < stop


def people_by_id(env, ids):
    """{id: employee} for the protocol: archived people included, deleted ones left out.

    Read as superuser. A transfer writes into several companies, and the
    operator downloading its protocol has one of them selected: read with
    their rights, one person of another tenant (hr.employee's company rule)
    stopped the whole download. Only the name and the time zone are used, and
    the names are in the protocol lines already.
    """
    people = env['hr.employee'].sudo().with_context(active_test=False).browse(sorted(ids))
    return {person.id: person for person in people.exists()}


#: What a day of work says: hours worked, day and night, against what was owed,
#: plus lateness, early leaving and overtime. Every name exists on the target
#: model - asserted by a test. The previous list asked for 'check_in',
#: 'check_out', 'late_minutes', 'early_leave_minutes', 'overtime_minutes' and
#: 'worked_hours', which exist in NEITHER version, so every roll-up would have
#: arrived as an empty shell: a person and a date, and not one of the numbers
#: the record is kept for. 'for_date' is NOT NULL in the target.
EXTRA_OPTIONAL_FIELDS = [
    'for_date', 'shift_number',
    'actual_work_time', 'actual_work_time_day', 'actual_work_time_night',
    'theoretical_work_time', 'late_time', 'early_come_time',
    'early_leave_time', 'overtime', 'overtime_night', 'extra_time',
    'extra_night',
]


class AttendanceImporter(PhaseImporter):
    """Phase 6b: Attendance data.

    Steps: hr.attendance (Direct SQL), the hours worked of the people it
    concerns, hr.attendance.extra (Direct SQL).
    """

    PHASE_ID = 'Phase 6b'
    NAME = 'Attendance'
    REQUIRES_SOURCE = ('hr_attendance_multi_rfid',)
    # Asked about, not required: the daily roll-ups come from this module and
    # have their own switch, which can only be on if the source is known to
    # keep them.
    PROBE_SOURCE = ('hr_attendance_late',)
    REQUIRES_TARGET = ('hr.attendance',)
    OPTION = ''
    OPTION_ANY = ('import_attendance', 'import_attendance_extra')
    WEIGHT = 7

    def run(self, wizard):
        """Execute Phase 6b.

        Through ``steps`` so the two are independent. They were called one
        after the other, and on an Odoo 14 source - where hr_attendance_late
        keeps no daily roll-up model at all - the second one raised on its
        first line and the phase savepoint took the FIRST one's rows with it:
        196 659 attendances read, written and thrown away, reported as one
        red line. One step failing must never cost another step's work.
        """
        steps = []
        if self.b.options.get('import_attendance'):
            steps.append(self._import_attendance)
            steps.append(self._settle_attendance_figures)
        if self.b.options.get('import_attendance_extra'):
            steps.append(self._import_attendance_extra)
        return self.steps(*steps)

    def _import_attendance(self):
        """Step 36: hr.attendance - Direct SQL batch."""
        start = time.time()
        model = 'hr.attendance'
        table = 'hr_attendance'

        source_fields_info = self.b._get_source_fields(model)
        # Real columns only - a non-stored field in a raw INSERT is an
        # UndefinedColumn that kills the whole step.
        target_fields = self.b._target_columns(model)

        fields_to_read = ['employee_id', 'check_in', 'check_out']
        # in_zone_id added by rfid_service module
        if 'in_zone_id' in source_fields_info and 'in_zone_id' in target_fields:
            fields_to_read.append('in_zone_id')
        if 'out_zone_id' in source_fields_info and 'out_zone_id' in target_fields:
            fields_to_read.append('out_zone_id')

        # Attendance belongs to the employee's company. Reading globally and
        # dropping foreign rows in the loop reported the WHOLE source as this
        # company's source_count, so "no attendance for this client" and
        # "every row was dropped" looked identical in the protocol.
        cursor_key = ATTENDANCE_CURSOR
        source_records = self.b._read_all(
            model, self.b._scoped_domain('employee_id'), fields_to_read,
            cursor_key, batch_size=5000)
        imported = 0
        already = 0
        rejected = 0
        skipped = 0

        # date is a stored computed field in v19 (from check_in + tz)
        # We must include it in SQL INSERT since it's required
        has_date_col = 'date' in target_fields
        columns = ['employee_id', 'check_in', 'check_out']
        # Carried attendance is the machine's, not a person's: it came from
        # the other system's own door events. A raw INSERT bypasses the ORM
        # default, so the stamp is written here - without it every carried
        # record reads as typed in by hand, and a rebuild of that period both
        # refuses to replace them and treats them as somebody's word.
        stamps_origin = 'in_mode' in target_fields
        if stamps_origin:
            columns.append('in_mode')
        if has_date_col:
            columns.append('date')
        if 'in_zone_id' in fields_to_read:
            columns.append('in_zone_id')
        if 'out_zone_id' in fields_to_read:
            columns.append('out_zone_id')

        rows = []
        src_ids = []
        zones = {}
        for rec in source_records:
            emp_target = self.b._map_m2o('hr.employee', rec.get('employee_id'))
            if not emp_target:
                skipped += 1
                continue

            check_in = rec['check_in']
            row = [
                emp_target,
                check_in,
                rec.get('check_out') or None,
            ]
            if stamps_origin:
                row.append('rfid')
            if has_date_col:
                row.append(self._attendance_date(emp_target, check_in, zones))
            if 'in_zone_id' in columns:
                zone_target = self.b._map_m2o('hr.rfid.zone', rec.get('in_zone_id'))
                row.append(zone_target or None)
            if 'out_zone_id' in columns:
                zone_target = self.b._map_m2o('hr.rfid.zone', rec.get('out_zone_id'))
                row.append(zone_target or None)

            rows.append(tuple(row))
            src_ids.append(rec['id'])

        page_ids = list(src_ids)
        rows, src_ids, same, differs = self._leave_out_stays_recorded_here(
            columns, rows, src_ids)

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported, already, rejected = self.b._direct_sql_insert_tracked(
                        table, columns, rows, model, src_ids)
            except Exception as e:
                _logger.error("Failed to insert attendance: %s", e, exc_info=True)
                self.b.rewind_cursors(cursor_key)
                self.results.append(self.b._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        # Only now that the page has landed, as accumulate() asks.
        self._remember_left_out(page_ids, same, differs)
        note = self._differs_note()
        self.results.append(self.b.accumulated_result(
            cursor_key, model, len(source_records), imported,
            already + len(same), skipped + len(differs),
            duration=time.time() - start, rejected_count=rejected,
            # Partly, never "none of it came across": stays kept here on
            # purpose are not records that fell through.
            status='partial' if note else 'done', error=note,
        ))

    def _leave_out_stays_recorded_here(self, columns, rows, src_ids):
        """Leave out every stay core would refuse beside what is recorded here.

        The rows go in with SQL, past core's own guard against two stays of a
        person at one time (hr.attendance._check_validity), and nothing in the
        table refuses them. Customer case, 23.10.2026: a second transfer from
        an older copy of the other system would have laid 11 116 of its stays
        over the ones this system had rebuilt from the door events for the
        same months - 9 808 of them the same to the second, every one a day
        counted twice in hours and pay.

        What is recorded here stays as it is (owner's decision, 23.10.2026):
        the record here is what people have been working with since. A stay
        the same to the second is already here, and is counted so. A stay that
        differs is left out and remembered, with both times, for the people
        who keep the records to look at. A row this transfer brought over
        before is not looked at: it is already here as itself.

        Stays of the same read are held to the same rule against each other,
        in the order the other system recorded them: two of its own that
        overlap would otherwise both arrive.

        Returns the rows and source ids to insert, then the stays already here
        and the stays left out, both by source id as kept under SAME_HERE_KEY
        and DIFFERS_KEY.
        """
        done = self.b.already_imported('hr.attendance', src_ids)
        emp_at = columns.index('employee_id')
        in_at = columns.index('check_in')
        out_at = columns.index('check_out')
        to_datetime = fields.Datetime.to_datetime
        to_string = fields.Datetime.to_string
        pending = [(row, sid, to_datetime(row[in_at]), to_datetime(row[out_at]))
                   for row, sid in zip(rows, src_ids, strict=True) if sid not in done]
        if not pending:
            return rows, src_ids, {}, {}
        people = sorted({row[emp_at] for row, *_rest in pending})
        here = self._stays_recorded_here(people, pending)
        companies = self._companies_of(people)
        taken = {}
        same, differs = {}, {}
        for row, sid, start, stop in pending:
            person = row[emp_at]
            company = companies.get(person) or 0
            others = here.get(person, []) + taken.get(person, [])
            # Keyed as text: the totals are stored as JSON, whose keys are text.
            if (start, stop) in others:
                # Asked before the rule: a stay that begins and ends at one
                # moment collides with nothing, not even with its own twin.
                same[str(sid)] = company
                continue
            clash = [other for other in others if refused_beside(start, stop, *other)]
            if not clash:
                taken.setdefault(person, []).append((start, stop))
                continue
            other_start, other_stop = clash[0]
            differs[str(sid)] = [
                person, company,
                to_string(start), stop and to_string(stop),
                to_string(other_start), other_stop and to_string(other_stop),
            ]
        if not same and not differs:
            return rows, src_ids, same, differs
        kept = [(row, sid) for row, sid in zip(rows, src_ids, strict=True)
                if str(sid) not in same and str(sid) not in differs]
        return [row for row, _sid in kept], [sid for _row, sid in kept], same, differs

    def _stays_recorded_here(self, people, pending):
        """{person: [(check-in, check-out)]} of what this system holds near them.

        Every stay of those people that can collide with a row of the page,
        earliest first: one that ends after the page's earliest moment and
        begins before its latest, and every open one, wherever it began. A
        page that holds an open stay has no latest moment - that stay holds
        all the time after it. A row whose check-out is before its check-in
        (old data) is counted by both of its moments.
        """
        earliest = min(min(start, stop) if stop else start
                       for _row, _sid, start, stop in pending)
        ends = [max(start, stop) if stop else None
                for _row, _sid, start, stop in pending]
        before_the_latest = (SQL("") if None in ends
                             else SQL("AND check_in <= %s", max(ends)))
        self.env['hr.attendance'].flush_model(['employee_id', 'check_in', 'check_out'])
        self.env.cr.execute(SQL(
            """
            SELECT employee_id, check_in, check_out
              FROM hr_attendance
             WHERE employee_id = ANY(%s)
               AND (check_out IS NULL OR (check_out >= %s %s))
             ORDER BY check_in, id
            """, people, earliest, before_the_latest,
        ))
        here = {}
        for person, start, stop in self.env.cr.fetchall():
            here.setdefault(person, []).append((start, stop))
        return here

    def _companies_of(self, people):
        """{person: company} here, read once for a page."""
        self.env.cr.execute(SQL(
            "SELECT id, company_id FROM hr_employee WHERE id = ANY(%s)", people))
        return dict(self.env.cr.fetchall())

    def _remember_left_out(self, page_ids, same, differs):
        """Put a landed page's verdicts into the transfer's running totals.

        By source id, and every id of the page loses its earlier verdict
        first: a page read again - after a write that failed, which sends the
        read back to the start - replaces what it said the first time instead
        of saying it twice, and a stay that arrives now is no longer listed.
        """
        totals = self.b.step_totals.setdefault(ATTENDANCE_CURSOR, {})
        judged = {str(sid) for sid in page_ids}
        # New objects, not the old ones changed: progress_snapshot copies one
        # level deep, and a step that is undone must get the old ones back.
        for key, verdicts in ((SAME_HERE_KEY, same), (DIFFERS_KEY, differs)):
            earlier = totals.get(key) or {}
            if verdicts or judged & earlier.keys():
                totals[key] = {**{sid: value for sid, value in earlier.items()
                                  if sid not in judged}, **verdicts}

    def _differs_note(self):
        """The protocol's word on the stays left out, over the whole transfer."""
        differs = self.b.step_totals.get(ATTENDANCE_CURSOR, {}).get(DIFFERS_KEY)
        if not differs:
            return ''
        first = {}
        for person, _company, check_in, *_rest in differs.values():
            first[person] = min(first.get(person) or check_in, check_in)
        known = people_by_id(self.env, first)

        def named(person):
            """Name and first day, the day as the person lived it."""
            employee = known.get(person)
            moment = utc.localize(fields.Datetime.to_datetime(first[person]))
            tz = self._person_tz(employee) if employee else utc
            return self.env._(
                "%(name)s from %(day)s",
                name=employee.name if employee else '#%s' % person,
                day=format_date(self.env, moment.astimezone(tz).date()),
            )

        shown = self.b.first_few(sorted(first), named, PEOPLE_NAMED)
        return self.env._(
            "%(count)s stay(s) of the other system were not brought over: this "
            "system already has a different stay recorded for the same person "
            "at that time, and that one stays as it is. %(who)s. The "
            "downloaded protocol lists every one of them with both times, to "
            "be looked at.",
            count=len(differs), who=shown,
        )

    @staticmethod
    def _person_tz(employee):
        """The zone core cuts this person's overtime days and weeks in.

        The person's own (hr_attendance.py:273, _get_overtimes_to_update_domain;
        :686, _get_localized_times), and so the zone of every day the set
        reads (hr_attendance_multi_rfid, hr.employee._local_tz) - which this
        module cannot call, as it does not depend on it.
        """
        return timezone(employee.sudo().tz or 'UTC')

    def _attendance_date(self, employee_id, check_in, zones):
        """The date core gives an attendance that began at this moment.

        The column is core's own, so it is filled by core's rule for it
        (odoo/addons/hr_attendance/models/hr_attendance.py:90, _compute_date:
        the check-in read in ``employee._get_tz()``), and a record carried
        over reads exactly like one the doors made. The UTC date written here
        before filed a stay begun between 00:00 and 03:00 in Sofia under the
        day before.

        :param zones: {employee id: timezone}, filled as people come up, so a
                      page of thousands of rows asks once per person
        """
        if not check_in:
            return None
        if employee_id not in zones:
            zones[employee_id] = timezone(
                self.env['hr.employee'].browse(employee_id).sudo()._get_tz())
        moment = fields.Datetime.to_datetime(check_in)
        return utc.localize(moment).astimezone(zones[employee_id]).date()

    def _settle_attendance_figures(self):
        """Give the transferred attendance the figures the ORM would have.

        The step above inserts with SQL for speed, so nothing computed the
        stored figures: worked hours stayed empty and core's overtime run
        never ran. Customer case, 12.10.2026: after a transfer more than half
        of the closed attendances read 0 hours worked, and about a third had
        regular hours that were not worked minus extra.

        A step of its own, run once the read is finished: a fault here must
        not take back attendance that has already landed, and a person's
        figures are worked out once over all of their rows, not again for
        every page. Where it got to and what it could not do travel with the
        cursors, so a pass that runs out of time carries on from there, and a
        person it could not figure is still named when a later pass re-enters
        the phase and writes the protocol lines again.

        Whose: the people this source brought across (by their external IDs)
        into the companies of THIS transfer, and every attendance of theirs
        whose figures do not hold, whatever its date - a new transfer over an
        earlier one puts the old rows right too.
        """
        if not self.b.read_is_finished(ATTENDANCE_CURSOR):
            return
        start = time.time()
        if not self.b.read_is_finished(FIGURES_KEY):
            self._settle_people()
        self.results.append(self._figures_result(time.time() - start))

    def _settle_people(self):
        """Work through the people whose figures do not hold, as time allows.

        One person at least per pass, then only while the pass has time: the
        cost of a person is their history, and a pass that overruns is cut
        off with nothing saved.
        """
        Attendance = self.env['hr.attendance'].with_context(**IMPORT_CONTEXT)
        Employee = self.env['hr.employee'].with_context(active_test=False)
        settled_one = False
        while True:
            employee_id = self._next_person_to_settle(
                self.b.read_cursors.get(FIGURES_KEY, 0))
            if not employee_id:
                self.b.read_cursors[FIGURES_KEY] = self.b.CURSOR_FINISHED
                return
            if settled_one and self.b.time_is_up and self.b.time_is_up():
                self.b.stopped_early = True
                return
            if not self._settle_person(Attendance, Employee.browse(employee_id)):
                # Somebody else is writing this person's attendance right now
                # - a door event, say. They wait for the next pass instead of
                # being reported as a problem in their days; the run returns
                # to an unfinished phase (import_run._process_pass).
                _logger.info(
                    "Hours worked of employee %s wait for the next pass: their "
                    "attendance is being written by another process", employee_id)
                self.b.stopped_early = True
                return
            self.b.read_cursors[FIGURES_KEY] = employee_id
            settled_one = True

    def _next_person_to_settle(self, after):
        """The next person of this transfer whose figures do not hold.

        Brought across from this source (external ID) AND in one of the
        companies this transfer writes into: the same source read earlier for
        another company is another tenant's transfer, not this one's.
        """
        prefix = self.b._xml_id_name('hr_employee', '')
        companies = sorted({cid for cid in self.b.company_map.values() if cid})
        self.env.cr.execute(SQL(
            """
            SELECT a.employee_id
              FROM hr_attendance a
              JOIN hr_employee emp ON emp.id = a.employee_id
              JOIN ir_model_data d
                ON d.model = 'hr.employee' AND d.res_id = a.employee_id
               AND d.module = %(module)s
               AND left(d.name, %(length)s) = %(prefix)s
             WHERE a.employee_id > %(after)s
               AND emp.company_id = ANY(%(companies)s)
               AND a.check_out IS NOT NULL
               AND (a.worked_hours IS NULL OR %(disagrees)s)
             ORDER BY a.employee_id
             LIMIT 1
            """,
            module=EXTERNAL_ID_MODULE, length=len(prefix), prefix=prefix,
            after=after, companies=companies, disagrees=REGULAR_HOURS_DISAGREE,
        ))
        row = self.env.cr.fetchone()
        return row and row[0]

    def _settle_person(self, Attendance, employee):
        """Put one person's figures right. False when their rows are busy.

        Core's overtime run deletes and recreates every overtime line in the
        range it is given, and a recreated line loses the manager's decision
        on it (hr_attendance.py, _update_overtime; hr_attendance_overtime.py,
        _compute_status). It also needs the person's schedule, which core has
        only inside a version (hr_employee.py, _get_version_periods): before
        the first version it counts the WHOLE day as approved extra time
        (measured: 08:00-17:00 read 9 extra and -1 regular, also for a day
        entered by hand). Core's own "Regenerate overtimes" therefore never
        reaches before the version (hr_attendance_overtime_ruleset.py,
        _attendances_to_regenerate_for), and on a transferred database the
        versions begin at the transfer while the history runs years back. So
        the rows are cured three ways:

        - worked hours present, regular hours disagreeing: only the regular
          hours are recomputed, and the overtime lines are left alone;
        - no worked hours, before the first version: the hours are worked out
          (``modified`` on the two times, the way core marks a record whose
          times changed, as l10n_gcc_invoice/models/account_move.py:61 does
          after its own raw update) and nothing else - no rules apply there,
          exactly as core's button leaves them;
        - no worked hours, inside a version: the same, and core's overtime run
          follows, as after every create. It gets one run of such rows at a
          time, cut at every row that has its hours and at every local week,
          so a day that was right - approved or refused - between them is
          never in its range. A day or a week that holds both kinds is worked
          out again as a whole, as core does whenever a stay of it changes.

        Regular hours are marked in all three, because core marks them in its
        overtime run only since odoo/odoo 17577a1f9c6 (in 19.0 since
        30.03.2026), and the transfer target is often an older server. Each
        unit has its own savepoint, so what one of them refuses costs only
        that unit.
        """
        disagreeing, before, runs = self._figures_to_settle(employee)
        units = [(disagreeing, False, False)] if disagreeing else []
        units += [(before, True, False)] if before else []
        units += [(run, True, True) for run in runs]
        for rows, mark, regenerate in units:
            attendances = Attendance.browse(row[0] for row in rows)
            try:
                with self.env.cr.savepoint():
                    if mark:
                        attendances.modified(FIGURES_TIMES)
                    if regenerate:
                        attendances._update_overtime()
                    self.env.add_to_compute(
                        Attendance._fields['expected_hours'], attendances)
                    Attendance.env.flush_all()
            except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
                return False
            except FIGURES_DATA_ERRORS as exc:
                _logger.warning(
                    "Hours worked of %s attendances of employee %s from %s "
                    "could not be worked out", len(rows), employee.id,
                    rows[0][1], exc_info=True)
                self._note_unfigured(employee, rows, exc)
                self.b.accumulate(FIGURES_KEY, found=len(rows))
                continue
            self.b.accumulate(FIGURES_KEY, found=len(rows), settled=len(rows))
        return True

    def _figures_to_settle(self, employee):
        """This person's rows whose figures do not hold, split by their cure.

        Returns ``(disagreeing, before, runs)`` of ``(id, check_in)`` rows:
        those with worked hours whose regular hours disagree; those without
        worked hours from before the person's first version; and those without
        worked hours inside a version, cut into runs - each within one local
        week (core's weeks, MO-SU in the person's zone), with no row between
        its first and its last that has its hours.
        """
        tz = self._person_tz(employee)
        earliest = employee.sudo().with_context(active_test=True).version_ids.sorted('date_start')[:1]
        first = None
        if earliest:
            # The first moment core has a schedule for this person: midnight of
            # the first version's start in that version's working hours, or in
            # the person's own zone without them (hr_employee.py:1627-1628,
            # _get_version_periods) - not the zone of the weeks below.
            version_tz = timezone(earliest.resource_calendar_id.tz
                                  if earliest.resource_calendar_id
                                  else earliest.employee_id.resource_id.tz or 'UTC')
            first = version_tz.localize(datetime.combine(
                earliest.date_start, day_start.min)).astimezone(utc).replace(tzinfo=None)
        self.env.cr.execute(SQL(
            """
            SELECT a.id, a.check_in, a.worked_hours IS NULL, %s
              FROM hr_attendance a
             WHERE a.employee_id = %s AND a.check_out IS NOT NULL
             ORDER BY a.check_in, a.id
            """, REGULAR_HOURS_DISAGREE, employee.id,
        ))
        disagreeing, before, runs, run = [], [], [], []
        for att_id, check_in, unfigured, disagrees in self.env.cr.fetchall():
            week = utc.localize(check_in).astimezone(tz).isocalendar()[:2]
            # A run ends at a row that has its hours, and where the week changes.
            if run and (not unfigured or week != run[-1][2]):
                runs.append([row[:2] for row in run])
                run = []
            if not unfigured:
                if disagrees:
                    disagreeing.append((att_id, check_in))
            elif first is None or check_in < first:
                before.append((att_id, check_in))
            else:
                run.append((att_id, check_in, week))
        if run:
            runs.append([row[:2] for row in run])
        return disagreeing, before, runs

    def _note_unfigured(self, employee, rows, exc):
        """Remember, with the cursors, whose figures could not be worked out."""
        totals = self.b.step_totals.setdefault(FIGURES_KEY, {})
        # A new dict, not the old one changed: progress_snapshot copies one
        # level deep, and a step that is undone must get the old one back.
        failed = dict(totals.get('failed') or {})
        # Keyed as text: the totals are stored as JSON, whose keys are text.
        key = str(employee.id)
        known = failed.get(key) or {}
        # The day as the person lived it, not the server's UTC date.
        day = utc.localize(rows[0][1]).astimezone(
            self._person_tz(employee)).date().isoformat()
        # An exception may carry no text at all (a bare ValueError()); its
        # kind is then the only thing to say, and failing here would lose the
        # person instead of naming them.
        said = str(exc).strip().splitlines() or [type(exc).__name__]
        failed[key] = {
            'records': known.get('records', 0) + len(rows),
            'day': min(known.get('day') or day, day),
            'problem': known.get('problem') or said[0][:160],
        }
        totals['failed'] = failed

    def _figures_result(self, duration):
        """The protocol line for the hours worked, over the whole transfer."""
        totals = self.b.step_totals.get(FIGURES_KEY, {})
        found, settled = int(totals.get('found', 0)), int(totals.get('settled', 0))
        failed = totals.get('failed') or {}
        label = self.env._("Worked Hours")
        if not failed:
            return self.b._make_result(label, found, settled, duration=duration)
        return self.b._make_result(
            label, found, settled, duration=duration, status='partial',
            error=self.env._(
                "Hours worked could not be worked out for %(records)s "
                "attendance(s) of %(who)s. Put those days right, then run the "
                "transfer again with only \"Import attendance\" ticked.",
                records=sum(entry['records'] for entry in failed.values()),
                who=self._name_unfigured(failed),
            ))

    def _name_unfigured(self, failed):
        """Who, from which day, and what the system said - the first few."""
        known = people_by_id(self.env, (int(employee_id) for employee_id in failed))

        def said(item):
            employee_id, entry = item
            person = known.get(int(employee_id))
            return self.env._(
                "%(name)s from %(day)s: %(problem)s",
                name=person.name if person else '#%s' % employee_id,
                day=format_date(self.env, entry['day']),
                problem=entry['problem'],
            )

        return self.b.first_few(sorted(failed.items()), said, PEOPLE_NAMED)

    def _drop_days_already_summed_here(self, columns, rows, src_ids):
        """Leave out the days this system has already summed up itself.

        The daily figures are produced HERE too, by this system's own scheduled
        job, for whichever days it can see - and after a transfer it can see
        the days it has just received. So the most recent days end up with two
        rows for one person: the one that came across and the one worked out
        here. Nothing refuses it (there is no unique index), and a day with two
        rows is a day counted twice in every report over it. Measured while
        moving a 27-tenant cloud: 10 such days, all of them yesterday and
        today.

        The row already here is left alone rather than replaced: it was worked
        out from the attendances of a day that may still be running, and
        replacing it with a figure taken before midnight would be the same
        double bookkeeping in reverse.
        """
        if not rows or 'for_date' not in columns:
            return rows, src_ids, 0
        emp_at = columns.index('employee_id')
        date_at = columns.index('for_date')
        shift_at = columns.index('shift_number') if 'shift_number' in columns else None

        def day_key(employee, day, shift):
            """One shape for both sides of the comparison.

            The two sides arrive in DIFFERENT types and that is the whole
            trap: the other system hands its date over the wire as the text
            '2026-08-16', while reading our own table gives a date object, and
            a shift left unset is False here and 0 there. Compared as they
            come, the key never matches, no day is ever recognised as already
            summed, and this guard quietly does nothing at all - which is
            precisely what a review of it found before the second live run
            could hide it again.
            """
            if isinstance(employee, (list, tuple)):
                employee = employee[0]
            return (employee, fields.Date.to_date(day) if day else None,
                    int(shift or 0) if shift_at is not None else None)

        employees = {row[emp_at] for row in rows}
        dates = {row[date_at] for row in rows if row[date_at]}
        if not employees or not dates:
            return rows, src_ids, 0
        here = self.env['hr.attendance.extra'].sudo().search_read(
            [('employee_id', 'in', list(employees)),
             ('for_date', 'in', list(dates))],
            ['employee_id', 'for_date', 'shift_number'])
        taken = {day_key(rec['employee_id'], rec['for_date'],
                         rec.get('shift_number'))
                 for rec in here}
        kept_rows, kept_ids, dropped = [], [], 0
        for row, source_id in zip(rows, src_ids):
            key = day_key(row[emp_at], row[date_at],
                          row[shift_at] if shift_at is not None else None)
            if key in taken:
                dropped += 1
                continue
            kept_rows.append(row)
            kept_ids.append(source_id)
        return kept_rows, kept_ids, dropped

    def _import_attendance_extra(self):
        """Step 37: hr.attendance.extra - Direct SQL batch.

        Model from hr_attendance_late module (NOT hr_attendance_multi_rfid!).
        """
        start = time.time()
        model = 'hr.attendance.extra'
        table = 'hr_attendance_extra'

        if not self.b._has_model(model):
            # Odoo 14 ships hr_attendance_late without the daily roll-up
            # model - it only extends hr.attendance there. "That system keeps
            # no such thing" is not a failure, and saying so is not optional:
            # a step that returns nothing without a line reads exactly like a
            # step that ran and found no data.
            self.results.append(self.b._make_result(
                model, 0, 0, status='skipped',
                error=self.env._(
                    "The other system does not keep daily working-time "
                    "roll-ups - it only records the attendances themselves, "
                    "which came across above."),
                duration=time.time() - start,
            ))
            return

        source_fields_info = self.b._get_source_fields(model)
        # Real columns only - a non-stored field in a raw INSERT is an
        # UndefinedColumn that kills the whole step.
        target_fields = self.b._target_columns(model)

        fields_to_read = ['employee_id', 'department_id']
        # What a day of work actually says: hours worked, day and night,
        # against what was owed, plus lateness, early leaving and overtime.
        # The names are the ones both versions really use - a live 15 and this
        # 19 agree on all sixteen. The previous list asked for 'check_in',
        # 'check_out', 'late_minutes', 'early_leave_minutes',
        # 'overtime_minutes' and 'worked_hours', which exist in NEITHER, so
        # even when the step ran, every roll-up arrived as an empty shell -
        # a person and a date, and not one of the numbers the record is for.
        # 'for_date' is NOT NULL in the target - it must be read and written,
        # otherwise every batch is rejected and no extra record migrates at all.
        for f in EXTRA_OPTIONAL_FIELDS:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)

        cursor_key = 'attendance:%s' % model
        source_records = self.b._read_all(
            model, self.b._scoped_domain('employee_id'), fields_to_read,
            cursor_key, batch_size=5000)
        imported = 0
        already = 0
        rejected = 0
        skipped = 0

        columns = ['employee_id', 'department_id']
        for f in fields_to_read:
            if f not in columns:
                columns.append(f)

        rows = []
        src_ids = []
        for rec in source_records:
            emp_target = self.b._map_m2o('hr.employee', rec.get('employee_id'))
            if not emp_target:
                skipped += 1
                continue
            dept_target = self.b._map_m2o('hr.department', rec.get('department_id'))

            row = [emp_target, dept_target or None]
            for f in columns[2:]:
                row.append(rec.get(f) if rec.get(f) is not False else None)

            rows.append(tuple(row))
            src_ids.append(rec['id'])

        rows, src_ids, ours = self._drop_days_already_summed_here(
            columns, rows, src_ids)
        if ours:
            self.b.note_skip_reason(self.env._(
                "%(count)s day(s) had already been worked out here - the "
                "figures this system produced for them are kept, so a day is "
                "not counted twice", count=ours))
        skipped += ours

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported, already, rejected = self.b._direct_sql_insert_tracked(
                        table, columns, rows, model, src_ids)
            except Exception as e:
                _logger.error("Failed to insert attendance extra: %s", e, exc_info=True)
                self.b.rewind_cursors(cursor_key)
                self.results.append(self.b._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self.b.accumulated_result(
            cursor_key, model, len(source_records), imported, already, skipped,
            duration=time.time() - start, rejected_count=rejected,
        ))
