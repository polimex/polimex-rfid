---
id: hr_rfid_hardware_import
title: RFID Hardware Import
module: hr_rfid_hardware_import
module_version: 19.0.1.0.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Survey a running access control system without changing it and import it
last_updated: '2026-09-04'
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
2. **No command from the import.** Records are created under the context
   that switches the access control module's hardware side effects off, and
   controllers are created through the path that module uses for a
   controller it already knows - so no reset, clock sync or card deletion is
   ever queued. The end-to-end test asserts that no write command exists in
   the command queue after an import.
3. **Idempotent.** Every created record carries an external ID
   (`__import__.rfid_import_hw_<site>_<kind>_<ref>`); a second import of the
   same site finds and reuses them.

The decoders of the replies mirror what `hr_rfid` already reads and writes
and are verified against the protocol reference implementation
(polimex-protocol 0.1.1) by a local oracle test whose vectors are private and
not part of this repository.

## Recent changes

* 19.0.1.0.0 - first version: discovery, reading, analysis, names file,
  proposed groups, schedule decisions, conflict reporting, background import,
  explicit hand-over of modules.

## Architecture

| Part | File | Role |
|---|---|---|
| Allowlist | `helpers/allowlist.py` | The only decision point for what may be sent |
| Transport | `helpers/transport.py` | HTTP client for the module's local interface, UDP discovery, retry and stray-reply handling |
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
at a time (`PASS_SECONDS`), and a survey untouched for `STALLED_MINUTES` is
closed.

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
  (`COMMAND_BUDGET_SECONDS`) so that retries on a busy bridge or a silent
  bus cannot push a pass past the scheduled action's own time limit, and the
  network search waits at most `MAX_DISCOVERY_TIMEOUT` seconds.
* Merging proposed groups is refused, with the reason, when the result could
  not exist in `hr_rfid`: the same door on different schedules or alarm
  rights inside one group, or a card that would reach a door through two
  groups (`check_doors`), or a card set another proposed group already has.

### The import

Order: schedules, modules (created inactive, with the time zone set at
creation), controllers (created with the serial pre-set and then fed the
captured system-information reply through `hr_rfid`'s own handler, which
builds doors and readers and, because the controller already exists, queues
nothing), people, cards, access groups with door rights and memberships
(`hr_rfid` derives the card-door rights itself under the import context),
report. Every step can be left out. A right whose schedule number the
company does not have is left out and reported - never widened to "no
schedule", which would open the door around the clock. When a company
schedule is overwritten by the controllers' one, the company's other
controllers that held the previous version are unlinked from it and listed
in the report (`hr_rfid` rewrites them when the schedule is next needed
there). The only device write the module knows is `action_point_to_server`
on a module row, which reuses `hr.rfid.webstack.action_set_webstack_settings`;
pointing every module of a survey handles each one in its own savepoint, so
a module that refuses does not undo the ones already reconfigured.

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
| `hr.rfid.hw.import.cmd.log` | Every command sent; vacuumed after 90 days |

Wizards: add a module by address, upload a names file (read through the
standard import reader of `base_import`), import options, merge proposed
groups.

## Security

All models are restricted to `base.group_system`; every row belongs to its
survey's company through record rules. Module passwords are cleared when the
survey ends, and by the scheduled action after a day without activity on a
parked survey (`IDLE_PASSWORD_HOURS`). The module configuration kept as
evidence has secret-looking keys and credentials inside addresses redacted.
The transport accepts only a JSON object with a status code as a command
reply, follows no redirect, and names a password problem as such.

## Testing

Tags: `rfid_hw_import` (all), `rfid_hw_import_allowlist`,
`rfid_hw_import_codecs`, `rfid_hw_import_transport`,
`rfid_hw_import_discovery`, `rfid_hw_import_read`, `rfid_hw_import_import`,
`rfid_hw_import_company`, `rfid_hw_import_tour`, `rfid_hw_import_oracle`
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

**Why does a person with two cards get a warning?** The access control
module grants rights per person, the controller per card; after the import
both cards open the union. The warning names the difference.
