## Transfer contract

What a caller and a reviewer can rely on. Written by hand; the sections around
it are generated from the code.

**Every long read is resumable, and that is enforced.** `BaseImporter._read_all`
takes a mandatory `cursor_key`, unique to the STEP (two steps reading the same
model through different domains must not share one). The key remembers where
the read got to, on the run record, so the next pass carries on; it is set to
`CURSOR_FINISHED` when the source is exhausted, and a finished read is not
repeated. A step that cannot name its cursor raises rather than silently
restarting from the beginning on every pass - which is what stalled a 6 176
person tenant at 1 001 people for good.

**A step reports the RUN, not the pass.** `BaseImporter.accumulated_result`
takes the same key as the cursor and adds this pass's slice to the running
totals, so a finished step whose last pass legitimately read nothing still
reports what the whole transfer moved.

**Rows, cursors and totals move together.** `progress_snapshot()` /
`restore_progress()` are taken around every step (`PhaseImporter.steps`) and
every phase (`run._run_one_phase`, and the synchronous path in the wizard): when
a savepoint takes the rows back, the reading position and the counts go back
with them, so the next pass does not skip records that never landed.

**A phase declares what it needs, and what it merely ASKS about.**
`REQUIRES_SOURCE` gates the phase; `PROBE_SOURCE` only adds module names to the
list the wizard asks the source about, for data that has its own switch. Both
feed `source_probe_modules()`, so no list is kept by hand.

**Field names are read from BOTH schemas, never assumed.** Each step intersects
its candidates with the source's `fields_get` and the target's columns, so a
name that exists in neither is dropped WITHOUT A WORD. Four such lists shipped
with names that existed in neither version - the controller's capacities
(`readers`, `time_schedules`), the daily roll-up's numbers, the vending profile
of a person, and a refill run's total - and each one cost real data on a live
cloud. When adding a field, check it against both sides.

**What the automation here already made is ADOPTED, not duplicated.**
Controllers, doors and readers by their device key; cameras by their chain; time
schedules by (company, slot). Every one of those exists before a transfer runs,
because this system creates them itself.

**The final check separates inherited from introduced.** Phase 9 asks the source
whether it has the same shape; equal numbers are reported as carried over
rather than as a fault of the transfer.

## Attendance hours after a transfer

The attendance step writes `hr.attendance` rows with SQL for speed, so the
stored figures (`worked_hours`, `overtime_hours`, `expected_hours`) are not
computed by the insert itself. The one figure it does write, the record's
`date`, is core's own rule for it (`hr_attendance.py:90`: the check-in read in
`employee._get_tz()`), so a stay begun after midnight in Sofia carries that
morning's date as a record made by the doors would; rows an earlier transfer
dated by UTC get the right date when the step below works them out. A step of its own,
`AttendanceImporter._settle_attendance_figures()`, runs after it and puts them
right. It shows in the protocol as the line "Worked Hours".

- **When.** Only once the attendance read is finished, so a person's figures
  are worked out once over all of their rows. A fault in it cannot take back
  attendance that has already landed.
- **Whose.** The people this source brought across (found by their external
  IDs) into the companies of THIS transfer, and every attendance of theirs
  whose figures do not hold, whatever its date: no worked hours at all, or
  regular hours further than `FIGURE_TOLERANCE` from worked minus extra. A new
  transfer over an earlier one therefore repairs the earlier one.
