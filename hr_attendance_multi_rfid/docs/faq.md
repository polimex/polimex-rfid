## The day is the person's own

Every daily figure of the attendance set - the day a stay is filed under, the
schedule it is judged by, the night hours, an absence, the holiday rate, the
days of Form 76, the days a rebuild clears - reads the day in the employee's
own **Timezone** (employee form, *Settings* tab), through one method:
`hr.employee._local_tz()`.

Why that zone. Core 19 cuts the days of its overtime, and reads the hours a
day is worth, in the employee's own zone (`hr_attendance.py:686`,
`_get_localized_times`, whose version zone is the employee's;
`hr_employee.py:1792`, `_get_expected_attendances`). Odoo 20 removes the zone
of working hours and reads everything in the employee's zone. The only place
core 19 differs is the stored date of an attendance record
(`hr_attendance.py:90`), which goes through `_get_tz()` - the working hours'
zone first. The two agree unless an employee's zone and their schedule's zone
are set differently; check that both say the same.

What it changes for people working in Sofia, two or three hours ahead of UTC:

- a stay begun between midnight and 02:00 (03:00 in summer) belongs to that
  morning, not to the evening before, and is judged by that morning's
  schedule;
- night work (22:00-06:00) is counted by the clock of the day worked, also
  when a winter day is recomputed in summer;
- a day with no badge is an absence only once it is over for the person;
- the eve of a public holiday is not paid at the holiday rate;
- a day the clocks change is 23 or 25 hours long, and its schedule does not
  borrow an hour of the next day.

Daily rows computed before this rule keep their figures until the day is
computed again - **Recompute Extra Attendance** for the period does it.

## Regenerating overtime keeps the day's figures right

`hr.attendance._update_overtime` is extended so that core's overtime run leaves
every figure of the affected days consistent with core's own formulas:

- Attendance written past the ORM (a transfer inserting with SQL) has no
  `worked_hours`; core's overtime run reads only the times and never fills
  them. Before calling core, the records with a check-out and no worked hours
  get `modified(['check_in', 'check_out'])` - the two fields
  `_compute_worked_hours` depends on, the idiom core uses after its own raw
  updates (l10n_gcc_invoice/models/account_move.py:61).
- After core's run, `expected_hours` (stored, worked minus overtime) is
  marked for recomputation on every attendance of the run. Core does this
  itself only since odoo/odoo 17577a1f9c6 (in 19.0 since 30.03.2026); on an
  older server a day built record by record kept stale regular hours. On a
  newer server it is the same mark twice, which is why the test for this
  shape passes on this tree with or without the module.

Core's **Regenerate overtimes** button on the ruleset
(`action_regenerate_overtimes`) runs this method. It reaches from the earliest
`date_version` of ALL versions that carry the ruleset, for every employee on
it (`hr_attendance_overtime_ruleset.py`, `_attendances_to_regenerate_for`) -
not from each employee's own version. Core deletes and recreates every
overtime line of that period, and a recreated line takes its default status
(`hr_attendance_overtime.py`, `_compute_status`), so approvals and refusals in
the period have to be given again - core's behaviour, not changed here. The
user guide says so before telling anyone to press it. History older than that
is out of the button's reach by core's design; a transfer repairs its own
history when it runs again (hr_rfid_odoo_import, "Worked Hours"), hands core
only the days that are wrong, and gives days before a person's first version
their hours without overtime.

Customer case (12.10.2026): after a transfer more than half of the closed
attendances read 0 hours worked, and about a third had regular hours that
were not worked minus extra.

Tests: `tests/test_regenerate_puts_figures_right.py`
(tag `rfid_attendance_figures`).

## Rebuilding attendance: the background job

### Why it is a job and not a click

Rebuilding one person means deleting their attendance for a period and
replaying every door event in it; a site has hundreds of people. Inside the
request the operator pressed, that is cut off at `limit_time_real` (120 s by
default), leaving attendance half deleted and never rebuilt. The scheduler
thread is NOT exempt: `limit_time_real_cron` only replaces the limit when it is
positive, and exceeding it **restarts the server** rather than merely stopping
the job. Hence `PASS_SECONDS` - a safety parameter.

One employee is the unit of work because the clear-and-replay is only
consistent as a whole. Each person ends in `_save_progress`, which writes the
resume cursor and calls `ir.cron._commit_progress(processed=1, remaining=N)` -
committing, and telling core how much is left so it reschedules itself instead
of computing zero remaining and calling the job done.

