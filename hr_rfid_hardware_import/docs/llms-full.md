---
id: hr_rfid_hardware_import
title: RFID Hardware Import
module: hr_rfid_hardware_import
module_version: 19.0.1.2.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Survey a running access control system without changing it and import it
last_updated: '2026-11-13'
depends:
- hr_rfid
- base_import
entities:
  primary: hr.rfid.hw.import.run
  related:
  - hr.rfid.hw.import.module
  - hr.rfid.hw.import.ctrl
  - hr.rfid.hw.import.card
  - hr.rfid.hw.import.card.record
  - hr.rfid.hw.import.ts
  - hr.rfid.hw.import.ts.slot
  - hr.rfid.hw.import.group
  - hr.rfid.hw.import.group.right
  - hr.rfid.hw.import.person
  - hr.rfid.hw.import.name
  - hr.rfid.hw.import.issue
  - hr.rfid.hw.import.cmd.log
keywords:
- access control
- survey
- hardware
- import
- cards
- access groups
- read-only
license: AGPL-3
author: Polimex Dev Team
category: HR
installable: true
application: false
auto_install: false
chunking:
  target_tokens: 500
  overlap_tokens: 75
---

# RFID Hardware Import - technical reference

## Overview

The module surveys a working access control installation through the local
interface of its network modules, keeps everything it read as evidence,
lets the operator decide about names, groups and conflicts, and then creates
the records of the access control module (`hr_rfid`). Three guarantees hold
by construction:

1. **Read-only towards the hardware.** Every controller command passes
   through one allowlist (`helpers/allowlist.py`) before any network call; a
   command that is not a read is refused with an exception. The module's HTTP
   paths are allowlisted the same way. Every command sent is logged
   (`hr.rfid.hw.import.cmd.log`).
2. **Nothing written by the import.** Records are created under the context
   that switches the access control module's hardware side effects off, and
   controllers are created through the path that module uses for a
   controller it already knows - so no reset, clock sync or card deletion is
   ever queued. The end-to-end test asserts that no write command exists in
   the command queue after an import. (For a temperature controller on a
   module that is already active here, the access control module's own
   handling of the system information queues two reads; nothing else.)
3. **Idempotent.** Every created record carries an external ID
   (`__import__.rfid_import_hw_<site>_<kind>_<ref>`); a second import of the
   same site finds and reuses them.

The decoders of the replies mirror what `hr_rfid` already reads and writes
and are verified against the protocol reference implementation
(polimex-protocol 0.1.1) by a local oracle test whose vectors are private and
not part of this repository.

## Recent changes

* 19.0.1.2.0 - ready for large sites: the people, cards and memberships
  steps of the import commit in batches with the step's position
  (`step_cursor`), memberships are a step of their own, every pass respects
  the time the scheduler gives its job and hands over to a fresh one, a
  pass that could do nothing asks to be repeated at once, a half-read card table
  continues from its page after a reopen, the counters of the survey are
  counted in the database, the command log opens from a button instead of a
  tab, the module address must be a bare IP address or host name, an Excel
  sheet that would exceed its row limit is refused, members holding
  cards that were not read are named in the report, a card left out of the
  import gives its holder no group, an import started again after a
  failure writes no report line twice, anti-passback is read as the
  controller holds it - per reader pair - so the common zone setting is
  reported instead of switching anti-passback on for a third door, and the
  findings and the report are written in the language of the person who
  started the survey, not in English.
* 19.0.1.1.0 - the network search is the core's own (`hr.rfid.webstack.discovery`);
  everything read can be exported as an Excel workbook or a JSON document
  without importing.
* 19.0.1.0.1 - the vending firmwares 20 (Executive only) and 21 (MDB) are
  surveyed as vending machines, not alarm panels; the vending family follows
  `hr_rfid`'s list of vending codes.
* 19.0.1.0.0 - first version: discovery, reading, analysis, names file,
  proposed groups, schedule decisions, conflict reporting, background import,
  explicit hand-over of modules.

## Architecture

