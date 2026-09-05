"""The read sequence for one module: enumerate its controllers, read each.

Only read commands are used (the allowlist in ``helpers/allowlist.py`` is the
proof); a command the controller does not know is recorded as a gap and the
reading continues. Card tables are read page by page with a cursor kept on the
controller row, so a pass that runs out of time resumes where it stopped.

Every finding this file raises carries ``phase='read'``: the analysis rebuilds
only its own findings, and reading a module again clears the read findings of
that module before the new ones are written.
"""
import json
import logging
import re
import time

from odoo import fields

from odoo.addons.hr_rfid.controllers.polimex import READ_CARDS_BLOCK_SIZE

from ..helpers import codecs, transport

_logger = logging.getLogger(__name__)

#: Reply codes that mean "this controller does not do that" rather than "failed".
GAP_CODES = (transport.E_UNKNOWN_COMMAND,)

#: Module firmware before this version reads the input/output table row by row.
IO_BY_ROW_BEFORE = (1, 40)


def setting_label(env, opcode):
    """What a read command is about, in the operator's words. The wire opcode
    stays in the command log; the findings talk about settings."""
    _ = env._
    return {
        'F0': _('system information'),
        'F2': _('card table'),
        'F3': _('time schedules'),
        'F4': _('holidays'),
        'F5': _('operating mode'),
        'F6': _('reader settings'),
        'F7': _('clock'),
        'F8': _('input/output settings'),
        'F9': _('input/output table'),
        'FB': _('input masks'),
        'FC': _('anti-passback settings'),
        'FF': _('output schedules'),
        'B0': _('alarm zone settings'),
        'B3': _('status'),
    }.get(opcode, _('a setting'))


def failure_label(env, e_code):
    """Why a controller command failed, in the operator's words; the wire code
    stays in the command log."""
    _ = env._
    return {
        transport.E_NO_RESPONSE: _('the controller did not answer'),
        transport.E_BUSY: _('the controller was busy'),
        transport.E_BAD_CRC: _('the reply arrived damaged'),
        transport.E_BRIDGE_ACTIVE: _("the module's bridge was in use by another tool"),
        transport.E_INTERNAL: _('the module reported an internal error'),
        transport.E_WRONG_VALUE: _('the controller refused the request'),
        transport.E_BAD_JSON: _('the module did not accept the request'),
    }.get(e_code, _('the controller answered with an error'))


def unreachable_label(env, exc):
    """Why a module could not be talked to, in the operator's words, with the
    next step; the technical text of the exception goes to the log."""
    _ = env._
    kind = getattr(exc, 'kind', 'network')
    if kind == 'password':
        return _("it requires a password, or the password is wrong; enter the password on the module's "
                 "row and check it again")
    if kind == 'http':
        return _('it answered with an error page instead of its interface')
    if kind in ('json', 'reply'):
        return _('it answered with something this system cannot read')
    return _('it did not answer; check the address, the network and that the module is powered')