### Refusing a rebuild: `hr.employee._check_recalc_allowed`

The hook is DECLARED in `hr_rfid` (`models/hr_employee.py`), not here, and that
placement is load-bearing: Odoo composes one class per model from every add-on
that extends it, last loaded outermost, and two unrelated add-ons that both
declared the method would be in no fixed order - the one that only allows would
silently cancel the one that refuses. Declared in the module underneath both,
it cannot be cancelled that way.

- An override MUST call `super()` FIRST, or every objection underneath is lost.
- Raise `UserError` with an operator-readable reason to refuse; return to allow.
- It is asked at three points, deliberately: in the wizard (so a refusal lands
  on the screen the operator is looking at), in `_run_one_employee` (so one
  refused person does not stop the rest), and again inside
  `_recalc_attendance_one` (a rebuild may become forbidden while it is queued,
  and every programmatic caller passes through there).

`hr_rfid_odoo_import` is the implementer: attendance carrying the transfer's
external ID cannot be worked out again here, and rebuilding would delete the
record together with the metadata row that identifies it, so the next transfer
would no longer recognise it and would bring it over a second time.

A refusal is NOT a failure and the two are told apart by exception TYPE, never
by message text (which stops working the moment it is translated):
`AccessError` -> `error` line + `failed`; `UserError` -> `refused` line, logged
at INFO with no traceback, reason kept whole and posted through
`plaintext2html` so its paragraphs survive.

### Five outcomes, not two

`done`, `no_events`, `no_result`, `refused`, `error` per person; `done`,
`nothing`, `refused`, `failed` for the run. `no_result` exists because a period
that was cleared and produced no attendance reads as "Rebuilt" under a two-way
status and is never looked at again - the operator finds out at the end of the
month when payroll does not add up.

`done_count` counts everybody got through, including no-ops and failures; the
number actually rebuilt is in the closing message. The label says so ("People
dealt with") rather than the counter being narrowed, because a progress bar
whose numerator counted only successes would sit at 67% for ever on a finished
run.

### Tests

`tests/test_recalc_background.py` (lifecycle, resume, outcomes),
`tests/test_recalc_security.py` (officer vs manager, company isolation),
`hr_rfid/tests/test_recalc_hook.py` (the hook allows by default),
`hr_rfid_odoo_import/tests/test_recalc_guard.py` (the refusal, driven through
the wizard button and through `_cron_process`).


## Where the rules live (the technical names)


This module reads no system parameters. What decides how passages become
attendance is on `hr.rfid.zone`: `attendance`, `overwrite_check_in`,
`overwrite_check_out`. When a stay is a forgotten badge and what it is credited
is core's Automatic Check-Out with the company's `forgotten_badge_policy`, and
per schedule `resource.calendar.forgotten_badge_hours`; a forgotten day is
never credited past the end of the schedule the person came in under. The
tolerances for small deviations are on `hr.department` (hr_attendance_late:
`ignore_late_time`, `ignore_early_come_time`, `ignore_early_leave_time`,
`ignore_overtime`, `ignore_extra_time`) and work on AMOUNTS OF TIME, never on
passages.

## How a person's attendance is rebuilt (`hr.employee`)

- **`recalc_attendance(self, from_date=None, to_date=None)`** - decorators: -
  - Rebuild attendance for this recordset in ONE transaction. Calls
    `_check_recalc_allowed` once (the chokepoint every caller passes through),
    then `_recalc_attendance_one` per employee. Anything larger than a handful
    of people belongs on `hr.attendance.recalc.run` instead.
  - effects: `log_warn`, `with_context`
  - touches: `hr.attendance`, `hr.rfid.event.user`, `hr.rfid.zone`
- **`_recalc_attendance_one(self, from_date, to_date, ctx)`** - decorators: -
  - One employee, the smallest piece that can be committed on its own: the
    period is cleared and replayed as a whole. Asks `_check_recalc_allowed`
    again, because the background job calls this directly and a rebuild may
    have become forbidden while it was queued. Returns
    `{'event_count': N, 'attendance_count': M}` - the numbers the rebuild
    reports per person.
  - A stay with `check_in` before the period and `check_out` in it (or none)
    is not cleared, so it is settled ground: passages inside a closed one are
    skipped (an entry is rewritten `already_inside`, its own exit marked
    `out`), and the latest open rfid one is carried on - the replay starts
    with it as the presence and writes its check-out instead of creating a
    second record. A typed-in stay from before the period joins the
    preserved spans like one inside it. Before this, the entry inside such a
    stay and its exit were replayed into an overlapping record, and core's
    overtime engine raised `Expected singleton` (the person came out
    "Not rebuilt").
  - touches: `hr.attendance`, `hr.rfid.event.user`
- **`_recalc_attendance_context(self)`** - decorators: `@api.model`
  - Resolves once what counts as an attendance door: `{'zones', 'doors',
    'in_readers', 'out_readers'}`. Passed to every `_recalc_attendance_one` of
    a run so the same searches are not repeated per person.
- **`_local_tz(self)`** - decorators: -
  - The zone every day of this person is read in: their own `tz`. The one
    place the set asks it; see "The day is the person's own" below.
- **`_local_day(self, moment)`** - decorators: -
  - The date of this person's calendar a naive-UTC moment falls on.
- **`_local_days_window(self, from_date, to_date)`** - decorators: -
  - The chosen DAYS as the two naive-UTC MOMENTS bounding them, in the
    employee's own timezone, last day included whole (bound is "before", not
    "up to"); each end localized on its own, so a day the clocks change is
    23 or 25 hours long. Both the events replayed and the attendance deleted
    are cut to this window, so no day is cleared that is not also replayed;
    the daily figures, the holiday check and Form 76 read their days through
    it too.