| Part | File | Role |
|---|---|---|
| Allowlist | `helpers/allowlist.py` | The only decision point for what may be sent, and to which address (`check_host`) |
| Transport | `helpers/transport.py` | HTTP client for the module's local interface with retry and stray-reply handling; the network search is the core's own (`hr.rfid.webstack.discovery._discover_ws`, wrapped by `CoreDiscovery`) |
| Export | `models/exporter.py` | Everything a survey read as an Excel workbook or a JSON document, with or without an import |
| Fake transport | `helpers/fake_transport.py` | Scripted stand-in used by the tests and tours |
| Codecs | `helpers/codecs.py` | Decoders of the replies; reader-to-door and zone-to-door maps identical to `hr_rfid` |
| Survey | `models/hw_import_run.py` | The persistent survey, its state machine and the scheduled worker |
| Reader | `models/reader.py` | The read sequence per module and per controller, resumable through cursors |
| Analyser | `models/analyser.py` | Rights per card, minimum set of access groups, schedule slots, people, conflicts |
| Importer | `models/importer.py` | The import steps, the external-ID ledger, the safe controller creation |

### State machine of a survey

`draft` (modules) -> `discovering` -> `draft` -> `reading` -> `analysing` ->
`naming` -> `grouping` -> `importing` -> `done`; any worker failure ->
`failed` with the reason on the record. The worker states are processed by
the scheduled action *RFID: continue hardware surveys*, one committed piece
at a time (`PASS_SECONDS`, capped by the time the scheduler still gives the
job, `cron_end_time`), and a survey untouched for `STALLED_MINUTES` is
closed with a message that names *Reopen the survey*.

### The analysis

* A card's rights are derived per controller record: for every door of the
  controller (doors are derived from the mode and reader count exactly as
  `hr_rfid` derives them), the readers of that door that accept the card
  give the right, the schedule of the lowest reader gives its schedule and
  the alarm zones of the door give its alarm right.
* Access groups: a right is (controller, door, schedule, alarm right);
  rights held by the identical set of cards form one group. A card belongs
  to every group whose card set contains it. Groups never share a right
  (database constraint).
* Schedule slots: the readings of one slot number across controllers are
  compared by a fingerprint of the weekly grid. Several variants block the
  schedule import until the operator chooses a source controller; the
  company's own schedule is overwritten by the controllers' one (owner
  decision).
* People: one generated owner per card, replaced by the people of the names
  file (matched by card number only; identical names merged, flagged for
  review). A person whose cards open one door on different schedules is
  blocked until split, because `hr_rfid` cannot hold that.
* Conflicts with existing modules (serial), controllers (serial number) and
  cards (number in the company) are reported as blockers with a resolution
  (use the existing record / leave out); nothing is merged automatically,
  and a finding without a decision means "leave out". A module or controller
  registered by another company of the same database is reported as taken,
  without naming that record; it can only be left out.
* What a device does badly is a finding, never silence: a refused request
  (the setting is skipped, the rest is read), an empty or unreadable reply
  (kept as evidence, that setting not imported), a damaged reply on every
  attempt (that controller fails with a note about the wiring), a module that
  stops answering (that module fails and is not tried again by the worker),
  a card count beyond the controller's capacity (clamped), a card table that
  ends before the announced count (that controller fails - an incomplete
  table is never imported), a clock that is not a date (a finding, never a
  drift of zero), the same card twice in one table with different rights
  (the later record is used, and said). A failed module or controller can be
  read again from the names step; the analysis is then redone. A network
  search that cannot run (port in use, no broadcast) is a warning, not an
  empty network, and the cause goes to the server log. The same device
  reached by two addresses is set aside with a finding, never a database
  error in the worker.
* Findings carry a phase (`discovery`, `read`, `analysis`, `import`). The
  analysis deletes and rebuilds only its own; what the reading found stays on
  the Findings tab until that module or controller is read again. Before it
  rebuilds, the analysis remembers the operator's decisions - the resolution
  of every conflict, the controller chosen (or "keep this company's") per
  schedule slot, the name and tick of every proposed group - and puts them
  back on the rebuilt rows that still mean the same thing (same conflict,
  same slot, same set of cards). Merged groups cannot be restored: the
  partition is recomputed from the rights, and the confirm text says so.
* Whether a module is already registered is decided at analysis time against
  the survey's company as it is then (not against what the probe saw), and
  the company of a survey cannot be changed once modules are listed.
