"""What the survey concludes from what it read: rights, groups, schedules,
people and conflicts. Pure database work; no command is sent from here.

The analysis can run more than once on a survey (after a names file, after a
module was read again). It rebuilds only its own findings and keeps what the
operator decided: the resolution of every conflict, the controller chosen for
a schedule slot, the name given to a proposed group. What was found while
reading (``phase='read'``) is never touched here.
"""
import hashlib
import json

from ..helpers import codecs
from .reader import setting_label

#: Conflict findings whose resolution is the operator's decision to keep.
CONFLICT_KINDS = ('conflict_webstack', 'conflict_ctrl', 'conflict_card')


def _fingerprint(items):
    return hashlib.sha1(json.dumps(sorted(items)).encode()).hexdigest()


class SurveyAnalyser:
    def __init__(self, run):
        self.run = run
        self.env = run.env

    def _finding(self, kind, severity, message, **links):
        return self.run._log_issue(kind, severity, message, phase='analysis', **links)

    # ------------------------------------------------------------ entry points

    def analyse(self):
        run = self.run
        decisions = self._remember_decisions()
        run.issue_ids.filtered(lambda i: i.phase == 'analysis' and i.kind != 'decision').unlink()
        self._card_rights()
        self._groups(decisions['groups'])
        self._slots(decisions['slots'])
        self._placeholders()
        self._conflicts(decisions['resolutions'])
        self._gaps()

    def _remember_decisions(self):
        """Everything the operator decided on the rows the analysis is about to
        rebuild, keyed by what identifies the row across analyses."""
        run = self.run
        resolutions = {}
        for issue in run.issue_ids.filtered(lambda i: i.kind in CONFLICT_KINDS and i.resolution != 'none'):
            resolutions[(issue.kind, issue.module_id.id, issue.ctrl_id.id, issue.card_id.id)] = issue.resolution
        slots = {slot.number: (slot.source_ctrl_id.id, slot.keep_existing, slot.decision_note)
                 for slot in run.ts_slot_ids if slot.source_ctrl_id or slot.keep_existing or slot.decision_note}
        groups = {group.holder_key: (group.name, group.include, group.merged_from_json)
                  for group in run.group_ids}
        return {'resolutions': resolutions, 'slots': slots, 'groups': groups}

    def apply_names(self, rows):
        """Match the lines of a names file to the surveyed cards; rebuild the people.

        ``rows`` is a list of (row_number, name, card number) as read from the
        file. Matching is by card number only. Identical names (after
        normalising spaces and case) become one person with several cards,
        flagged for review so the operator can split them.
        """
        run = self.run
        run.name_line_ids.unlink()
        run.person_ids.filtered(lambda p: p.source == 'file').unlink()
        cards_by_number = {c.number: c for c in run.card_ids}
        seen_numbers = set()
        lines = []
        for row_number, name, number_raw in rows:
            values = {'run_id': run.id, 'row_number': row_number, 'name_raw': name or '',
                      'number_raw': str(number_raw or '')}
            norm = codecs.normalise_card_number(number_raw)
            if not norm or not (name or '').strip():
                values.update(status='invalid', note=self.env._('The line has no usable name or card number.'))
                lines.append(values)
                continue
            values['number_norm'] = norm
            card = cards_by_number.get(norm)
            if not card:
                converted = codecs.w34s_to_internal(norm)
                if converted and converted in cards_by_number:
                    card = cards_by_number[converted]
                    values['number_norm'] = converted
                    values['note'] = self.env._('Matched after converting the number to the form the readers report.')
            if not card:
                values.update(status='unmatched', note=self.env._('No controller holds this card.'))
                lines.append(values)
                continue
            if card.number in seen_numbers:
                values.update(status='duplicate', card_id=card.id,
                              note=self.env._('This card number appears earlier in the file; the first line is used.'))
                lines.append(values)
                continue
            seen_numbers.add(card.number)
            values.update(status='matched', card_id=card.id)
            lines.append(values)
        name_env = self.env['hr.rfid.hw.import.name']
        created = name_env.create(lines)
        person_env = self.env['hr.rfid.hw.import.person']
        by_key = {}
        for line in created.filtered(lambda l: l.status == 'matched'):
            key = codecs.normalise_name(line.name_raw)
            by_key.setdefault(key, []).append(line)
        for key, key_lines in by_key.items():
            person = person_env.create({
                'run_id': run.id, 'name': ' '.join(key_lines[0].name_raw.split()), 'name_key': key,
                'source': 'file', 'owner_type': run.placeholder_owner_type, 'merged': len(key_lines) > 1,
            })
            for line in key_lines:
                line.write({'person_id': person.id})
                line.card_id.write({'person_id': person.id})
        self._placeholders()
        self._person_pins()
        return {
            'matched': len(created.filtered(lambda l: l.status == 'matched')),
            'unmatched': len(created.filtered(lambda l: l.status == 'unmatched')),
            'duplicate': len(created.filtered(lambda l: l.status == 'duplicate')),
            'invalid': len(created.filtered(lambda l: l.status == 'invalid')),
            'merged': len([p for p in by_key.values() if len(p) > 1]),
        }

    # ------------------------------------------------------------ cards -> rights

    def _card_rights(self):
        for card in self.run.card_ids:
            rights = []
            apb = {}
            anomalies = set()
            pins = set()
            for record in card.record_ids:
                ctrl = record.ctrl_id
                if not ctrl.include or ctrl.family not in codecs.CARD_FAMILIES:
                    continue
                if record.pin:
                    pins.add(record.pin)
                door_map = ctrl._door_map()
                zone_map = ctrl._zone_map()
                ts_by_reader = {1: record.ts_r1, 2: record.ts_r2, 3: record.ts_r3, 4: record.ts_r4}
                apb[str(ctrl.id)] = {'apb1': record.apb1, 'apb2': record.apb2}
                if record.anomaly:
                    anomalies.add(record.anomaly)
                for door, readers in door_map.items():
                    with_bit = [r for r in readers if (record.rights >> (r - 1)) & 1]
                    if not with_bit:
                        continue
                    partial = len(with_bit) < len(readers)
                    if partial:
                        anomalies.add('partial_reader')
                    ts_values = {ts_by_reader[r] for r in with_bit}
                    if len(ts_values) > 1:
                        anomalies.add('reader_ts_mismatch')
                    ts = ts_by_reader[min(with_bit)]
                    zones = zone_map.get(door, [])
                    alarm = any(record.alarm_bits & (1 << (z - 1)) for z in zones)
                    rights.append({'ctrl': ctrl.id, 'serial': ctrl.serial or '', 'door': door, 'ts': ts,
                                   'alarm': alarm, 'readers': with_bit, 'partial': partial})
            if not rights:
                anomalies.add('no_rights')
            if len(pins) > 1:
                anomalies.add('pin_mismatch')
            anomaly = 'none'
            for candidate in ('bad_bcd', 'pin_mismatch', 'reader_ts_mismatch', 'partial_reader', 'no_rights'):
                if candidate in anomalies:
                    anomaly = candidate
                    break
            card.write({
                'door_rights_json': json.dumps(rights),
                'rights_key': _fingerprint([(r['serial'], r['door'], r['ts'], r['alarm']) for r in rights]),
                'apb_bits_json': json.dumps(apb),
                'pin': pins.pop() if len(pins) == 1 else '',
                'pin_mismatch': len(pins) > 1,
                'anomaly': anomaly,
            })
            if anomaly == 'pin_mismatch':
                self._finding('pin_conflict', 'warning', self.env._(
                    "Card %(number)s carries different PIN codes on different controllers; no PIN is imported.",
                    number=card.number_display), card_id=card)
            elif anomaly in ('partial_reader', 'reader_ts_mismatch'):
                self._finding('anomaly', 'warning', self.env._(
                    "Card %(number)s has a right this system cannot hold exactly (%(what)s); it is "
                    "imported as a right on the whole door with the schedule of the first reader.",
                    number=card.number_display,
                    what=dict(card._fields['anomaly'].selection).get(anomaly)), card_id=card)
            elif anomaly == 'no_rights':
                self._finding('anomaly', 'info', self.env._(
                    "Card %(number)s is stored on the controllers but opens no door.",
                    number=card.number_display), card_id=card)

    # ------------------------------------------------------------ groups

    def _groups(self, remembered):
        run = self.run
        run.group_ids.unlink()
        holders = {}
        for card in run.card_ids:
            for right in json.loads(card.door_rights_json or '[]'):
                key = (right['ctrl'], right['door'], right['ts'], bool(right['alarm']))
                holders.setdefault(key, set()).add(card.id)
        partition = {}
        for right, cards in holders.items():
            partition.setdefault(frozenset(cards), []).append(right)
        ordered = sorted(partition.items(), key=lambda item: (-len(item[0]), -len(item[1]), sorted(item[1])))
        group_env = self.env['hr.rfid.hw.import.group']
        right_env = self.env['hr.rfid.hw.import.group.right']
        cards_by_id = {c.id: c for c in run.card_ids}
        name_size = group_env._fields['name'].size or 32
        for index, (card_ids, rights) in enumerate(ordered, start=1):
            numbers = sorted(cards_by_id[cid].number for cid in card_ids)
            holder_key = _fingerprint(numbers)
            # The access group name is limited in length; a translation that
            # does not fit falls back to the short form rather than being cut.
            name = self.env._('Access group %(n)s - %(doors)s doors', n=index, doors=len(rights))
            if len(name) > name_size:
                name = self.env._('Group %(n)s (%(doors)s)', n=index, doors=len(rights))[:name_size]
            values = {'run_id': run.id, 'sequence': index, 'name': name, 'holder_key': holder_key,
                      'card_ids': [(6, 0, sorted(card_ids))]}
            if holder_key in remembered:
                # The same set of cards as before: the operator's name and
                # choice for it are kept.
                values['name'], values['include'], values['merged_from_json'] = remembered[holder_key]
            group = group_env.create(values)
            right_env.create([{
                'group_id': group.id, 'run_id': run.id, 'ctrl_id': ctrl_id, 'door_number': door,
                'ts_number': ts, 'alarm': alarm,
            } for ctrl_id, door, ts, alarm in sorted(rights)])

    # ------------------------------------------------------------ schedule slots

    def _slots(self, remembered):
        run = self.run
        run.ts_slot_ids.unlink()
        readings = run.ctrl_ids.filtered('include').mapped('ts_ids')
        used = set()
        for card in run.card_ids:
            for right in json.loads(card.door_rights_json or '[]'):
                used.add(right['ts'])
        for ctrl in run.ctrl_ids.filtered('include'):
            for ts in json.loads(ctrl.out_ts_json or '[]'):
                if ts:
                    used.add(ts)
        slot_env = self.env['hr.rfid.hw.import.ts.slot']
        included_ctrl_ids = set(run.ctrl_ids.filtered('include').ids)
        for number in sorted({t.number for t in readings}):
            existing = run._company_ts(number)
            values = {'run_id': run.id, 'number': number, 'used_by_rights': number in used,
                      'existing_ts_id': existing.id if existing else False,
                      'existing_is_empty': existing.is_empty if existing else True}
            if number in remembered:
                source_ctrl_id, keep_existing, note = remembered[number]
                # The chosen controller must still be part of the survey.
                values.update({'source_ctrl_id': source_ctrl_id if source_ctrl_id in included_ctrl_ids else False,
                               'keep_existing': keep_existing, 'decision_note': note})
            slot = slot_env.create(values)
            readings.filtered(lambda t: t.number == number).write({'slot_id': slot.id})
            variants = {t.week_fingerprint for t in slot.ts_ids if not t.is_empty}
            existing_fp = codecs.week_fingerprint(existing.ts_data) if existing and existing.ts_data else ''
            slot.existing_differs = bool(existing) and not existing.is_empty and bool(variants) and existing_fp not in variants
            if len(variants) > 1:
                names = ', '.join('%s (%s)' % (t.ctrl_id.name, t.summary or '-')
                                  for t in slot.ts_ids if not t.is_empty)
                self._finding('ts_conflict', 'warning' if number not in used else 'info', self.env._(
                    "Schedule slot %(n)s differs between controllers: %(names)s. Choose which controller "
                    "to take it from.", n=number, names=names), slot_id=slot)
            elif slot.existing_differs:
                self._finding('ts_conflict', 'info', self.env._(
                    "Schedule slot %(n)s in this company differs from the controllers; the controllers' "
                    "version will be taken.", n=number), slot_id=slot)

    # ------------------------------------------------------------ people

    def _placeholders(self):
        run = self.run
        person_env = self.env['hr.rfid.hw.import.person']
        for card in run.card_ids.filtered(lambda c: not c.person_id):
            person = person_env.create({
                'run_id': run.id, 'name': self.env._('Card %(number)s', number=card.number_display),
                'name_key': 'card:%s' % card.number, 'source': 'placeholder',
                'owner_type': run.placeholder_owner_type,
            })
            card.write({'person_id': person.id})
        run.person_ids.filtered(lambda p: p.source == 'placeholder' and not p.card_ids).unlink()
        self._person_pins()

    def _person_pins(self):
        for person in self.run.person_ids:
            pins = {c.pin for c in person.card_ids if c.pin}
            person.pin = pins.pop() if len(pins) == 1 else ''

    # ------------------------------------------------------------ conflicts and gaps

    def _conflict(self, kind, message, remembered, **links):
        issue = self._finding(kind, 'blocker', message, **links)
        key = (kind, issue.module_id.id, issue.ctrl_id.id, issue.card_id.id)
        if key in remembered:
            issue.resolution = remembered[key]
        return issue

    def _conflicts(self, remembered):
        run = self.run
        serial_size = self.env['hr.rfid.webstack']._fields['serial'].size or 0
        for module in run.module_ids.filtered(lambda m: m.include and m.serial and serial_size
                                              and len(m.serial) > serial_size):
            module.write({'include': False})
            self._finding('warning', 'warning', self.env._(
                "The serial number of module %(serial)s at %(ip)s is longer than this system can hold "
                "(%(size)s characters), so the module and its controllers are left out of the import.",
                serial=module.serial, ip=module._display_address(), size=serial_size), module_id=module)
        for module in run.module_ids.filtered(lambda m: m.include and m.status != 'unreachable' and not m.serial):
            self._finding('warning', 'blocker', self.env._(
                "The module at %(ip)s reports no serial number and cannot be registered; untick it or "
                "check it again.", ip=module._display_address()), module_id=module)
        # Whether a module is already registered is decided now, against the
        # survey's company as it is now - not against what the probe saw.
        for module in run.module_ids.filtered(lambda m: m.include and m.status != 'unreachable' and m.serial):
            existing, ours = run._existing_webstack(module.serial)
            module.write({'status': 'known' if existing else 'new',
                          'existing_webstack_id': existing.id if existing and ours else False})
            if not existing:
                continue
            if ours:
                self._conflict('conflict_webstack', self.env._(
                    "Module %(serial)s at %(ip)s is already registered in this system as '%(name)s'. "
                    "Decide whether to use that record or leave the module out.",
                    serial=module.serial, ip=module._display_address(), name=existing.name), remembered,
                    module_id=module, target_model='hr.rfid.webstack', target_id=existing.id)
            else:
                # Registered by another company of this database: that record is
                # not this company's to see or to use, and a second one with the
                # same serial number cannot exist. The module stays out.
                self._conflict('conflict_webstack', self.env._(
                    "Module %(serial)s at %(ip)s is already registered elsewhere in this database and "
                    "cannot be imported here. Untick it to continue.",
                    serial=module.serial, ip=module._display_address()), remembered, module_id=module)
        # The search is global on purpose: the access control module keys
        # controllers by serial number alone, so a twin in another company
        # blocks this import just the same. What must not cross the company
        # boundary is the name of that record.
        ctrls = run.ctrl_ids.filtered(lambda c: c.include and c.serial)
        by_serial = {}
        for existing in self.env['hr.rfid.ctrl'].sudo().search([('serial_number', 'in', ctrls.mapped('serial'))]):
            by_serial.setdefault(existing.serial_number, existing)
        for ctrl in ctrls:
            existing = by_serial.get(ctrl.serial)
            owner = existing.webstack_id.company_id if existing else None
            if existing and owner and owner != run.company_id:
                ctrl.existing_ctrl_id = False
                self._conflict('conflict_ctrl', self.env._(
                    "Controller %(ctrl)s has the serial number of a controller registered elsewhere in "
                    "this database and cannot be imported here. Untick it to continue.", ctrl=ctrl.name),
                    remembered, ctrl_id=ctrl)
                continue
            ctrl.existing_ctrl_id = existing.id if existing else False
            if existing:
                self._conflict('conflict_ctrl', self.env._(
                    "Controller %(ctrl)s has the same serial number as '%(name)s', which is already "
                    "registered here. Decide whether to use that record or leave this controller out.",
                    ctrl=ctrl.name, name=existing.name), remembered,
                    ctrl_id=ctrl, target_model='hr.rfid.ctrl', target_id=existing.id)
        by_number = {}
        for existing in self.env['hr.rfid.card'].sudo().with_context(active_test=False).search([
                ('internal_number', 'in', run.card_ids.mapped('number')), ('company_id', '=', run.company_id.id)]):
            by_number.setdefault(existing.internal_number, existing)
        for card in run.card_ids:
            existing = by_number.get(card.number)
            card.existing_card_id = existing.id if existing else False
            if existing:
                owner = existing.get_owner()
                self._conflict('conflict_card', self.env._(
                    "Card %(number)s already exists here (owner: %(owner)s). Decide whether to use that "
                    "record or leave the surveyed card out.",
                    number=card.number_display, owner=owner.name if owner else '-'), remembered,
                    card_id=card, target_model='hr.rfid.card', target_id=existing.id)

    def _gaps(self):
        for ctrl in self.run.ctrl_ids:
            gaps = json.loads(ctrl.gaps_json or '[]')
            if gaps:
                self._finding('gap', 'info', self.env._(
                    "%(ctrl)s does not support reading its %(settings)s; those settings are not part of "
                    "the survey.", ctrl=ctrl.name,
                    settings=', '.join(setting_label(self.env, opcode) for opcode in gaps)), ctrl_id=ctrl)