- **`_recalc_clear_domain(self, period_start, period_end)`** - decorators: -
  - **Extension point.** Which of this person's attendance a rebuild may
    remove. Default: everything the system made in the window, never what a
    person typed in - it asks only for records carrying no reason, or the one
    from `_recalc_manual_attendance_reason`.
- **`_recalc_manual_attendance_reason(self)`** - decorators: -
  - **Extension point.** The reason this system puts on attendance it closed
    itself, read from `res.company.hr_attendance_autoclose_reason` when an
    add-on provides that field. Returns `False` where nothing records the
    reason - a typed-in record then cannot be told from a made one, the whole
    period is cleared, and the loss is logged rather than passed over.

#### Settling a forgotten badge

One setting, in one place. **When**: core's `res.company.auto_check_out` +
`auto_check_out_tolerance`, measured against the person's own scheduled day.
**What**: `res.company.forgotten_badge_policy` (`credit_schedule` / `penalty`
/ `ignore`) with `forgotten_badge_penalty_hours`, shown right under the core
switch in Settings -> Attendances. **Per schedule**:
`resource.calendar.forgotten_badge_hours` (Float, 0 = unset, CHECK >= 0;
models/resource_calendar.py, on the schedule form beside the hours, under the
schedule's own access rights) replaces the scheduled day in the policy for the
people on that schedule, capped at that day (`min(number, hours)`). The
schedule is the one of the stay's day, chosen as core's
`hr.employee._get_expected_attendances` chooses it
(`hr.attendance._calendar_of_the_day`: contract version in force, else the
person's, else the company's) - not `hr.attendance._get_employee_calendar`,
which Enterprise's `hr_work_entry_attendance` overrides to read `check_out`.
The policy still applies on top (penalty off the number, `ignore` credits
nothing). Settled stays are not re-credited when the number changes; a rebuild
re-credits them.

`hr.attendance` (models/hr_attendance.py):

- **`forgotten_badge`** (Boolean, indexed) - the system judged this stay a
  forgotten badge. Set under every policy, so they can all be found.
- **`_scheduled_day(self)`** - `(hours, span)` for the day of the check-in,
  from core's `hr.employee._get_expected_attendances`, so leaves, public
  holidays and two-week calendars read as they do everywhere else. `(0, 0)`
  on an unscheduled day - no answer, not a small one.
- **`_max_allowed_stay_hours(self)`** - scheduled hours + the company's
  tolerance; `0.0` when Automatic Check-Out is off or the day was not
  scheduled, and then nothing is ever settled.
- **`_end_of_the_schedule_ahead(self)`** - where the schedule the person came
  in under ends, when that still lay ahead of the check-in: the last scheduled
  minute of the stay's day (`_expected_work_on`, core's intervals, own leave
  taken off). A schedule that reaches midnight and goes straight on the next
  morning is one shift (22:00-06:00 ends at 06:00); a check-in after midnight
  while last evening's shift was still running ends with that shift, the same
  morning. `False` when the check-in is after the schedule's end, on an
  unscheduled day and on a floating schedule (core describes a stand-in
  window around noon for it, `resource_calendar.py:419`). On a schedule that
  runs round the clock the end found is a day or more ahead and holds nothing
  back. Module-level helpers: `reaches_midnight` (a row to 24:00 ends at
  23:59:59.999999 in core, and one typed as 23:59 a minute short:
  `A_SCHEDULE_REACHES_MIDNIGHT_WITHIN`), `work_goes_on_until` (a break the
  schedule declares - core's lunch rows, `_breaks_on` - does not end the
  shift), `last_scheduled_moment`. Only the END
  is read by the shift; whether a stay is forgotten at all is still judged
  by the hours of its calendar day (`_max_allowed_stay_hours`).
