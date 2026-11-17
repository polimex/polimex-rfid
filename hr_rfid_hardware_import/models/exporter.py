"""Everything a survey read, as a file the operator can take away.

The survey of a working site is worth keeping on its own: as a record of what
the controllers held on that day, as input for another system, or for an
import done later. Nothing here touches the hardware or creates a record in
the access control module; it only writes what the survey already holds.

Two shapes: an Excel workbook, one sheet per kind of thing, readable by a
person; and a JSON document with the same content plus every raw reply, for
a machine.
"""

import io
import json

import xlsxwriter

from odoo.exceptions import UserError

from ..helpers import codecs
from .reader import selection_label, setting_label

#: Bumped when the JSON shape changes in a way a reader has to know about.
FORMAT_VERSION = "hr_rfid_hardware_import/1"

#: The most text one workbook cell holds (xlsxwriter ``Worksheet.xls_strmax``);
#: a longer text is cut by the library and only a return code says so.
CELL_MAX_LENGTH = 32767

#: The raw replies kept on a controller row, in the order they are read.
RAW_FIELDS = (
    "f0_hex",
    "f5_hex",
    "f6_hex",
    "f8_hex",
    "fb_hex",
    "fc_hex",
    "ff_hex",
    "f9_hex",
    "b0_hex",
    "f7_hex",
    "b3_hex",
    "io_table_hex",
)


def _loads(text, default):
    return json.loads(text) if text else default