* The worker: one pass works on the oldest survey in a working state, and
  reports the other waiting surveys as remaining work, so the scheduled
  action reschedules itself at once instead of at its next daily time. A
  disabled or missing scheduled action is refused with a message that names
  it; otherwise every operator action would park the survey for ever. A
  survey that stops on an exception is closed with a message that says what
  to do next (`Reopen the survey`), never with a Python class name alone; the
  traceback is in the server log. Every controller command has a time budget
  (`COMMAND_BUDGET_SECONDS`), stray replies for another command included, so
  that retries on a busy bridge or a silent bus cannot push a pass past the
  scheduled action's own time limit. The core runs up to ten passes in one
  job; once the job has used its time (`ir.cron` `cron_end_time`), a pass
  starts no work and reports work left with nothing done, which ends the job
  ("partially done") and lets the scheduler start a fresh one. A pass that
  could not take the survey row (another transaction holds it) or met a
  concurrent write (`PG_CONCURRENCY_EXCEPTIONS_TO_RETRY`) is undone and
  reports the same, so it is repeated at once instead of at the daily run. A
  pass the server kills needs nothing of ours: the core deletes the job's
  wake-up calls in the scheduler's own transaction, which a killed worker
  rolls back, so the job is taken up again.
* Language: the scheduler's environment has none, so the worker takes every
  survey in the language of the person who started it
  (`hr.rfid.hw.import.run._in_starter_language`, as the core does for a
  notification); findings, the report and the reason a survey stopped are
  written in that language. A word picked from a list (the severity of a
  finding, the kind and state of a controller) goes through
  `reader.selection_label`, never through the field's raw list, which is
  English only.
* A controller whose card table was half read when the survey stopped keeps
  its position (`read_cursor`) through a reopen and a new *Read the
  controllers*; the pages already read are not asked for again.
* The counters on the survey (cards, people, groups, commands) are counted
  with `_read_group`, never by loading the rows; the blockers are counted from
  the rows on the screen so that the warning follows the operator's edits.
* The network search is not this module's: `CoreDiscovery` calls
  `hr.rfid.webstack.discovery._discover_ws` of the access control module,
  which sends the discovery datagram, collects the answers into rows of that
  wizard and touches no device (its `setup_modules`, the part that writes,
  is never called). Its contract is kept: a module already registered in the
  database does not appear in the result; the survey lists such a module
  when it is added by address, where the module's own configuration page
  identifies it.

### The export

`SurveyExporter` (`models/exporter.py`) turns a survey into a file the
operator can keep or hand on, at any point after the reading and whether or
not an import ever happens. The Excel workbook has one sheet per kind of
thing (modules, controllers, schedules, cards, card records, access groups,
people, findings, raw replies, and the command log on request); the JSON
document (`FORMAT_VERSION`) holds the same, every decoded setting and every
raw reply, for a program or a later import. Nothing is created in the access
control module and nothing is sent to the hardware by an export. A sheet that
would exceed the Excel row limit is refused with a pointer to the JSON
document, as the core's own export does; the JSON document is encoded piece
by piece into one buffer.
* Merging proposed groups is refused, with the reason, when the result could
  not exist in `hr_rfid`: the same door on different schedules or alarm
  rights inside one group, or a card that would reach a door through two
  groups (`check_doors`), or a card set another proposed group already has.

### The import

Order: schedules, modules (created inactive, with the time zone set at
creation), controllers (created with the serial pre-set and then fed the
captured system-information reply through `hr_rfid`'s own handler, which
builds doors and readers and, because the controller already exists, queues
nothing), people, cards, access groups with door rights, memberships
(`hr_rfid` derives the card-door rights itself under the import context),
report. Every step can be left out. People and cards go in batches of
`IMPORT_BATCH`, memberships in batches of `MEMBERSHIP_BATCH` (giving a person
a group recomputes the doors of every card they hold, about 30 ms a person);
each batch is committed with the step's position, and a pass out of time
pauses the step there (`StepPaused`). A member who was already here and
holds cards the survey did not read is named in a warning: `hr_rfid` gives
the groups to all of that person's cards, which the controllers do not hold. A right whose schedule number the
company does not have is left out and reported - never widened to "no
schedule", which would open the door around the clock. When a company
schedule is overwritten by the controllers' one, the company's other
controllers that held the previous version are unlinked from it and listed
in the report (`hr_rfid` rewrites them when the schedule is next needed
there). The only device write the module knows is `action_point_to_server`
on a module row, which reuses `hr.rfid.webstack.action_set_webstack_settings`
and refuses, on the server, a module that was registered here before the
survey;
pointing every module of a survey handles each one in its own savepoint, so
a module that refuses does not undo the ones already reconfigured.