- **`_settled_check_out(self)`** - when the stay is taken to have ended:
  check-in + the SPAN of the scheduled day (break included, so a settled day
  is worth a normal one), or, after an earlier stay that day, what is left of
  the day's hours (`_hours_earlier_that_day`); never past
  `_end_of_the_schedule_ahead`, so a forgotten badge-out pays no more than a
  day badged out when the schedule ended (owner's decision, 16.11.2026: in at
  09:07 on an 08:00-17:00 day is credited to 17:00, not 18:07) - counted from
  the check-in alone only where no end of the schedule lies ahead; with the schedule's
  `forgotten_badge_hours` set, that number (at most the day's hours) less the
  earlier stays, ended at the first second core's own count reaches it
  (`_end_after_worked_hours`: core's `_get_worked_hours_in_range` on a probe,
  halving a window of `UNPAID_TIME_A_CREDITED_DAY_MAY_SPAN` when check-in plus
  the hours falls short, so an end inside a break moves past it), the number
  capped as well by what the schedule still held at the check-in
  (`_worth_as_core_counts` up to `_end_of_the_schedule_ahead`);
  less the penalty where the policy
  sets one, and never past `_latest_end_of_stay` (the moment judged, or the
  person's next stay, core's absence marks included, because its overtime engine
  refuses a record across one); `False` when nothing is to be credited.
- **`stay_is_not_credible(self)`** - does the stay run past
  `_max_allowed_stay_hours`? An OPEN stay counts the earlier stays of that day,
  as core's check-out rule does. A CLOSED stay with `in_mode='manual'` is an
  operator's word and is never judged. Honours the `attendance_calc_time`
  context, the module's own clock seam. The comparison itself is the
  module-level `stay_outlasts`, which the rebuild also uses for a stay that has
  no record yet.
- **`autoclose_attendance(self)`** - settles one stay and raises on failure.
  With nothing to credit, an open stay ends at its own check-in and a closed one
  only gets the mark. Writes with `no_validity_check`: the credited end stops at
  the next stay.
- **`_settle_before_new_entry(self, moment)`** - the door's wrapper, called by
  `hr.rfid.zone.person_entered`. Past the limit it settles the stay and returns
  True, and the entry begins a new one. Runs with `from_event` (no zone list or
  anti-passback change), in a savepoint. `SETTLING_REFUSED` (data failures only)
  returns False and the passage stays "Already inside"; concurrency errors reach
  Odoo's retry, for which `hr_rfid/controllers/main.py` passes them on. The
  rebuild calls `autoclose_attendance` directly, so a failure lands on the person
  in `_run_one_employee`.
- **`check_for_incomplete_attendances(self)`** - settles both shapes, oldest
  first, committing each record inside the task (`ir.cron._commit_progress`). The
  over-long CLOSED ones are found by a raw-SQL span query, NOT by
  `worked_hours`: that field is paid time with the unpaid break already
  deducted, so it reads under the limit for a record that spans more than it
  (measured: 1827 real cases, `worked_hours > 24` matched none of them). History
  brought over from another system is settled the same way (owner's decision,
  05.11.2026).
- **`_cron_auto_check_out(self)`** - core's scheduled task, running this sweep and
  NOT core's rule (owner's decision, 05.11.2026): core's rule reads no schedule on
  a day off and closes a person at work after the bare tolerance, credits the
  working day plus the tolerance whatever the Forgotten Badge setting says, and
  writes all its records in one unprotected loop.