class SurveyExporter:
    def __init__(self, run, include_commands=False):
        self.run = run
        self.env = run.env
        self.include_commands = include_commands
        self._ctrl_by_id = {c.id: c for c in run.ctrl_ids}

    # ------------------------------------------------------------ words

    def _door_label(self, right):
        ctrl = self._ctrl_by_id.get(right.get("ctrl"))
        return self.env._(
            "%(ctrl)s door %(door)s",
            ctrl=ctrl.name if ctrl else right.get("serial") or "?",
            door=right.get("door"),
        )

    def _right_words(self, right):
        words = self._door_label(right)
        if right.get("ts"):
            words += " " + self.env._("(schedule %(n)s)", n=right["ts"])
        else:
            words += " " + self.env._("(always)")
        if right.get("alarm"):
            words += " " + self.env._("+ alarm")
        return words

    # ------------------------------------------------------------ the data

    def data(self):
        """The whole survey as plain dicts and lists (the JSON document)."""
        run = self.run
        return {
            "format": FORMAT_VERSION,
            "survey": {
                "name": run.name,
                "company": run.company_id.name,
                "card_number_format": run.company_id.card_input_type or "w34",
                "network_searched_on": run.discovered_at
                and run.discovered_at.isoformat(),
                "controllers_read_on": run.read_at and run.read_at.isoformat(),
                "state": run.state,
            },
            "modules": [self._module(module) for module in run.module_ids],
            "cards": [self._card(card) for card in run.card_ids],
            "people": [
                {
                    "name": person.name,
                    "source": person.source,
                    "create_as": person.owner_type,
                    "cards": person.card_ids.mapped("number"),
                    "pin": person.pin or "",
                    "review": person.review_state,
                }
                for person in run.person_ids
            ],
            "access_groups": [
                {
                    "name": group.name,
                    "include": group.include,
                    "cards": group.card_ids.mapped("number"),
                    "rights": [
                        {
                            "controller": right.ctrl_id.name,
                            "controller_serial": right.ctrl_id.serial or "",
                            "door": right.door_number,
                            "schedule": right.ts_number,
                            "alarm": right.alarm,
                        }
                        for right in group.right_ids
                    ],
                }
                for group in run.group_ids
            ],
            "schedule_slots": [
                {
                    "slot": slot.number,
                    "in_words": slot.summary or "",
                    "versions": slot.variant_count,
                    "used_by_rights": slot.used_by_rights,
                    "state": slot.state,
                    "taken_from": slot.source_ctrl_id.name or "",
                }
                for slot in run.ts_slot_ids
            ],
            "findings": [
                {
                    "phase": issue.phase,
                    "severity": issue.severity,
                    "kind": issue.kind,
                    "message": issue.message,
                }
                for issue in run.issue_ids
            ],
            "commands": [
                {
                    "module": log.module_id._display_address(),
                    "controller": log.address,
                    "command": log.opcode,
                    "parameters": log.data_sent or "",
                    "reply_code": log.e_code,
                    "reply_time_ms": log.duration_ms,
                    "attempt": log.attempt,
                    "reply": log.response_hex or "",
                }
                for log in run.cmd_log_ids
            ]
            if self.include_commands
            else None,
        }

    def _module(self, module):
        return {
            "address": module._display_address(),
            "name": module.hostname or "",
            "mac": module.mac or "",
            "serial": module.serial or "",
            "hardware_version": module.hw_version or "",
            "firmware": module.fw_version or "",
            "controllers_seen": module.dev_found,
            "reports_to": module.server_url or "",
            "status": module.status,
            "reading": module.read_state,
            "reading_problem": module.read_error or "",
            "configuration": _loads(module.config_json, {}),
            "controllers": [self._controller(ctrl) for ctrl in module.ctrl_ids],
        }

    def _controller(self, ctrl):
        return {
            "address": ctrl.address,
            "name": ctrl.name,
            "hardware_code": ctrl.hw_code or "",
            "hardware": ctrl.hw_name or "",
            "kind": ctrl.family,
            "serial": ctrl.serial or "",
            "firmware": ctrl.sw_version or "",
            "mode": ctrl.mode,
            "readers": ctrl.readers,
            "inputs": ctrl.inputs,
            "outputs": ctrl.outputs,
            "schedule_slots": ctrl.time_schedules,
            "io_table_rows": ctrl.io_table_lines,
            "alarm_zones": ctrl.alarm_lines,
            "card_capacity": ctrl.max_cards,
            "event_capacity": ctrl.max_events,
            "asks_server_for_unknown_cards": ctrl.external_db,
            "two_cards_to_open": ctrl.dual_person,
            "interlocked_doors": ctrl.interlocking,
            "relay_times_in_tenths": ctrl.relay_time_factor,
            "readers_per_door": _loads(ctrl.door_map_json, {}),
            "alarm_zones_per_door": _loads(ctrl.zone_map_json, {}),
            "reader_settings": _loads(ctrl.reader_modes_json, []),
            "input_mask": ctrl.input_mask,
            "relay_output_mask": ctrl.output_relay_mask,
            "anti_passback": {
                "readers_1_and_2": bool(ctrl.apb_bitmap & codecs.APB_PAIR_R1_R2),
                "readers_3_and_4": bool(ctrl.apb_bitmap & codecs.APB_PAIR_R3_R4),
                "one_zone_for_both_pairs": bool(
                    ctrl.apb_bitmap & codecs.APB_COMMON_ZONE
                ),
            },
            "output_schedules": _loads(ctrl.out_ts_json, []),
            "alarm_zone_settings": _loads(ctrl.alarm_setup_json, {}),
            "holiday_lists": _loads(ctrl.holidays_json, {}),
            "status": _loads(ctrl.status_json, {}),
            "clock": ctrl.clock_read and ctrl.clock_read.isoformat(),
            "clock_difference_seconds": ctrl.clock_drift_seconds,
            "settings_not_reported": [
                setting_label(self.env, code) for code in _loads(ctrl.gaps_json, [])
            ],
            "cards_on_device": ctrl.card_count_device,
            "cards_read": ctrl.cards_read,
            "reading": ctrl.read_state,
            "reading_problem": ctrl.read_error or "",
            "raw": {
                name[:-4] if name.endswith("_hex") else name: ctrl[name] or ""
                for name in RAW_FIELDS
            },
            "schedules": [
                {
                    "slot": ts.number,
                    "in_words": ts.summary or "",
                    "empty": ts.is_empty,
                    "holiday_list": ts.holiday_ref,
                    "schedule": ts.raw_hex or "",
                }
                for ts in ctrl.ts_ids
            ],
            "card_records": [
                {
                    "position": rec.position,
                    "number": rec.card_id.number,
                    "number_display": rec.card_id.number_display,
                    "pin": rec.pin or "",
                    "schedule_per_reader": [rec.ts_r1, rec.ts_r2, rec.ts_r3, rec.ts_r4],
                    "readers_accepting": rec.rights,
                    "alarm_zones": rec.alarm_bits,
                    "anti_passback_state": [rec.apb1, rec.apb2],
                    "unusual": rec.anomaly or "",
                    "record": rec.raw_hex or "",
                }
                for rec in ctrl.card_record_ids
            ],
        }

    def _card(self, card):
        return {
            "number": card.number,
            "number_display": card.number_display,
            "pin": card.pin or "",
            "pin_codes_differ": card.pin_mismatch,
            "unusual": card.anomaly,
            "person": card.person_id.name or "",
            "person_source": card.person_id.source or "",
            "doors": [
                {
                    "controller": self._ctrl_by_id[r["ctrl"]].name
                    if r.get("ctrl") in self._ctrl_by_id
                    else "",
                    "controller_serial": r.get("serial", ""),
                    "door": r["door"],
                    "schedule": r["ts"],
                    "alarm": bool(r.get("alarm")),
                    "readers": r.get("readers", []),
                    "partial": bool(r.get("partial")),
                }
                for r in _loads(card.door_rights_json, [])
            ],
            "access_groups": card.group_ids.mapped("name"),
        }

    def json_bytes(self):
        # Encoded piece by piece into one buffer: a large site's document is
        # never held as a whole text and as its bytes at the same time.
        output = io.BytesIO()
        for chunk in json.JSONEncoder(ensure_ascii=False, indent=2).iterencode(
            self.data()
        ):
            output.write(chunk.encode("utf-8"))
        return output.getvalue()

    # ------------------------------------------------------------ the workbook

    def xlsx_bytes(self):
        run = self.run
        output = io.BytesIO()
        book = xlsxwriter.Workbook(output, {"in_memory": True})
        bold = book.add_format({"bold": True, "bg_color": "#e9ecef", "text_wrap": True})

        def sheet(title, headers, rows):
            ws = book.add_worksheet(title[:31])
            rows = list(rows)
            limit = ws.xls_rowmax - 1  # row 0 is the header
            if len(rows) > limit:
                # A sheet holds a limited number of rows; the rest would be
                # dropped without a word. Refused instead, as the core's own
                # export does (web/controllers/export.py).
                raise UserError(
                    self.env._(
                        "The sheet '%(sheet)s' would have %(count)s rows; an Excel sheet holds at most %(limit)s. "
                        "Export as JSON instead; it has no such limit.",
                        sheet=title,
                        count=len(rows),
                        limit=limit,
                    )
                )
            for col, header in enumerate(headers):
                ws.write(0, col, header, bold)
            for r, row in enumerate(rows, start=1):
                for col, value in enumerate(row):
                    if value is None or value is False:
                        continue
                    if ws.write(r, col, value) < 0:
                        # Cut by the library without an exception: refused, so
                        # that the workbook never holds less than it seems to.
                        raise UserError(
                            self.env._(
                                "A value in the sheet '%(sheet)s' is too long for an Excel cell. Export as JSON "
                                "instead; it has no such limit.",
                                sheet=title,
                            )
                        )
            ws.freeze_panes(1, 0)
            return ws

        sheet(
            self.env._("Modules"),
            [
                self.env._("Address"),
                self.env._("Serial number"),
                self.env._("Name"),
                self.env._("Hardware version"),
                self.env._("Firmware"),
                self.env._("Controllers seen"),
                self.env._("Status"),
                self.env._("Reports to today"),
                self.env._("Reading"),
                self.env._("Reading problem"),
            ],
            [
                [
                    m._display_address(),
                    m.serial,
                    m.hostname,
                    m.hw_version,
                    m.fw_version,
                    m.dev_found,
                    selection_label(m, "status"),
                    m.server_url,
                    selection_label(m, "read_state"),
                    m.read_error,
                ]
                for m in run.module_ids
            ],
        )
        sheet(
            self.env._("Controllers"),
            [
                self.env._("Module"),
                self.env._("Address on the bus"),
                self.env._("Controller"),
                self.env._("Hardware"),
                self.env._("Kind"),
                self.env._("Serial number"),
                self.env._("Firmware"),
                self.env._("Operating mode"),
                self.env._("Readers"),
                self.env._("Inputs"),
                self.env._("Outputs"),
                self.env._("Schedule slots"),
                self.env._("Alarm zones"),
                self.env._("Card capacity"),
                self.env._("Cards on the device"),
                self.env._("Cards read"),
                self.env._("Controller clock"),
                self.env._("Clock difference (seconds)"),
                self.env._("Settings the controller cannot report"),
                self.env._("Reading"),
                self.env._("Reading problem"),
            ],
            [
                [
                    c.module_id._display_address(),
                    c.address,
                    c.name,
                    c.hw_name,
                    selection_label(c, "family"),
                    c.serial,
                    c.sw_version,
                    c.mode,
                    c.readers,
                    c.inputs,
                    c.outputs,
                    c.time_schedules,
                    c.alarm_lines,
                    c.max_cards,
                    c.card_count_device,
                    c.cards_read,
                    c.clock_read and c.clock_read.isoformat(" "),
                    c.clock_drift_seconds,
                    ", ".join(
                        setting_label(self.env, code)
                        for code in _loads(c.gaps_json, [])
                    ),
                    selection_label(c, "read_state"),
                    c.read_error,
                ]
                for c in run.ctrl_ids
            ],
        )
        sheet(
            self.env._("Schedules"),
            [
                self.env._("Controller"),
                self.env._("Slot"),
                self.env._("In words"),
                self.env._("Empty"),
                self.env._("Holiday list"),
                self.env._("Schedule (raw)"),
            ],
            [
                [
                    ts.ctrl_id.name,
                    ts.number,
                    ts.summary,
                    ts.is_empty,
                    ts.holiday_ref,
                    ts.raw_hex,
                ]
                for ts in run.ctrl_ids.mapped("ts_ids")
            ],
        )
        sheet(
            self.env._("Cards"),
            [
                self.env._("Card number"),
                self.env._("Number (as stored)"),
                self.env._("PIN"),
                self.env._("Person"),
                self.env._("Source"),
                self.env._("Doors opened"),
                self.env._("Unusual"),
                self.env._("Access groups"),
            ],
            [
                [
                    card.number_display,
                    card.number,
                    card.pin,
                    card.person_id.name,
                    selection_label(card.person_id, "source") if card.person_id else "",
                    "; ".join(
                        self._right_words(r) for r in _loads(card.door_rights_json, [])
                    ),
                    selection_label(card, "anomaly") if card.anomaly != "none" else "",
                    ", ".join(card.group_ids.mapped("name")),
                ]
                for card in run.card_ids
            ],
        )
        sheet(
            self.env._("Card records"),
            [
                self.env._("Controller"),
                self.env._("Position in the table"),
                self.env._("Card number"),
                self.env._("PIN"),
                self.env._("Schedule, reader 1"),
                self.env._("Schedule, reader 2"),
                self.env._("Schedule, reader 3"),
                self.env._("Schedule, reader 4"),
                self.env._("Readers accepting the card"),
                self.env._("Alarm zones"),
                self.env._("Anti-passback state 1"),
                self.env._("Anti-passback state 2"),
                self.env._("Unusual"),
                self.env._("Record (raw)"),
            ],
            [
                [
                    rec.ctrl_id.name,
                    rec.position,
                    rec.card_id.number_display,
                    rec.pin,
                    rec.ts_r1,
                    rec.ts_r2,
                    rec.ts_r3,
                    rec.ts_r4,
                    rec.rights,
                    rec.alarm_bits,
                    rec.apb1,
                    rec.apb2,
                    rec.anomaly,
                    rec.raw_hex,
                ]
                for rec in run.ctrl_ids.mapped("card_record_ids")
            ],
        )
        sheet(
            self.env._("Access groups"),
            [
                self.env._("Name"),
                self.env._("Include"),
                self.env._("Number of cards"),
                self.env._("Number of doors"),
                self.env._("Rights"),
                self.env._("Card numbers"),
            ],
            [
                [
                    g.name,
                    g.include,
                    g.card_count,
                    g.door_count,
                    "; ".join(
                        r.door_label + (" " + self.env._("+ alarm") if r.alarm else "")
                        for r in g.right_ids
                    ),
                    self._card_list(g),
                ]
                for g in run.group_ids
            ],
        )
        sheet(
            self.env._("People"),
            [
                self.env._("Name"),
                self.env._("Source"),
                self.env._("Create as"),
                self.env._("Number of cards"),
                self.env._("Card numbers"),
                self.env._("PIN"),
                self.env._("Review"),
            ],
            [
                [
                    p.name,
                    selection_label(p, "source"),
                    selection_label(p, "owner_type"),
                    p.card_count,
                    ", ".join(p.card_ids.mapped("number_display")),
                    p.pin,
                    selection_label(p, "review_state"),
                ]
                for p in run.person_ids
            ],
        )
        sheet(
            self.env._("Findings"),
            [
                self.env._("Phase"),
                self.env._("Severity"),
                self.env._("Kind"),
                self.env._("Message"),
            ],
            [
                [
                    selection_label(i, "phase"),
                    selection_label(i, "severity"),
                    selection_label(i, "kind"),
                    i.message,
                ]
                for i in run.issue_ids
            ],
        )
        sheet(
            self.env._("Raw replies"),
            [
                self.env._("Controller"),
                self.env._("Setting"),
                self.env._("Reply (raw)"),
            ],
            [
                [c.name, self._raw_label(name), c[name]]
                for c in run.ctrl_ids
                for name in RAW_FIELDS
                if c[name]
            ],
        )
        if self.include_commands:
            sheet(
                self.env._("Commands"),
                [
                    self.env._("Module"),
                    self.env._("Controller address"),
                    self.env._("Command"),
                    self.env._("Parameters"),
                    self.env._("Reply code"),
                    self.env._("Reply time (ms)"),
                    self.env._("Attempt"),
                    self.env._("Reply (raw)"),
                ],
                [
                    [
                        log.module_id._display_address(),
                        log.address,
                        log.opcode,
                        log.data_sent,
                        log.e_code,
                        log.duration_ms,
                        log.attempt,
                        log.response_hex,
                    ]
                    for log in run.cmd_log_ids
                ],
            )
        book.close()
        return output.getvalue()

    def _card_list(self, group):
        """The cards of a group for its cell; a group too large for one cell
        is given as a count, since the Cards sheet names the groups of every card."""
        numbers = ", ".join(group.card_ids.mapped("number_display"))
        if len(numbers) <= CELL_MAX_LENGTH:
            return numbers
        return self.env._(
            "%(n)s cards; the Cards sheet gives the groups of every card.",
            n=len(group.card_ids),
        )

    def _raw_label(self, name):
        if name == "io_table_hex":
            return self.env._("input/output table")
        return setting_label(self.env, name[:2].upper())