- **How.** Core's `_update_overtime` deletes and recreates every overtime line
  in the range it is given, and a recreated line loses its approval or
  refusal. It also needs the person's schedule, which core has only inside a
  version (`hr.employee._get_version_periods`): before the first version it
  counts the whole day as approved extra time (measured: 08:00-17:00 read 9
  extra and -1 regular, for a day entered by hand too). So the rows are cured
  three ways:
  - regular hours that disagree, with worked hours present: only
    `expected_hours` is recomputed, and the overtime lines are left alone;
  - no worked hours, before the first version: `modified(['check_in',
    'check_out'])` (the idiom core uses after its own raw updates) and nothing
    else - no rules apply there, exactly as core's "Regenerate overtimes"
    leaves them (`_attendances_to_regenerate_for` stops at the version);
  - no worked hours, inside a version: the same, then core's
    `_update_overtime()`, as `hr.attendance.create` does. It is handed one run
    of such rows at a time, cut at every row that has its hours and at every
    local week (MO-SU in the person's zone, as core counts weeks), so a correct
    day between them is never in its range. A day or week holding both kinds
    is worked out again as a whole, as core does on any edit of it.
  - `expected_hours` is marked explicitly in all three, because core marks it
    in the overtime run only since odoo/odoo 17577a1f9c6 (in 19.0 since
    30.03.2026).
- **Time.** Where it got to (`read_cursors['attendance:figures']`) and what it
  could not do (`step_totals['attendance:figures']`) travel with the cursors.
  A pass that runs out of time stops between people and the next pass carries
  on from there. A person whose rows another process is writing at that
  moment waits for the next pass: the step stops part-way, and
  `import_run._process_pass` returns to any phase that did not finish instead
  of ending the run without it.
- **When it cannot.** Each unit has its own savepoint. A unit that core's
  overtime run refuses stays without figures, so the next transfer finds it
  again. The line turns "partial" and names the people, the first day (in the
  person's own zone) and what the system answered, with the advice to put
  those days right and run the transfer again. Only data errors (`UserError`,
  integrity and data errors from the database) are counted this way; anything
  else is a fault in the code and shows as a failed step.
- **No history entries.** The step runs with the import context
  (`tracking_disable`), so the transferred attendances get no tracking message.
- Customer case (12.10.2026): after a transfer more than half of the closed
  attendances read 0 hours worked, and about a third had regular hours that
  were not worked minus extra.

Tests: `tests/test_transferred_attendance_has_hours.py`
(tags `rfid_odoo_import`, `rfid_import_attendance_hours`), and
`tests/test_background_run.py` for the return to an unfinished phase.

## The phase registry

Phases are classes in `models/importers/`, each declaring what it needs:

| Attribute | Meaning |
|---|---|
| `PHASE_ID`, `NAME` | identity in the transfer log |
| `REQUIRES_SOURCE` | module names the SOURCE must have installed |
| `REQUIRES_TARGET` | model names, or `(model, field)` pairs, this system needs |
| `OPTION` / `OPTION_ANY` | key(s) in the options dict that switch it on |
| `WEIGHT` | share of the progress range |

`registry()` returns them in execution order; the order carries meaning and is
asserted by tests, not by comments. `phase_plan(env, options, source_modules)`
is a pure function returning `[(class, skip_reason_or_None)]` - no network, no
writes - which is what makes the gate testable without a source system.

`source_probe_modules()` derives the list of modules asked of the source from
the phases themselves. A list maintained anywhere else falls behind: that is
how the camera module went unqueried and the whole camera dataset was silently
left behind while the run reported success.

`_target_available` refuses abstract and transient models (they resolve in the
registry but own no table) and accepts a `(model, field)` pair, because a model
present under the same name may still lack the column a bulk insert will write.

### Adding a phase

1. Subclass `PhaseImporter` in `models/importers/`, set the metadata, implement
   `run(wizard)` returning a list of `_make_result` dicts.
2. Add it to `build_registry()` in the position its dependencies require.
3. Add the option field to the wizard and to `_build_options`.

Nothing in the wizard needs to learn its name.

## Background execution

`hr.rfid.odoo.import.run` is a permanent record; the wizard only fills it in
and triggers the scheduler. The work cannot happen in the HTTP request - it is
cut off at `limit_time_real` (120 s by default) - and the cron thread is NOT
exempt either: `limit_time_real_cron` only replaces the limit when positive,
and exceeding it restarts the server rather than just failing the job. Hence
`PASS_SECONDS`, a safety parameter rather than a tuning knob.

Each pass works through whole phases and commits between them via
`ir.cron._commit_progress`, which also reports how much is left so core
reschedules itself. Long reads stop between pages (`BaseImporter.time_is_up`)
and the phase is marked `partial` rather than done.

Resuming safely rests on two things:

- every write path goes through an external ID, so a repeated read creates
  nothing twice;
- `_map_m2o` falls back to `ir.model.data` when the in-memory map is empty,
  which it always is in a new process. Without that fallback every relation in
  every later pass resolves to nothing and is counted as skipped - a transfer
  that loses its data and reports success.

A run untouched for `STALLED_MINUTES` is closed automatically and its stored
credentials cleared. `_abandon_stalled_runs()` RETURNS what it closed and
`_cron_process` commits that before starting the next pass: a pass rolls the
transaction back when it fails, which would otherwise undo exactly the closures
that unblock the queue, leaving the same dead runs in the way on every wake-up.

## Identity of a transferred record

**A record is recognised by its source id, carried in Odoo's own external-ID
metadata (`ir.model.data`) - never by name, serial, e-mail or card number.**
There is no separate register: the "ledger" of earlier versions was always
`ir.model.data`, and the word has been dropped because it named a thing that
does not exist.

| Piece | Where | Value |
|---|---|---|
| `EXTERNAL_ID_MODULE` | `models/importers/base_importer.py` | `'__import__'` - what core's own `BaseModel.load()` writes for imported rows |
| `EXTERNAL_ID_PREFIX` | same | `'rfid_import_'` |
| `_xml_id_name(model_prefix, source_id)` | `BaseImporter` | `rfid_import_{source_slug}_{model_prefix}_{source_id}` |
| `normalise_source_slug(value)` | module-level function | `-` and `.` to `_`; an external-ID name may not carry dots, so every producer and every reader must apply the SAME rule or a check answers about one spelling while the transfer writes another |

`source_slug` is the identity of the SOURCE SYSTEM. It defaults to the source
database name and is overridable on the wizard (`source_slug`, "Source
Identity") for the case that made it necessary: the same installation read from
two places - a restored backup for the bulk, then the live server for the
delta - must write ONE set of ids. Two names for one system means nothing
matches and everything arrives twice; measured on the o15 cloud, 298 937
duplicated events alone.

Helpers (renamed from the `*_ledger` names, same behaviour):

- `find_by_external_id(model, source_id, expect_text=None, text_field='name')` -
  the only identity lookup. `expect_text` is a SECOND check on the record
  already found by id: a mismatch is reported, never used to search elsewhere.
  `find_by_ledger` remains as a temporary alias for the camera, people and
  service importers, which have not been renamed yet.
- `prefetch_external_ids(model, source_ids)` - reads the durable half of the
  in-memory map back in one query. A new process starts with `id_map` empty, so
  without this every relation resolves to False and the row is counted as
  skipped while the protocol reads as a clean run.
- `link_existing`, `_bulk_insert_with_xmlid`, `_match_by_external_id` - all
  write or read the same names.

### What a second run does

`_load_records` looks the external ID up first and WRITES to the record it
names, so a second run **refreshes from the source**. The `'noupdate': True`
carried in `data_list` is recorded on the metadata row but changes nothing
here: core honours it only when called with `update=True`
(`if not (update and d_noupdate)`), and this call does not. That is the owner's
decision, not an accident - so the wizard says it out loud before the start
(`_warn_about_refresh_on_rerun`), in three parts that are each true of the code:

- equipment and cards are written again (put back to the source's version);
- people, contacts, departments, staff tags, card types, access groups and
  sites are recognised and left alone (the write is never reached);
- a list the source keeps as a whole - an access group's DEPARTMENTS, the
  groups it inherits, the doors a reader serves - is written back whole, so an
  entry added here is taken out again. The DOORS of an access group are not
  such a list: they are permissions of their own and are only ever added.

Regression tests for each clause:
`tests/test_second_run_changes_nothing.py`.

### Recognising another system's records

`_warn_about_other_source_identity` asks the question the only way that can be
answered: for each identity a transfer started IN THIS DATABASE has read
(`hr.rfid.odoo.import.run` is the permanent account of that), is anything from
it still here (`_holds_records_from`, one `=like` per identity). It does NOT
sample what is already present - a sample answers with whichever rows it meets
first, so in a database that also holds a large import from another tool the
one name that matters can fall outside it. Reading a sample also cannot tell
this module's records from the Andromeda or old-cloud imports, which write the
same module with names of their own; asking "which systems have WE read" can.

Empty box + records from another identity = `danger`, which blocks the start.
Filling the box IS the decision, so it drops to `warning` and the transfer
proceeds.

## Attendance brought over is never rebuilt

`models/hr_employee.py` implements `hr.employee._check_recalc_allowed` (the
hook declared in `hr_rfid`) and refuses when the requested window holds
attendance carrying this transfer's external ID.

- Detection is ONE query: the external IDs are used as a sub-select
  (`ir.model.data` has no link back to attendance), matched on
  `EXTERNAL_ID_NAME_PATTERN` = `rfid_import_%_hr_attendance_%` - the module
  alone would also match an ordinary spreadsheet import.
- The window comes from the rebuild itself (`_local_days_window`, in the
  person's own zone - `_local_tz`), so the two cannot drift; people are
  grouped by that zone to keep it to one query.
- The `ir.model.data` side is read `sudo()` (not readable by whoever runs a
  rebuild); the attendance side is read with the CALLER's rights, so the
  refusal is about exactly the records the rebuild would have deleted and no
  name from another company leaks into the message.
- Why refuse at all: the rebuild deletes the record together with its metadata
  row, so the next transfer no longer recognises the row it already brought
  over and adds it a second time. The message tells the operator to run the
  transfer again instead.

Tests: `tests/test_recalc_guard.py` - refused at the wizard button with nothing
queued, and a run driven through `_cron_process` ending `refused` with the
attendance AND its `ir.model.data` row untouched.

## A stay already recorded here is kept

The attendance step inserts with SQL, past core's `hr.attendance._check_validity`
(`hr_attendance.py:206-246`), so before the insert
`AttendanceImporter._leave_out_stays_recorded_here` holds every row not yet
carried by this transfer (its source id has no external ID) to that rule:

- `refused_beside(start, stop, other_start, other_stop)` is core's check asked
  of the new stay AND of an open one at the moment it is closed: two open stays
  side by side; a stay beginning while another runs; another beginning inside a
  closed one. An open stay holds all the time from its check-in on - core
  accepts a closed stay begun after it, then refuses to close the open one (or,
  with the check bypassed, counts the time twice). The test asks core's own
  method, called directly, for every shape, and again after closing the open
  stay of the shape.
- The same stay to the second is asked first, before the rule: a stay that
  begins and ends at one moment collides with nothing, not even its twin.
- Compared with what is recorded here (`_stays_recorded_here`, one query per
  page, earliest first; a page with an open stay has no upper bound) and with
  the rows of the same read accepted before it, in source order.
- The same to the second: counted as already here (`linked`), under
  `SAME_HERE_KEY` as `{source id: company}`. Different: left out (`skipped`),
  under `DIFFERS_KEY` as `{source id: [person, company, check-in, check-out,
  check-in here, check-out here]}`. By source id, and every id of a page loses
  its earlier verdict first: a write that fails sends the read back to the
  start, and the page read again replaces what it said instead of saying it
  twice. The line is `partial`, names the first people with the first local
  day (`BaseImporter.first_few`), and
  `hr.rfid.odoo.import.run._protocol_stays_left_out` adds the whole list to the
  downloaded protocol, both times in the person's zone (`format_datetime`,
  `short`); the people are read as superuser (`people_by_id`), because the
  operator downloading it has one tenant selected.
- Both live in the step totals of `attendance:hr.attendance`, so they survive
  the passes and are undone with the rows. The reconciliation counts them as
  accounted for (`ReconcileImporter._kept_here_on_purpose`), not as lost; a
  transfer that carried no attendance takes them from the latest earlier
  transfer of the same system that did (`_attendance_verdicts`), since the
  check compares every kind whatever was ticked (see "The final check: a
  problem only in what was carried").
- Nothing links a left-out row to the record here, so every run checks again:
  a stay that collides today arrives on the run after the stay here is put
  right.

Customer case, 23.10.2026: a second transfer from an older copy of the other
system would have laid 11 116 stays over the ones rebuilt here from the door
events, 9 808 of them the same to the second. Rehearsed on a copy of that
database: 8 824 arrived (the three months the system had no attendance for),
9 808 counted as already here, 1 327 listed, no new overlap, and a second run
changed nothing.

## The final check: a problem only in what was carried

`ReconcileImporter` (Phase 10) counts every kind of `RECONCILED` on both
sides, tenant by tenant, whatever was ticked. Each entry is `(model, path,
option[, extra domain])`; `option` is the operator's tick that asks for the
kind, a tuple when several do (cards: `import_access` or the "Import Cards"
tick `import_cards`). `CARRIED_BY` maps model to option; the label the
operator reads is `KIND_LABELS[model]`, a lazy translation.

- Asked for = `_ticked(option)`: the option itself or the operator's raw tick
  in `options['ticked']`. The wizard (`_build_options`) folds a tick with
  module availability for vending, attendance, extra attendance and services,
  so the step switch is off when this system cannot take the data; the raw
  tick keeps such data, asked for and left behind, a problem.
- A kind not asked for: no difference - `done`; any difference, either way -
  `skipped` with a remark that it was not part of this transfer, both numbers
  per tenant. A check that breaks on such a kind is `skipped` too. None of it
  makes the run fail (owner's decision, 10.11.2026).
- A kind asked for and short: before calling it a loss, the check asks the
  other system how many of those records belong to an owner that is not here
  (`_owned_by_owners_not_here`). Owners are listed explicitly in `OWNED_BY`:
  the person of an attendance, daily summary, vending balance entry, absence,
  leave balance and staff membership of an access group; the contact of a
  contact membership; the person of a card, then - only for a card with no
  person - its contact. They are tried in the order the steps try them, and
  only owners whose kind was not asked for count (`OWNER_CARRIED_BY`: both
  come with People). The same tenant filter and extra domain as the main
  count apply. "Here" is the transfer's identity of the owner with a record
  still behind it, archived included (`_source_ids_here`; a ledger row whose
  record was deleted around the ORM does not count; a name that does not end
  in the source id makes the answer unknown).
  - those records fill the gap: a remark (`partial`), with their count;
  - the other system will not say (`None`): the whole gap stays a loss and the
    line says it was not told;
  - more of them than the gap: the two counts do not describe the same records
    and explain nothing - the whole gap stays a loss;
  - what is still short after them: `error`.
  When the owner's kind WAS asked for, nothing is excused: the owner's own line
  says who is missing.
- "Arrived" is read from the transfer's own identity rows by the exact prefix
  the steps write (`_identity_prefix`, model included): the identity of one
  source must not take in another's whose name continues it ("acme" and
  "acme_old").
- `KIND_LABELS` is a separate mapping on purpose: core's term extractor
  (`odoo/tools/babel/python_extractor.py`) keeps the last NAME it saw, so the
  `(` opening a tuple right after a `_lt(...)` or `env._(...)` call is read as
  one more call, and the tuple's model names went out for translation. The
  wizard's preview counts keep their labels in a mapping for the same reason.

Customer case, 10.11.2026: a second transfer of the attendance alone carried
8 824 stays and kept 1 327 recorded here, and was reported "stopped by a
problem" over people (209 there, 208 here), access and system events, daily
summaries and one stay of a person this system does not have. With the rule it
ends as finished, with those as remarks; a second run changes nothing.

The background worker writes the protocol in the language of the person who
started the transfer (`_in_starters_language`, used by `_cron_process`, its
failure path and `_abandon_stalled_runs`), not in the scheduler's - only when
that person has a language, as core does (`mail_activity.py:422-424`).

Tests: `tests/test_reconcile_with_the_source.py` (every rule above, each with
its negative twin, and the whole pass of an attendance-only transfer ending as
finished), `tests/test_a_stay_recorded_here_is_kept.py`,
`tests/test_background_run.py::test_the_protocol_is_written_in_the_language_of_who_started_it`.

## Reference data vs migrated data

Records shipped with a module - card types being the case in point - exist on
both sides under the same external id. `_match_by_external_id` links them
instead of creating copies. Creating a second "License Plate" makes plate
numbers land on a type the card validation does not recognise as plates, and
every plate is then refused for "digits must be from 0 to 9", taking the camera
links with them.

## Talking to hardware

`IMPORT_CONTEXT` carries `no_hardware_commands`, honoured by `hr_rfid` and, as
of 19.0.1.12.0, by `polimex_ip_cam`. The guard sits on `cctv.camera.command`
itself as well as on the callers, because `queue_send` registers a postcommit
hook and postcommit hooks survive a savepoint rollback - a rolled-back phase
would otherwise still have fired at the cameras.

Any new write in an importer must carry this context. The site phase originally
did not, and its access-group cascade reached live cameras through three
separate paths.


## The identity a transfer files its records under

- **`_effective_source_identity(self)`** - decorators: -
  - `normalise_source_slug(source_slug or source_db)` - the name this transfer
    will file its records under. Everything that compares identities must go
    through it, or it compares one spelling with another.
- **`_identities_this_transfer_has_read(self)`** / **`_holds_records_from(self, identity)`** / **`_other_source_identities(self)`** - decorators: -
  - The other-source check, asked per identity rather than by sampling what is
    already here. See "Recognising another system's records".
- **`_warn_about_other_source_identity(self)`** / **`_warn_about_refresh_on_rerun(self)`** - decorators: -
  - The two warnings whose wording is load-bearing: the operator decides
    whether to start on the strength of them, so every clause has to be true of
    the code (and is covered by a behaviour test).

## The transfer record (`hr.rfid.odoo.import.run`)

The permanent record of a transfer - the wizard is transient and would take the
job with it. It carries what the work needs to continue in another process:
the connection (`source_url`, `source_db`, `source_login`, `source_password`,
`source_uid`), the identity (`source_slug`), the operator's choices
(`options_json`, `company_map_json`, `resolution_json`), and the cursors
(`done_phases_json`, `read_cursors_json`, `current_phase`, `done_count`,
`total_count`). `state` is `queued` / `running` / `done` / `failed`; `log_ids`
is one line per phase, and a phase that stopped early is `partial` ("Partly"),
not `done`.

`hr_attendance_multi_rfid.hr.attendance.recalc.run` is deliberately the same
shape - one pattern for long jobs in this codebase, not two.

Key methods: `action_start`, `_cron_process` (one pass; closes stalled runs and
COMMITS that before starting a pass), `_process_pass`, `_run_one_phase`,
`_save_progress` (`ir.cron._commit_progress`), `_abandon_stalled_runs` (returns
what it closed; clears the stored credentials), `_finish_reporting_failures`.

## What the constants mean

- **`EXTERNAL_ID_MODULE`** = `'__import__'` - the `ir.model.data` module every
  transferred record is registered under, the same one core's own
  `BaseModel.load()` writes.
- **`EXTERNAL_ID_PREFIX`** = `'rfid_import_'` - start of every external-ID name
  this transfer writes. Read by anything that has to recognise a transferred
  record (`models/hr_employee.py` builds its pattern from it).
- **`ATTENDANCE_MODEL`** = `'hr.attendance'`
- **`EXTERNAL_ID_NAME_PATTERN`** = `'rfid_import_%_hr_attendance_%'` (built from
  the two constants above, source installation wildcarded)
- **`NAMES_SHOWN`** = `3`, **`DEFAULT_LOOKBACK_DAYS`** = `30` (the same window
  the rebuild starts from when no date is given)