- **`write`** - closing a stay with a zone calls `person_left` with
  `stay_being_closed`, which keeps only the zone list and anti-passback part, and
  only when no other stay of the person is open in that zone. A person's write of
  the times clears `forgotten_badge`.
- **`_check_validity`** - core's overlap check, skipped under
  `no_validity_check` (door passages, the rebuild, settling). The override repeats
  `@api.constrains`: without it Odoo does not run the check at all.

`hr.employee._recompute_daily_figures(from_date, to_date)` - hook called by
`_recalc_attendance_one` on every path, including the early return when there
were no events. Empty in `hr_attendance_multi_rfid`; `hr_attendance_late`
overrides it and calls `update_extra_attendance_data(..., overwrite_existing=
True)` for the whole period. Without it only the days whose attendance records
changed were refreshed - measured on a customer copy, 82 of 148 daily rows in
one June kept their old figures after a full rebuild, all of them days with
nothing to replay.

Day ownership (hr_attendance_late/models/hr_employee.py): a day's presence is
the records whose `check_in` falls on that day, counted in full. A record that
started earlier no longer contributes to later days. A record the system would
settle is capped at `_settled_check_out()` while measuring, and skipped
entirely under the `ignore` policy.

Migration `19.0.1.5.0/pre-migrate.py` carries the removed zone hours
(`max_time_in_zone`, `auto_close_time_for_zone`,
`delete_attendance_if_late_more_than`) onto the company: Automatic Check-Out
on, tolerance = zone limit - the company calendar's `hours_per_day`. The same
conversion runs in `hr_rfid_odoo_import`
(`core_importer._carry_forgotten_badge_settings`) when zones come from an
older instance.

## The passage says whether it was counted (`hr.rfid.event.user`)

- **`_mark_attendance(self, direction)`** - this passage IS the check-in / check-out;
  clears `no_attendance_reason` so the two columns cannot contradict each other.
- **`_mark_no_attendance(self, reason)`** - LIVE: records WHY the passage changed
  no attendance, but never over a passage another zone already counted (a door
  can belong to several zones, answered one after another).
- **`_rewrite_no_attendance(self, reason)`** - REBUILD: the same, replacing any
  earlier answer, because a replay is authoritative for its period. Two methods
  rather than one method and a flag: a forgotten flag would have looked like
  nothing at all.
- **`_write_no_attendance(self, reason)`** - the shared write; tolerates the
  empty recordset, so callers need no guard.
- **`button_show_employee_att_events(self)`** - decorators: -
  - effects: `i18n`

Both markers are used by the two machines that turn events into attendance -
`hr.rfid.zone` (live, as people walk through) and
`hr.employee._recalc_attendance_one` (replay) - so the two always tell the
operator the same thing about the same passage.

## The rebuild wizard, the run and its lines

- **`execute(self)`** - decorators: -
  - Writes the request down and hands the screen back: asks
    `_check_recalc_allowed` (so a refusal is shown on the screen the operator
    is looking at, not in a report they must go and find), checks the
    scheduled task is switched on, creates one `hr.attendance.recalc.run` and
    triggers it. Returns a `display_notification` whose `next` opens that run.
  - effects: `raise:UserError`, `raise:RedirectWarning`
  - touches: `hr.attendance.recalc.run`
- **`_check_background_worker_available(self)`** - decorators: -
  - Refuses rather than accepting a request nothing will ever pick up: an
    inactive `ir.cron` drops triggers silently
    (`odoo/addons/base/models/ir_cron.py`), so the run would sit queued for
    ever. `RedirectWarning` to the cron form for `base.group_system`, plain
    `UserError` for anybody else.

### `hr.attendance.recalc.run`
Python class `HrAttendanceRecalcRun` in `models/attendance_recalc_run.py:55`.  Model.  Inherits: `mail.thread`.  Description: *Attendance Rebuild*.  Default order: `create_date desc`.

