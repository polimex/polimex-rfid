## Plate-record write ladder (self-healing)

`HikvisionCamera._lp_audit_add` normalises validity times at the wire
boundary (`_lp_time`: UTC / 'Z'-suffixed values are converted to the
camera's own zone and sent without a suffix - the live-validated format)
and, when the firmware refuses a record as `badParameters`, retries it down
the `LP_RECORD_SHAPES` ladder: `full` -> `no_card` (linked card number
blanked) -> `no_times` (permanent window). The accepted shape is returned
as `shape_used`; the command executor persists it to
`cctv.camera.lp_record_shape` and posts one chatter note, so every later
record starts at the shape this camera speaks. The degradation is safe by
construction: entry/exit decisions are taken by the Odoo lists on each
event, not by the camera-side record details.
## Silence during a data transfer

`hr_rfid_odoo_import` carries `no_hardware_commands=True` in its
`IMPORT_CONTEXT` for every write it makes. This module honours it in FOUR
places, and all four are needed:

| Where | Without the guard |
|---|---|
| `cctv.camera.rfid.rel.create` | every plate brought across queues an `add_plate` at the camera - a few hundred HTTP requests at cameras that are guarding a live site |
| `cctv.camera.rfid.rel.unlink` | the same, as `remove_plate` |
| `cctv.camera.create` | two readers and a door are manufactured here, while the transfer also brings the source's own - two sets in the target and no way to tell which one the historical events belong to |
| `cctv.camera.command.create` | see below |

The guard on the COMMAND itself is not belt-and-braces. `queue_send` registers
a **postcommit** hook, and a postcommit hook SURVIVES a savepoint rollback:
`rollback()` calls `cr.clear()` (`odoo/sql_db.py`), and `clear()` drops only
the PREcommit callbacks. Guarding just the callers would still let a phase that
was rolled back fire at the hardware.

`hr.rfid.card.door.rel._mirrors_to_camera()` is the fifth guard, on the mirror
that pushes card-to-door changes into a camera's plate list. It is switched off
under the same context for a second reason as well as the traffic: the mirror
CREATES `cctv.camera.rfid.rel` rows of its own, which carry no source id, and
those collide with the ones the transfer brings across - afterwards nobody can
say which link is the real one.

This is `hr_rfid`'s own convention (`hr_rfid_door.py`), and **any new write in
an importer must carry the context**. The site phase originally did not, and
its access-group cascade reached live cameras through three separate paths.

Consequence, stated in both guides: after a transfer each camera still holds
the plate list it held before, and the operator has to reload them.

Tests: `tests/test_import_guards.py` - no commands during a transfer, none on
removal either, no manufactured readers, no invented card-camera links, and the
reverse: ordinary use still sends its commands unchanged.

## The self-test record (`cctv.camera.diagnostic`)

TransientModel holding the result of `cctv.camera.action_camera_diagnostics`
(the "Self-Test" button, `group_cctv_manager` only). The action runs the full
map of what the module uses from the camera - identity (`check_connection`,
serial compared against the record), snapshot, clock (read-only drift check
anchored in `camera.tz`), event destination (`get_http_host`), plate list
read (`search_lp_audit`, count vs `rfid_rel_ids`), the list schema as the
camera itself speaks it (`probe_vcl_capabilities` + `export_lp_list_xml` -
the export is written in exactly the schema the firmware's import accepts),
and one write round-trip with `DIAG_TEST_PLATE` ('TEST0001', added then
removed). When the minimal record passes but a record shaped like the real
data fails, the test bisects the shape (linked card number, 'Z'-suffixed
validity times, no times) and the report names the refused part, quoting the
camera verbatim. The clock check mirrors the heartbeat canon: the offset the
camera claims is dropped (the inverted Hikvision convention misstates it)
and the wall clock is compared in the camera's own zone, against the same
HEARTBEAT_CLOCK_DRIFT_TOLERANCE. The barrier is deliberately never
exercised. The report lives in the dialog only - the chatter is for
conversation, not for logs. Fields: `camera_id` (M2O `cctv.camera`),
`report` (Text).