class SurveyReader:
    def __init__(self, run, module, client):
        self.run = run
        self.module = module
        self.client = client
        self.env = run.env

    def _finding(self, kind, severity, message, **links):
        return self.run._log_issue(kind, severity, message, phase='read', **links)

    # ------------------------------------------------------------ module level

    def read(self, deadline):
        """Read what is left on this module. True when the module is finished."""
        module = self.module
        if module.read_state == 'failed':
            # Failed stays failed until the operator asks for it again; the
            # worker does not knock on a dead address every pass.
            return True
        if module.read_state == 'pending':
            module.write({'read_state': 'reading'})
        try:
            self._ensure_controllers()
        except transport.Unreachable as exc:
            _logger.warning("Hardware survey %s: module %s could not be read: %s",
                            self.run.id, module._display_address(), exc)
            self._fail_module(exc)
            return True
        for ctrl in module.ctrl_ids.sorted('address'):
            if ctrl.read_state in ('done', 'skipped', 'failed'):
                continue
            if not ctrl.include:
                ctrl.write({'read_state': 'skipped'})
                continue
            try:
                finished = self._read_ctrl(ctrl, deadline)
            except transport.Unreachable as exc:
                _logger.warning("Hardware survey %s: module %s stopped answering at controller %s: %s",
                                self.run.id, module._display_address(), ctrl.address, exc)
                self._fail_module(exc, ctrl=ctrl)
                return True
            except (transport.ReadFailed, ValueError) as exc:
                # ValueError covers every decoder: a reply of the wrong shape
                # fails this controller, never the whole survey.
                _logger.warning("Hardware survey %s: controller %s could not be read: %s",
                                self.run.id, ctrl.name, exc)
                self._fail_ctrl(ctrl, exc)
                continue
            if not finished or time.monotonic() > deadline:
                return False
        module.write({'read_state': 'done'})
        return True

    def _fail_module(self, exc, ctrl=None):
        module = self.module
        reason = unreachable_label(self.env, exc)
        if ctrl is not None:
            message = self.env._(
                "Module %(ip)s stopped answering while controller %(ctrl)s was being read: %(reason)s.",
                ip=module._display_address(), ctrl=ctrl.name, reason=reason)
        else:
            message = self.env._("Module %(ip)s could not be read: %(reason)s.",
                                 ip=module._display_address(), reason=reason)
        module.write({'read_state': 'failed', 'read_error': message})
        self._finding('warning', 'warning', message, module_id=module, ctrl_id=ctrl)

    def _fail_ctrl(self, ctrl, exc):
        e_code = getattr(exc, 'e_code', None)
        if e_code == transport.E_BAD_CRC:
            message = self.env._(
                "Controller %(ctrl)s answered with a damaged reply every time it was asked. "
                "This points at the wiring or the bus, not at the survey; check the device "
                "and read it again.", ctrl=ctrl.name)
        elif e_code is not None:
            message = self.env._("Controller %(ctrl)s could not be read: %(reason)s.",
                                 ctrl=ctrl.name, reason=failure_label(self.env, e_code))
        else:
            message = self.env._(
                "Controller %(ctrl)s answered with a reply this system could not read; the raw reply "
                "is in the command log.", ctrl=ctrl.name)
        ctrl.write({'read_state': 'failed', 'read_error': message})
        self._finding('warning', 'warning', message, module_id=self.module, ctrl_id=ctrl)

    def _ensure_controllers(self):
        """Create a row for every controller the module sees. No commands yet."""
        module = self.module
        dev_found = module.dev_found
        try:
            details = self.client.get_details()
            dev_found = int(details.get('devFound') or dev_found or 0)
        except transport.Unreachable as exc:
            # Older firmware has no details page; the configuration read at
            # discovery already told us how many controllers it sees. Anything
            # but "no such page" is a real failure.
            if exc.status != 404:
                raise
        if not dev_found and not module.ctrl_ids:
            self._finding('warning', 'warning', self.env._(
                "Module %(ip)s sees no controllers on its bus.", ip=module._display_address()),
                module_id=module)
            return
        known = {c.address: c for c in module.ctrl_ids}
        for dev in range(dev_found):
            status = self.client.get_status(dev)
            entry = status.get('dev') if isinstance(status.get('dev'), dict) else status
            try:
                address = int(entry.get('devID') or 0)
            except (TypeError, ValueError):
                address = 0
            if not address:
                self._finding('warning', 'warning', self.env._(
                    "Module %(ip)s lists a controller at position %(n)s without an address; it is "
                    "left out of the survey.", ip=module._display_address(), n=dev + 1), module_id=module)
                continue
            values = {
                'dev_index': dev,
                'hw_code': str(entry.get('devHardware') or '') or None,
                'sw_version': str(entry.get('devSoftware') or '') or None,
                'serial': str(entry.get('devSerial') or '') or None,
            }
            values = {k: v for k, v in values.items() if v is not None}
            if address in known:
                known[address].write(values)
            else:
                known[address] = self.env['hr.rfid.hw.import.ctrl'].create(dict(
                    values, run_id=self.run.id, module_id=module.id, address=address))

    # ------------------------------------------------------------ controller level

    def _cmd(self, ctrl, opcode, data='', tolerate_gap=True):
        """One command. Returns the reply data, or None when the controller does
        not support the command (a gap, recorded) or rejected the request (a
        warning, recorded). With ``tolerate_gap`` off both are failures."""
        relay = ctrl.family == 'relay'
        try:
            reply = self.client.cmd(ctrl.address, opcode, data, relay=relay).data
        except transport.CapabilityGap as gap:
            if not tolerate_gap:
                raise transport.ReadFailed(opcode, gap.e_code, ctrl.address)
            self._note_gap(ctrl, opcode, gap.e_code)
            return None
        except transport.ReadFailed as failed:
            if not tolerate_gap:
                raise
            if failed.e_code in GAP_CODES:
                self._note_gap(ctrl, opcode, failed.e_code)
                return None
            if failed.e_code == transport.E_WRONG_VALUE:
                # Not "does not support": the controller refused THIS request.
                self._finding('warning', 'warning', self.env._(
                    "%(ctrl)s refused the request for its %(setting)s; that setting is not part of "
                    "the survey.", ctrl=ctrl.name, setting=setting_label(self.env, opcode)), ctrl_id=ctrl)
                return None
            raise
        if not reply and tolerate_gap:
            # Success with nothing in it is not a setting; say so instead of
            # silently leaving the field empty.
            self._note_undecodable(ctrl, opcode, self.env._("the reply was empty"))
            return None
        return reply

    def _decoded(self, ctrl, opcode, data, decode):
        """``decode(data)``, or None with a finding when the reply does not have
        the documented shape: the raw reply stays as evidence on the controller
        row and in the command log, the setting is not imported."""
        try:
            return decode(data)
        except ValueError as exc:  # every decoder, DecodeError included
            _logger.warning("Hardware survey %s: controller %s, %s could not be decoded: %s",
                            self.run.id, ctrl.name, opcode, exc)
            self._note_undecodable(ctrl, opcode, self.env._("the reply does not have the expected shape"))
            return None

    def _unsupported(self, ctrl, opcode):
        return opcode in json.loads(ctrl.gaps_json or '[]')

    def _note_undecodable(self, ctrl, opcode, why):
        self._finding('warning', 'warning', self.env._(
            "%(ctrl)s answered the read of its %(setting)s with a reply this system could not "
            "interpret (%(why)s); the raw reply is kept but that setting is not imported.",
            ctrl=ctrl.name, setting=setting_label(self.env, opcode), why=why), ctrl_id=ctrl)

    def _note_gap(self, ctrl, opcode, e_code):
        gaps = json.loads(ctrl.gaps_json or '[]')
        if opcode not in gaps:
            gaps.append(opcode)
            ctrl.write({'gaps_json': json.dumps(gaps)})
        _logger.debug("Controller %s does not support %s (code %s)", ctrl.name, opcode, e_code)

    def _read_ctrl(self, ctrl, deadline):
        if ctrl.read_state == 'pending':
            if not self._read_identity(ctrl):
                return True
            if time.monotonic() > deadline:
                return False
        if ctrl.read_state == 'config':
            self._read_config(ctrl)
            ctrl.write({'read_state': 'cards' if ctrl.reads_cards else 'done',
                        'read_cursor': 1 if ctrl.reads_cards else -1, 'cards_read': 0})
            if not ctrl.reads_cards:
                return True
            if time.monotonic() > deadline:
                return False
        if ctrl.read_state == 'cards':
            return self._read_cards(ctrl, deadline)
        return True

    def _read_identity(self, ctrl):
        """System information first; it decides everything that follows."""
        data = self._cmd(ctrl, 'F0', tolerate_gap=False)
        dec = codecs.decode_f0(data)
        ctrl.write({
            'f0_hex': data,
            'hw_code': dec['hw_code'], 'serial': dec['serial'], 'sw_version': dec['sw_version'],
            'mode': dec['mode'], 'external_db': dec['external_db'], 'dual_person': dec['dual_person'],
            'interlocking': dec['interlocking'], 'relay_time_factor': dec['relay_time_factor'],
            'readers': dec['readers'], 'inputs': dec['inputs'], 'outputs': dec['outputs'],
            'time_schedules': dec['time_schedules'], 'io_table_lines': dec['io_table_lines'],
            'alarm_lines': dec['alarm_lines'], 'max_cards': dec['max_cards'], 'max_events': dec['max_events'],
            'record_size': codecs.record_size_of(dec['hw_code'], dec['alarm_lines']) or 0,
            'door_map_json': json.dumps(codecs.reader_door_map(dec['hw_code'], dec['mode'], dec['readers'])),
            'zone_map_json': json.dumps(codecs.zone_door_map(dec['alarm_lines'], dec['mode'])),
        })
        if ctrl.family == 'vending':
            ctrl.write({'include': False, 'read_state': 'skipped'})
            self._finding('report', 'info', self.env._(
                "%(ctrl)s is a vending machine controller and is left out of the survey.",
                ctrl=ctrl.name), module_id=self.module, ctrl_id=ctrl)
            return False
        if ctrl.family == 'unknown':
            self._finding('warning', 'warning', self.env._(
                "%(ctrl)s reports hardware type %(hw)s, which this system does not know; only its "
                "system information was read and it cannot be imported.", ctrl=ctrl.name, hw=ctrl.hw_code),
                module_id=self.module, ctrl_id=ctrl)
            ctrl.write({'read_state': 'done'})
            return False
        ctrl.write({'read_state': 'config'})
        return True

    def _module_reads_io_by_row(self):
        module = self.module
        if module.hw_version == '10.3':
            return True
        version = re.match(r'(\d+)\.(\d+)', module.fw_version or '')
        if not version:
            # Unknown firmware version: the whole-table read, which every
            # current module supports; older ones refuse it and say so.
            return False
        return (int(version.group(1)), int(version.group(2))) < IO_BY_ROW_BEFORE

    def _read_config(self, ctrl):
        values = {}
        card_family = ctrl.family in codecs.CARD_FAMILIES

        data = self._cmd(ctrl, 'F5')
        if data:
            values['f5_hex'] = data
            mode = self._decoded(ctrl, 'F5', data, codecs.decode_f5)
            if mode is not None and mode['mode'] != ctrl.mode:
                self._finding('warning', 'warning', self.env._(
                    "%(ctrl)s reports mode %(f5)s in one reply and %(f0)s in another; the system "
                    "information reply is used.", ctrl=ctrl.name, f5=mode['mode'], f0=ctrl.mode), ctrl_id=ctrl)

        if ctrl.readers:
            data = self._cmd(ctrl, 'F6')
            if data:
                values['f6_hex'] = data
                modes = self._decoded(ctrl, 'F6', data, codecs.decode_reader_modes)
                if modes is not None:
                    values['reader_modes_json'] = json.dumps(modes)

        data = self._cmd(ctrl, 'F8')
        if data:
            values['f8_hex'] = data

        data = self._cmd(ctrl, 'FB')
        if data:
            values['fb_hex'] = data
            masks = self._decoded(ctrl, 'FB', data, codecs.decode_input_masks)
            if masks is not None:
                mask, relay_bytes = masks
                values['input_mask'] = mask
                values['output_relay_mask'] = 0x7F in relay_bytes

        if card_family:
            data = self._cmd(ctrl, 'FC')
            if data:
                values['fc_hex'] = data
                apb = self._decoded(ctrl, 'FC', data, codecs.decode_apb)
                if apb is not None:
                    values['apb_bitmap'] = apb

        if ctrl.outputs and ctrl.family != 'vending':
            data = self._cmd(ctrl, 'FF')
            if data:
                values['ff_hex'] = data
                out_ts = self._decoded(ctrl, 'FF', data, lambda d: codecs.decode_output_ts(d, ctrl.outputs))
                if out_ts is not None:
                    values['out_ts_json'] = json.dumps(out_ts)

        if ctrl.io_table_lines:
            if self._module_reads_io_by_row():
                rows = []
                for row in range(1, ctrl.io_table_lines + 1):
                    data = self._cmd(ctrl, 'F9', '%02X' % row)
                    if data is None:
                        # What was read stays as evidence; the table is incomplete.
                        self._finding('warning', 'warning', self.env._(
                            "%(ctrl)s did not return row %(row)s of its input/output table; the rows "
                            "read before it are kept but the table is not imported.",
                            ctrl=ctrl.name, row=row), ctrl_id=ctrl)
                        break
                    rows.append(data)
                table = ''.join(rows)
            else:
                table = self._cmd(ctrl, 'F9', '00') or ''
            values['f9_hex'] = table
            if codecs.io_table_is_complete(table, ctrl.io_table_lines):
                values['io_table_hex'] = table.upper()
            elif table:
                self._finding('warning', 'warning', self.env._(
                    "%(ctrl)s returned an input/output table of an unexpected size; it is kept as "
                    "evidence but not imported.", ctrl=ctrl.name), ctrl_id=ctrl)

        if ctrl.alarm_lines:
            data = self._cmd(ctrl, 'B0', '01')
            if data:
                values['b0_hex'] = data
                setup = self._decoded(ctrl, 'B0', data, codecs.decode_alarm_setup)
                if setup is not None:
                    values['alarm_setup_json'] = json.dumps(setup)

        if ctrl.time_schedules and (card_family or ctrl.family == 'relay'):
            self._read_schedules(ctrl)

        if card_family:
            holidays = {}
            for slot in range(1, 9):
                data = self._cmd(ctrl, 'F4', '%02X' % slot)
                if data is None:
                    if self._unsupported(ctrl, 'F4'):
                        break
                    continue
                dates = self._decoded(ctrl, 'F4', data, codecs.decode_holidays)
                if dates is not None:
                    holidays[slot] = dates['dates']
            if holidays:
                values['holidays_json'] = json.dumps(holidays)

        data = self._cmd(ctrl, 'F7')
        if data:
            values['f7_hex'] = data
            clock = self._decoded(ctrl, 'F7', data, codecs.decode_clock)
            if clock is not None:
                values['clock_read'] = clock
                drift = int((clock - fields.Datetime.now()).total_seconds())
                values['clock_drift_seconds'] = drift
                if abs(drift) > 120:
                    self._finding('warning', 'warning', self.env._(
                        "The clock of %(ctrl)s differs from this server's by %(seconds)s seconds.",
                        ctrl=ctrl.name, seconds=drift), ctrl_id=ctrl)

        data = self._cmd(ctrl, 'B3')
        if data:
            values['b3_hex'] = data
            status = self._decoded(ctrl, 'B3', data, codecs.decode_status)
            if status is not None:
                values['status_json'] = json.dumps(status)

        ctrl.write(values)

    def _read_schedules(self, ctrl):
        ts_env = self.env['hr.rfid.hw.import.ts']
        existing = {t.number: t for t in ctrl.ts_ids}
        slots = min(ctrl.time_schedules or 0, 15)
        for slot in range(1, slots + 1):
            data = self._cmd(ctrl, 'F3', '%02X' % slot)
            if data is None:
                if self._unsupported(ctrl, 'F3'):
                    break
                continue
            try:
                dec = codecs.decode_ts(data)
            except ValueError as exc:  # every decoder, DecodeError included
                _logger.warning("Hardware survey %s: controller %s, schedule slot %s could not be decoded: %s",
                                self.run.id, ctrl.name, slot, exc)
                self._finding('warning', 'warning', self.env._(
                    "%(ctrl)s returned an unreadable schedule in slot %(slot)s; the raw reply is in the "
                    "command log.", ctrl=ctrl.name, slot=slot), ctrl_id=ctrl)
                continue
            values = {
                'run_id': self.run.id, 'ctrl_id': ctrl.id, 'number': slot,
                'raw_hex': dec['ts_data'], 'week_fingerprint': dec['week_fingerprint'],
                'holiday_ref': dec['holiday_ref'], 'is_empty': dec['is_empty'], 'summary': dec['summary'],
            }
            if slot in existing:
                existing[slot].write(values)
            else:
                ts_env.create(values)

    # ------------------------------------------------------------ cards

    def _read_cards(self, ctrl, deadline):
        if ctrl.read_cursor == 1 and not ctrl.cards_read:
            data = self._cmd(ctrl, 'F2', codecs.encode_f2_count(), tolerate_gap=False)
            count = codecs.decode_f2_count(data)
            if ctrl.max_cards and count > ctrl.max_cards:
                # A garbled count must not turn into thousands of requests on a
                # live bus; the controller cannot hold more than it says it can.
                self._finding('warning', 'warning', self.env._(
                    "%(ctrl)s reports %(count)s cards but can hold at most %(max)s; only the first "
                    "%(max)s are read.", ctrl=ctrl.name, count=count, max=ctrl.max_cards), ctrl_id=ctrl)
                count = ctrl.max_cards
            ctrl.write({'card_count_device': count})
        count = ctrl.card_count_device
        position = ctrl.read_cursor
        cards_read = ctrl.cards_read
        record_size = ctrl.record_size or codecs.CARD_RECORD_BASE_SIZE
        while position <= count:
            page_size = min(READ_CARDS_BLOCK_SIZE, count - position + 1)
            data = self._cmd(ctrl, 'F2', codecs.encode_f2_page(position, page_size), tolerate_gap=False)
            if not data:
                # Nothing for a page inside the range the controller announced:
                # the table read is incomplete, and an incomplete card table
                # must not be imported as if it were the whole one.
                message = self.env._(
                    "%(ctrl)s announced %(count)s cards but returned nothing from position %(pos)s; "
                    "its card table is incomplete. Read it again.",
                    ctrl=ctrl.name, count=count, pos=position)
                self._finding('warning', 'warning', message, ctrl_id=ctrl)
                ctrl.write({'read_cursor': position, 'cards_read': cards_read,
                            'read_state': 'failed', 'read_error': message})
                return True
            records = codecs.decode_cards_page(data, record_size)
            self._store_records(ctrl, records, position)
            cards_read += len(records)
            position += page_size
            if time.monotonic() > deadline:
                ctrl.write({'read_cursor': position, 'cards_read': cards_read})
                return False
        if cards_read < count:
            self._finding('warning', 'warning', self.env._(
                "%(ctrl)s announced %(count)s cards; %(read)s card records were found in its table.",
                ctrl=ctrl.name, count=count, read=cards_read), ctrl_id=ctrl)
        ctrl.write({'read_cursor': -1, 'cards_read': cards_read, 'read_state': 'done'})
        return True

    def _store_records(self, ctrl, records, first_position):
        card_env = self.env['hr.rfid.hw.import.card']
        record_env = self.env['hr.rfid.hw.import.card.record']
        numbers = [rec['number'] for rec in records if rec['number']]
        cards = {c.number: c for c in card_env.search([('run_id', '=', self.run.id), ('number', 'in', numbers)])}
        stored = {r.card_id.id: r for r in record_env.search(
            [('ctrl_id', '=', ctrl.id), ('card_id', 'in', [c.id for c in cards.values()])])}
        for rec in records:
            position = first_position + rec['index']
            if not rec['number']:
                self._finding('anomaly', 'warning', self.env._(
                    "%(ctrl)s holds a card record at position %(pos)s whose number is not readable; "
                    "it is left out.", ctrl=ctrl.name, pos=position), ctrl_id=ctrl)
                continue
            card = cards.get(rec['number'])
            if not card:
                card = card_env.create({
                    'run_id': self.run.id, 'number': rec['number'],
                    'number_display': self.run._display_number(rec['number']),
                })
                cards[rec['number']] = card
            values = {
                'position': position, 'raw_hex': rec['raw_hex'], 'pin': rec['pin'],
                'ts_r1': rec['ts'][0], 'ts_r2': rec['ts'][1], 'ts_r3': rec['ts'][2], 'ts_r4': rec['ts'][3],
                'rights': rec['rights'], 'apb1': rec['apb1'], 'apb2': rec['apb2'],
                'alarm_bits': rec['alarm_bits'], 'anomaly': rec['anomaly'],
            }
            existing = stored.get(card.id)
            if existing:
                # The same card twice in one table (a hand-added duplicate on
                # the old system). The later record wins, and it is said when
                # the two disagree on what the card may do.
                differs = any(existing[key] != values[key]
                              for key in ('pin', 'ts_r1', 'ts_r2', 'ts_r3', 'ts_r4', 'rights', 'alarm_bits'))
                if differs and existing.raw_hex != values['raw_hex']:
                    self._finding('anomaly', 'warning', self.env._(
                        "%(ctrl)s holds card %(number)s twice, with different rights; the later record "
                        "(position %(pos)s) is used.", ctrl=ctrl.name, number=card.number_display,
                        pos=position), ctrl_id=ctrl, card_id=card)
                    values['anomaly'] = 'duplicate'
                existing.write(values)
            else:
                stored[card.id] = record_env.create(dict(values, card_id=card.id, ctrl_id=ctrl.id))