The permanent half of a rebuild. The wizard is transient and the vacuum removes
it within the hour, which would take the job with it; core splits the same way
(`account.move.send.batch.wizard` transient, `account.move.sending_data`
permanent). Deliberately the same shape as
`hr_rfid_odoo_import/models/import_run.py` - one pattern for long jobs, not two.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char |  |  | ✓ | Computed from the period (`_compute_name`). |
| `state` | Selection |  | ✓ | ✓ | `queued` / `running` / `done` / `nothing` / `refused` / `failed`. Tracked, indexed. |
| `user_id` | Many2one → \`res.users\` | Started by | ✓ | ✓ | Whose rights the work runs with, and who is notified when it ends. |
| `company_id` | Many2one → \`res.company\` | Company | ✓ | ✓ | The company the work runs for (decides which attendance is cleared). |
| `date_from` | Date | From | ✓ | ✓ | First day rebuilt. |
| `date_to` | Date | To | ✓ | ✓ | Last day rebuilt, included whole. |
| `employee_ids` | Many2many → \`hr.employee\` | Employees | ✓ | ✓ | The list as chosen; changing it mid-run applies from the next person on. |
| `processed_employee_id` | Integer |  |  | ✓ | Resume cursor - the last id finished. Monotone, index-backed. |
| `current_employee_id` | Many2one → \`hr.employee\` | Working on |  | ✓ | Who is being rebuilt right now. |
| `done_count` | Integer | People dealt with |  | ✓ | Everybody got through, INCLUDING no-op and failed people - not "succeeded". |
| `total_count` | Integer | People in total |  | ✓ | Size of the list. |
| `progress` | Integer |  |  | - | `done_count * 100 / total_count`. |
| `log_ids` | One2many → \`hr.attendance.recalc.log\` | What happened |  | ✓ | One line per person. |

#### Notable methods

- **`action_start(self)`** - the "Continue now" button; sets `queued` and wakes the cron.
- **`_cron_process(self)`** - decorators: `@api.model`
  - One pass. Called from a request (the button) it only re-triggers the cron -
    doing the work inside the HTTP request would hit `limit_time_real`. Closes
    stalled runs first and **commits that** before starting a pass, because the
    pass rolls back on failure and would otherwise undo exactly the closures
    that unblock the queue. A pass that raises is caught, rolled back and the
    run ends `failed` - otherwise the oldest run is picked again on every
    wake-up and blocks every later one.
- **`_process_pass(self)`** - takes `try_lock_for_update()` and READS the result
  (an empty return means another worker holds the run), resumes at
  `id > processed_employee_id`, and stops at `PASS_SECONDS` or when
  `ir.cron._commit_progress` reports no time left.
- **`_run_one_employee(self, employee, ctx)`** - asks `_check_recalc_allowed`
  FIRST and on its own, then splits by exception TYPE: `AccessError` is a
  breakdown, `UserError` is the documented refusal. Never by message text -
  that stops working the moment it is translated. The rebuild itself runs in a
  `cr.savepoint()`; a plain `cr.rollback()` here would discard every person
  already committed in the pass.
- **`_outcome_of(result)`** (static) - three outcomes, not two: `done`
  (attendance written), `no_result` (events but nothing written - the period
  was cleared and left empty), `no_events` (nothing to replay).
- **`_finish_reporting_outcome(self)`** - picks the closing state and message;
  `_also_cleared` / `_also_left_alone` / `_also_refused` add the people the
  chosen sentence does not already account for.
- **`_abandon_stalled_runs(self)`** - decorators: `@api.model`
  - Closes runs untouched for `STALLED_MINUTES` and RETURNS them, so the caller
    knows there is something worth committing.
- **`_as_the_operator_would(self)`** - `hr.employee` `with_user(user_id)` +
  `with_company(company_id)`; `None` when the account is archived - except the
  superuser, which is archived by design and is the account every rebuild
  started outside a browser runs under.
- **`_tell_the_operator(self, state, message)`** - `_bus_send('simple_notification')`
  to `user_id`, green only for `done`, sticky for everything else.
- **`_for_the_operator(self)`** - the record in `user_id.lang`; the work runs as
  the scheduler's user, so without it every message reaches the operator in
  somebody else's language.
- **`_gc_recalc_runs(self)`** - decorators: `@api.autovacuum`
  - Deletes finished runs (`FINISHED_STATES`) older than `GC_DAYS`, at most
    `GC_LIMIT` per pass, returning `(count, count == GC_LIMIT)` so the vacuum
    re-queues itself.

### `hr.attendance.recalc.log`
Python class `HrAttendanceRecalcLog` in `models/attendance_recalc_run.py:668`.  Model.  Description: *Attendance Rebuild Line*.  Default order: `id`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `run_id` | Many2one → \`hr.attendance.recalc.run\` |  | ✓ | ✓ | `ondelete='cascade'`, indexed. |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | `related='run_id.company_id'`, stored - the record rule needs it in SQL. |
| `employee_id` | Many2one → \`hr.employee\` | Employee | ✓ | ✓ | `ondelete='cascade'`. |
| `status` | Selection |  | ✓ | ✓ | `done` / `no_events` / `no_result` / `refused` / `error`. |
| `event_count` | Integer | Door events |  | ✓ | How many events were replayed. |
| `attendance_count` | Integer | Attendance records |  | ✓ | How many records came out of them. |
| `error_message` | Text | Reason |  | ✓ | Kept WHOLE for a refusal - the refusing add-on wrote it for the operator. |


## What the constants of the rebuild mean

### `models/attendance_recalc_run.py`

- **`PASS_SECONDS`** = `5.0` - how long one pass may spend rebuilding. A safety
  parameter, not a tuning knob: `limit_time_real_cron` only replaces the limit
  when positive, and overrunning restarts the server rather than failing the job.
- **`STALLED_MINUTES`** = `30` - after this a run is treated as dead and closed.
- **`NAMES_SHOWN`** = `8` - people named in a summary before it switches to a count.
- **`FINISHED_STATES`** = `('done', 'nothing', 'refused', 'failed')` - drives the
  vacuum and the "Continue now" / banner visibility. Anything else is still on
  its way and must never be tidied away.
- **`HrAttendanceRecalcRun.GC_LIMIT`** = `500`, **`GC_DAYS`** = `7` (class
  attributes) - bounded deletion; a year of history in one transaction locks
  the table.


## Who may see and start rebuilds


An officer READS rebuilds and their lines and nothing more: they cannot create
the wizard, write a run directly, restart a finished one, edit a line or delete
a run. Asserted in `tests/test_recalc_security.py`, from a restricted user - a
security test that runs as superuser proves nothing, because
`ir.model.access.check` returns True on its first line.


## The scheduled actions


- **`hr_attendance_multi_rfid_autoclose_cron`** (HR RFID Multi Attendance: Auto-close incomplete attendances) on `model_hr_attendance`, runs every 1 minutes, active=True
- **`hr_attendance_multi_rfid_recalc_cron`** (HR RFID Multi Attendance: Continue attendance rebuilds) on `model_hr_attendance_recalc_run`, code `model._cron_process()`, runs every 1 days, priority 20, active=True, `noupdate="1"`.
  - The daily interval is a floor, not the cadence: every request for a rebuild
    triggers it (`ir.cron._trigger()`), and each pass that runs out of time
    triggers the next. It ships ACTIVE because an inactive cron drops triggers
    silently, which is why the wizard refuses when it is off.
  - Priority is below the auto-close cron (5, every minute) on purpose: a long
    rebuild must never hold up the job that closes people's open attendance.


## The screens of a rebuild

| `hr_attendance_recalc_run_list` | `hr.attendance.recalc.run` | list | | `views/attendance_recalc_run_views.xml` |
| `hr_attendance_recalc_run_form` | `hr.attendance.recalc.run` | form | | `views/attendance_recalc_run_views.xml` |

Plus `hr_attendance_recalc_run_action` and the menu **Attendance -> Attendance
Rebuilds** (`hr_attendance.group_hr_attendance_manager`). The form has no
`create` and no auto-refresh; the header carries **Continue now**
(`action_start`) because a progress bar that never moves reads as a stalled job
and the operator starts a second rebuild. Three banners spell out the endings
that are neither success nor failure (`nothing`, `refused`).

## The record rules of a rebuild

- **`ir_rule_hr_rfid_card_multi_company`** on `resource.model_resource_calendar` - perms=`R`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_hr_attendance_recalc_run_multi_company`** on `model_hr_attendance_recalc_run` - groups=`global`, domain=`['|', ('company_id', 'in', company_ids), ('company_id', '=', False)]`
- **`ir_rule_hr_attendance_recalc_log_multi_company`** on `model_hr_attendance_recalc_log` - groups=`global`, same domain; the line carries `company_id` as a STORED related of its run, because a record rule is evaluated in SQL.

The `('company_id', '=', False)` branch is deliberate (same form as
`hr_rfid_leave_block`): a record without a company must stay visible rather
than disappear from everybody.