Anti-passback: the controller holds one flag per reader pair (readers 1 and
2, readers 3 and 4) and one for a zone common to both pairs - not a flag per
door (`codecs.APB_PAIR_R1_R2`, `APB_PAIR_R3_R4`, `APB_COMMON_ZONE`). A door
becomes an anti-passback door here when both readers of a flagged pair are
its own (`codecs.apb_flag_of_readers`), which is also how `hr_rfid` writes
that setting from its doors with two readers. A flagged pair whose readers
are on separate doors in the controller's mode, and the common zone, are
named in the report and not imported: `hr_rfid` keeps anti-passback per
door. The export gives the three flags by name.

## Models

| Model | Purpose |
|---|---|
| `hr.rfid.hw.import.run` | The survey: state, options, counters, worker bookkeeping |
| `hr.rfid.hw.import.module` | A module found or added, its identity and read state |
| `hr.rfid.hw.import.ctrl` | A controller: capabilities, raw replies, decoded settings, read cursor |
| `hr.rfid.hw.import.card` / `.card.record` | A card number across controllers / its record on one controller |
| `hr.rfid.hw.import.ts` / `.ts.slot` | A schedule slot on one controller / across controllers with the decision |
| `hr.rfid.hw.import.group` / `.group.right` | A proposed access group and its rights |
| `hr.rfid.hw.import.person` | A card holder from the file or generated |
| `hr.rfid.hw.import.name` | A line of the names file |
| `hr.rfid.hw.import.issue` | Findings: conflicts, warnings, decisions, report lines |
| `hr.rfid.hw.import.cmd.log` | Every command sent; vacuumed 90 days after it was written, once its survey is done or failed |

Wizards: add a module by address, upload a names file (read through the
standard import reader of `base_import`), import options, merge proposed
groups, export what was read (Excel or JSON).

## Security

All models are restricted to `base.group_system`; every row belongs to its
survey's company through record rules. Module passwords are cleared when the
survey ends, and by the scheduled action after a day without activity on a
parked survey (`IDLE_PASSWORD_HOURS`). The module configuration kept as
evidence has secret-looking keys and credentials inside addresses redacted.
The transport accepts only a JSON object with a status code as a command
reply, follows no redirect, and names a password problem as such. The module
address is a bare IP address or host name (`allowlist.check_host`, enforced
on the module row and again in the HTTP client), so no address can reach a
page outside the allowlisted paths. An incomplete IP address ("192.168.1",
which the system resolver reads as another address) and an IPv6 zone are
refused with their own message; a row saved before the check existed sets
that module aside as unreachable, with a finding, instead of stopping the
survey. A department of another company is
refused when the import starts.

## Testing

Tags: `rfid_hw_import` (all), `rfid_hw_import_allowlist`,
`rfid_hw_import_codecs`, `rfid_hw_import_transport`,
`rfid_hw_import_discovery`, `rfid_hw_import_read`, `rfid_hw_import_import`, `rfid_hw_import_failures`, `rfid_hw_import_export`,
`rfid_hw_import_company`, `rfid_hw_import_large`, `rfid_hw_import_tour`, `rfid_hw_import_oracle`
(needs `POLIMEX_PROTOCOL_VECTORS` pointing at the private canonical
vectors; skipped otherwise). The fake transport (`helpers/fake_transport.py`)
scripts an invented site; `tests/common.py` holds it.

## Extension points

* `hw_import_run.override_backend(backend)` - substitute the transport
  (discovery + client factory) for tests or demos.
* `helpers/codecs.family_of` / `reads_cards` - which hardware families are
  read for cards.
* The importer's steps (`STEPS` in `models/importer.py`) are independent
  and resumable; a new step is a new `_step_<name>` method.

## FAQ

**Why are imported modules inactive?** While a module is inactive, no
command of the access control module can leave for it; the operator enables
it after pointing it to this server.

**Why does the import of a large site take minutes?** Giving people their
access groups makes the access control module recompute the doors of every
card; the import does it in small committed batches so that the server's
time limit for background work is never reached.

**Where is the command log?** On the *Commands sent* button of the survey; it
is a list of its own because a large site sends millions of commands.

**Why does a person with two cards get a warning?** The access control
module grants rights per person, the controller per card; after the import
both cards open the union. The warning names the difference.
