"""The import: the survey becomes records of the access control module.

Everything is created under a context that switches the hardware side effects
of that module off, and the controllers are created through the path the
module itself uses for a controller it already knows - so no reset, no clock
sync and no card deletion is ever queued. Every created record carries an
external ID, kept through the core's own external-ID machinery, so a second
import of the same site creates nothing twice.
"""
import hashlib
import json
import logging
import time

from odoo import Command, fields

from ..helpers import codecs

_logger = logging.getLogger(__name__)

#: ir.model.data module and name prefix of every record this import creates.
#: Same module as the standard Odoo import and as the sibling transfer, so the
#: existing tooling recognises the records as imported ones.
EXTERNAL_ID_MODULE = '__import__'
EXTERNAL_ID_PREFIX = 'rfid_import_hw_'

#: Context that keeps the access control module from talking to the hardware
#: while records are created (same six keys as the sibling transfer).
IMPORT_CONTEXT = {
    'no_hardware_commands': True,
    'tracking_disable': True,
    'mail_create_nolog': True,
    'mail_create_nosubscribe': True,
    'mail_activity_automation_skip': True,
    'no_reset_password': True,
}

STEPS = ('schedules', 'webstacks', 'controllers', 'people', 'cards', 'groups', 'report')

#: Operating modes the access control module accepts (0 is refused by it).
VALID_MODES = (1, 2, 3, 4)


class HardwareImporter:
    def __init__(self, run):
        self.run = run
        self.env = run.env
        serials = sorted(m.serial for m in run.module_ids.filtered(lambda m: m.include and m.serial))
        self.site_slug = ('_'.join(serials) or 'run%s' % run.id).replace('-', '_').replace('.', '_')
        self.company = run.company_id
        # The operator's decisions, read once: (kind, field, row id) -> resolution.
        self.resolutions = {}
        for issue in run.issue_ids.filtered(lambda i: i.kind.startswith('conflict_')):
            for field in ('module_id', 'ctrl_id', 'card_id'):
                if issue[field]:
                    self.resolutions[(issue.kind, field, issue[field].id)] = issue.resolution
        self._pending_xmlids = []

    # ------------------------------------------------------------ ledger

    def _xml_id(self, prefix, ref):
        return '%s.%s%s_%s_%s' % (EXTERNAL_ID_MODULE, EXTERNAL_ID_PREFIX, self.site_slug, prefix, ref)

    def _find(self, model, prefix, ref):
        """The record this import created for ``ref`` in an earlier survey, if
        it still exists (the core's cached external-ID lookup)."""
        res_model, res_id = self.env['ir.model.data']._xmlid_to_res_model_res_id(self._xml_id(prefix, ref))
        if res_id and res_model == model:
            return self.env[model].sudo().with_context(active_test=False).browse(res_id).exists()
        return self.env[model].browse()

    def _mark(self, record, prefix, ref):
        """Remember ``record`` under its external ID; written in one batch at
        the end of the step through the core's own ``_update_xmlids``, which
        also repairs an ID that points at a record deleted since."""
        self._pending_xmlids.append({'xml_id': self._xml_id(prefix, ref), 'record': record, 'noupdate': True})

    def _flush_xmlids(self):
        if self._pending_xmlids:
            self.env['ir.model.data'].sudo()._update_xmlids(self._pending_xmlids, update=True)
            self._pending_xmlids = []

    def _lang(self):
        return self.run.user_id.lang or self.env.user.lang or 'en_US'

    def _ctx(self, model, **extra):
        # The records are named in the language of the person who started
        # the survey, not in the scheduler's.
        return self.env[model].sudo().with_context(**IMPORT_CONTEXT, lang=self._lang(), **extra)

    def _report(self, message, **links):
        self.run._log_issue('report', 'info', message, phase='import', **links)

    def _warn(self, message, **links):
        self.run._log_issue('warning', 'warning', message, phase='import', **links)

    def _resolution(self, kind, **link):
        """The operator's decision on a conflict, or None when no finding was
        raised for it. No finding means no decision, never "use the existing"."""
        field, record = next(iter(link.items()))
        return self.resolutions.get((kind, field, record.id))

    # ------------------------------------------------------------ driver

    def execute(self, deadline):
        """Work through the steps not yet done. True when every step is finished."""
        done = set(json.loads(self.run.phase_done_json or '[]'))
        for step in STEPS:
            if step in done:
                continue
            self.run.write({'current_phase': dict(self._step_labels())[step]})
            getattr(self, '_step_' + step)()
            self._flush_xmlids()
            done.add(step)
            self.run.write({'phase_done_json': json.dumps(sorted(done)), 'done_count': len(done),
                            'total_count': len(STEPS)})
            self.run._save_progress(remaining=len(STEPS) - len(done))
            if time.monotonic() > deadline and len(done) < len(STEPS):
                return False
        return True

    def _step_labels(self):
        _ = self.env._
        return [
            ('schedules', _('Time schedules')), ('webstacks', _('Modules')),
            ('controllers', _('Controllers, doors and readers')), ('people', _('People')),
            ('cards', _('Cards')), ('groups', _('Access groups')), ('report', _('Report')),
        ]

    # ------------------------------------------------------------ 1. schedules

    def _step_schedules(self):
        run = self.run
        if not run.import_schedules:
            self._report(self.env._("Time schedules were left out on request."))
            return
        for slot in run.ts_slot_ids:
            if slot.keep_existing:
                self._report(self.env._("Schedule slot %(n)s: this company's schedule was kept.", n=slot.number),
                             slot_id=slot)
                continue
            chosen = slot._chosen_reading()
            if not chosen:
                self._report(self.env._(
                    "Schedule slot %(n)s: no controller reading was chosen for it, so this company's "
                    "schedule with that number is left as it is.", n=slot.number), slot_id=slot)
                continue
            if not slot.existing_ts_id:
                self._report(self.env._(
                    "Schedule slot %(n)s: this company has no schedule with that number, so the "
                    "controllers' schedule was not imported%(rights)s.", n=slot.number,
                    rights=self.env._(" and the rights that use it are left out") if slot.used_by_rights else ''),
                    slot_id=slot)
                continue
            existing = slot.existing_ts_id
            if codecs.week_fingerprint(existing.ts_data) != chosen.week_fingerprint:
                others = existing.controller_ids
                existing.with_context(**IMPORT_CONTEXT).sudo().write({'ts_data': chosen.raw_hex})
                self._report(self.env._(
                    "Schedule slot %(n)s was taken from %(ctrl)s: %(summary)s.",
                    n=slot.number, ctrl=chosen.ctrl_id.name, summary=chosen.summary or '-'), slot_id=slot)
                if others:
                    existing.with_context(**IMPORT_CONTEXT).sudo().write({'controller_ids': [Command.clear()]})
                    self._report(self.env._(
                        "Controllers already in this system hold the previous schedule %(n)s (%(names)s); "
                        "the system will write the new schedule to them when it is next needed there.",
                        n=slot.number, names=', '.join(others.mapped('name'))), slot_id=slot)
            self._mark(existing, 'ts', slot.number)
            differing = slot.ts_ids.filtered(
                lambda t: t.ctrl_id.include and not t.is_empty and t.week_fingerprint != chosen.week_fingerprint)
            for reading in differing:
                self._report(self.env._(
                    "%(ctrl)s holds a different schedule in slot %(n)s (%(summary)s); the chosen schedule "
                    "will be written to it the first time a right using that slot is granted here.",
                    ctrl=reading.ctrl_id.name, n=slot.number, summary=reading.summary or '-'),
                    slot_id=slot, ctrl_id=reading.ctrl_id)

    # ------------------------------------------------------------ 2. modules

    def _included_modules(self):
        return self.run.module_ids.filtered(lambda m: m.include and m.status != 'unreachable' and m.serial)

    def _step_webstacks(self):
        run = self.run
        if not run.import_hardware:
            self._report(self.env._("Modules and controllers were left out on request."))
            return
        for module in run.module_ids.filtered(lambda m: m.include and m.status != 'unreachable' and not m.serial):
            self._report(self.env._("The module at %(ip)s reports no serial number and was not registered.",
                                    ip=module._display_address()), module_id=module)
        serial_size = self.env['hr.rfid.webstack']._fields['serial'].size or 0
        tz = self.company.partner_id.tz or self.env.user.tz or 'UTC'
        for module in self._included_modules():
            if module.webstack_id:
                continue
            if module.status == 'known' and not module.existing_webstack_id:
                # Registered by another company; there is nothing this company
                # may link to and a second record with that serial cannot exist.
                self._report(self.env._("Module %(serial)s was left out (registered elsewhere in this database).",
                                        serial=module.serial), module_id=module)
                continue
            existing = module.existing_webstack_id or self._find('hr.rfid.webstack', 'ws', module.serial)
            if module.existing_webstack_id and self._resolution('conflict_webstack', module_id=module) != 'link':
                # No finding, or a finding without a decision, means the
                # existing record is not touched.
                self._report(self.env._("Module %(serial)s was left out (already registered).",
                                        serial=module.serial), module_id=module)
                continue
            if existing:
                self._mark(existing, 'ws', module.serial)
                module.write({'webstack_id': existing.id})
                self._report(self.env._("Module %(serial)s: the existing record '%(name)s' is used.",
                                        serial=module.serial, name=existing.name), module_id=module)
                continue
            if serial_size and len(module.serial) > serial_size:
                self._warn(self.env._(
                    "The serial number of module %(serial)s is longer than this system can hold "
                    "(%(size)s characters); the module cannot be registered by this import.",
                    serial=module.serial, size=serial_size), module_id=module)
                continue
            values = {
                'name': self.env._('Module %(serial)s (%(host)s)', serial=module.serial,
                                   host=module.hostname or module._display_address()),
                'serial': module.serial,
                'hw_version': module.hw_version or False,
                'version': (module.fw_version or '')[:6],
                'behind_nat': False,
                'last_ip': module._display_address(),
                'active': False,
                'available': 'a',
                'company_id': self.company.id,
                'tz': tz,
                'module_username': module.module_username or 'sdk',
            }
            if module.sudo().module_password:
                values['module_password'] = module.sudo().module_password
            webstack = self._ctx('hr.rfid.webstack').create(values)
            self._mark(webstack, 'ws', module.serial)
            module.write({'webstack_id': webstack.id})
            self._report(self.env._("Module %(serial)s was created (switched off until you enable it).",
                                    serial=module.serial), module_id=module)

    # ------------------------------------------------------------ 3. controllers

    def _step_controllers(self):
        run = self.run
        if not run.import_hardware:
            return
        for ctrl in run.ctrl_ids.filtered(lambda c: c.include and c.read_state == 'done' and c.family != 'vending'):
            if ctrl.ctrl_rec_id or not ctrl.module_id.webstack_id or not ctrl.f0_hex:
                continue
            if not ctrl.existing_ctrl_id and self._resolution('conflict_ctrl', ctrl_id=ctrl) is not None:
                # A twin registered by another company: nothing to link to, and
                # the access control module would refuse a second one anyway.
                self._report(self.env._("%(ctrl)s was left out (registered elsewhere in this database).",
                                        ctrl=ctrl.name), ctrl_id=ctrl)
                continue
            if ctrl.existing_ctrl_id:
                if self._resolution('conflict_ctrl', ctrl_id=ctrl) == 'link':
                    self._mark(ctrl.existing_ctrl_id, 'ctrl', ctrl.serial)
                    ctrl.write({'ctrl_rec_id': ctrl.existing_ctrl_id.id})
                    self._report(self.env._("%(ctrl)s: the existing controller record is used.", ctrl=ctrl.name),
                                 ctrl_id=ctrl)
                else:
                    self._report(self.env._("%(ctrl)s was left out (already registered).", ctrl=ctrl.name),
                                 ctrl_id=ctrl)
                continue
            existing = self._find('hr.rfid.ctrl', 'ctrl', ctrl.serial or 'a%s' % ctrl.address)
            if existing:
                ctrl.write({'ctrl_rec_id': existing.id})
                continue
            self._create_controller(ctrl)

    def _controller_values(self, ctrl):
        dec = codecs.decode_f0(ctrl.f0_hex)
        values = {
            'name': ctrl.name,
            'ctrl_id': ctrl.address,
            'webstack_id': ctrl.module_id.webstack_id.id,
            'serial_number': dec['serial'],
            'hw_version': dec['hw_code'],
            'sw_version': dec['sw_version'],
            'mode': dec['mode'],
            'external_db': dec['external_db'],
            'dual_person_mode': dec['dual_person'],
            'interlocking_mode': dec['interlocking'],
            'relay_time_factor': '1' if dec['relay_time_factor'] else '0',
            'readers': dec['readers'],
            'inputs': dec['inputs'],
            'outputs': dec['outputs'],
            'time_schedules': dec['time_schedules'],
            'io_table_lines': dec['io_table_lines'],
            'alarm_lines': dec['alarm_lines'],
            'max_cards_count': dec['max_cards'],
            'max_events_count': dec['max_events'],
            'last_f0_read': fields.Datetime.now(),
        }
        if ctrl.io_table_hex:
            values['io_table'] = ctrl.io_table_hex.lower()
        if ctrl.alarm_setup_json:
            setup = json.loads(ctrl.alarm_setup_json)
            values['alarm_lines_setup'] = setup.get('alarm_lines_setup') or ''
            values['alarm_sensor_events'] = bool(setup.get('sensor_events'))
        if ctrl.input_mask:
            values['inputs_mask'] = ctrl.input_mask
        if ctrl.status_json:
            status = json.loads(ctrl.status_json)
            values.update({
                'input_states': status.get('input_states', 0),
                'output_states': status.get('output_states', 0),
                'system_voltage': status.get('system_voltage', 0.0),
                'input_voltage': status.get('input_voltage', 0.0),
            })
        return values, dec

    def _create_controller(self, ctrl):
        values, dec = self._controller_values(ctrl)
        # What the wire says goes into fields the access control module
        # validates; a value it would refuse is a finding here, never an
        # exception that closes the whole import.
        if str(dec['hw_code']) not in codecs.HW_LABELS:
            self._warn(self.env._(
                "%(ctrl)s reports hardware type %(hw)s, which this system does not know; it was not "
                "imported.", ctrl=ctrl.name, hw=dec['hw_code']), ctrl_id=ctrl)
            return
        if dec['mode'] not in VALID_MODES:
            self._warn(self.env._(
                "%(ctrl)s reports operating mode %(mode)s, which this system does not accept; it was "
                "not imported.", ctrl=ctrl.name, mode=dec['mode']), ctrl_id=ctrl)
            return
        Ctrl = self._ctx('hr.rfid.ctrl', from_controller=True)
        record = Ctrl.create(values)
        ctrl.write({'ctrl_rec_id': record.id})
        if ctrl.family != 'unknown' and codecs.f0_would_pass(dec):
            # The module's own F0 handling builds the doors and readers. Because
            # the controller already exists with this serial on this module, it
            # takes the "known controller" branch: nothing is reset, nothing is
            # queued to the hardware.
            command = self._ctx('hr.rfid.command').create({
                'webstack_id': record.webstack_id.id, 'controller_id': record.id,
                'cmd': 'F0', 'status': 'Success', 'ex_timestamp': fields.Datetime.now(),
            })
            command.with_context(**IMPORT_CONTEXT, from_controller=True, lang=self._lang()).parse_f0_response({
                'response': {'id': ctrl.address, 'c': 'F0', 'e': 0, 'd': ctrl.f0_hex}})
            if not record.exists():
                # The access control module removes a controller whose serial
                # number it already knows on another module. Said, not hidden.
                ctrl.write({'ctrl_rec_id': False})
                self._warn(self.env._(
                    "%(ctrl)s could not be created: a controller with its serial number is registered on "
                    "another module of this system.", ctrl=ctrl.name), ctrl_id=ctrl)
                return
            self._mirror_settings(ctrl, record)
            self._report(self.env._("%(ctrl)s was created with %(doors)s doors and %(readers)s readers.",
                                    ctrl=ctrl.name, doors=len(record.door_ids), readers=len(record.reader_ids)),
                         ctrl_id=ctrl)
        else:
            ctrl.write({'imported_without_doors': True})
            self._report(self.env._(
                "%(ctrl)s was created with its settings only; its doors and readers could not be derived "
                "from the mode it reports.", ctrl=ctrl.name), ctrl_id=ctrl)
        self._mark(record, 'ctrl', ctrl.serial or 'a%s' % ctrl.address)
        self._link_schedules(ctrl, record)

    def _mirror_settings(self, ctrl, record):
        """Copy the settings read from the controller onto its record, through the
        same hooks the module uses for replies from the device (no command)."""
        # Alarm zones: the lines are created from the doors, then set from what
        # was read; from_controller keeps the alarm-line write from re-sending.
        if record.alarm_lines and record.door_ids:
            record._setup_alarm_lines()
            if ctrl.alarm_setup_json:
                setup = json.loads(ctrl.alarm_setup_json)
                for line in record.alarm_line_ids:
                    bit = 1 << (line.line_number - 1)
                    line.with_context(from_controller=True).write({
                        'enableAC': not bool(setup.get('disable_readers', 0) & bit),
                        'enableDC': not bool(setup.get('disable_door_contacts', 0) & bit),
                        'enabled': bool(setup.get('zones_enabled', 0) & bit),
                    })
        # Reader modes.
        if ctrl.reader_modes_json:
            modes = {m['reader']: m['mode'] for m in json.loads(ctrl.reader_modes_json)}
            for reader in record.reader_ids:
                mode = modes.get(reader.number)
                if mode and mode != '00':
                    reader.write({'mode': mode, 'no_d6_cmd': True})
        # Input masks.
        if ctrl.fb_hex:
            try:
                mask, relay_bytes = codecs.decode_input_masks(ctrl.fb_hex)
                record.process_input_masks(mask, output_relay_mask=relay_bytes)
            except codecs.DecodeError as exc:
                _logger.warning("Hardware survey %s: input masks of %s not decodable: %s", self.run.id, ctrl.name, exc)
                self._report(self.env._("%(ctrl)s: the input masks could not be interpreted and were not "
                                        "imported.", ctrl=ctrl.name), ctrl_id=ctrl)
        # Output time schedules.
        if ctrl.out_ts_json:
            commands = []
            for index, ts_number in enumerate(json.loads(ctrl.out_ts_json), start=1):
                if not ts_number:
                    continue
                ts = self.run._company_ts(ts_number)
                if ts:
                    commands.append(Command.create({'output_number': index, 'time_schedule_id': ts.id,
                                                    'controller_id': record.id}))
                else:
                    self._report(self.env._(
                        "%(ctrl)s: output %(output)s follows schedule %(n)s, which this company does not "
                        "have; that output schedule was not imported.",
                        ctrl=ctrl.name, output=index, n=ts_number), ctrl_id=ctrl)
            if commands:
                record.with_context(from_controller=True).write({'output_ts_ids': commands})
        # Anti-passback per door.
        if ctrl.apb_bitmap:
            for door in record.door_ids:
                if codecs.door_apb(ctrl.apb_bitmap, door.number):
                    door.with_context(**IMPORT_CONTEXT).write({'apb_mode': True})

    def _link_schedules(self, ctrl, record):
        """Record which company schedules this controller already holds, so the
        module does not write them again when a right using them is granted."""
        for reading in ctrl.ts_ids.filtered(lambda t: not t.is_empty):
            ts = self.run._company_ts(reading.number)
            if not ts or not ts.ts_data or len(ts.ts_data) < 258:
                continue
            if codecs.week_fingerprint(ts.ts_data) == reading.week_fingerprint and record not in ts.controller_ids:
                ts.with_context(**IMPORT_CONTEXT).sudo().write({'controller_ids': [Command.link(record.id)]})

    # ------------------------------------------------------------ 4. people

    def _person_ref(self, person):
        """The identity of a person across surveys of the same site.

        A named person is identified by the name from the file. Two people
        who share a name (the operator split them) are told apart by their
        first card, otherwise the second would land on the first one's
        record and receive the union of both cards' rights.
        """
        if person.source == 'file':
            namesakes = self.run.person_ids.filtered(
                lambda p: p.source == 'file' and p.name_key == person.name_key and p != person)
            key = person.name_key
            if namesakes:
                key = '%s:%s' % (person.name_key, min(person.card_ids.mapped('number')) or person.id)
            return 'p_' + hashlib.sha1(key.encode()).hexdigest()[:16]
        return 'pc_' + (min(person.card_ids.mapped('number')) if person.card_ids else str(person.id))

    def _adopt_existing_owner(self, person):
        """A generated holder for a card that already exists here is that card's
        owner - never a second person next to them."""
        for card in person.card_ids:
            existing = card.existing_card_id if self._resolution('conflict_card', card_id=card) == 'link' else None
            existing = existing or self._find('hr.rfid.card', 'card', card.number)
            if not existing:
                continue
            if existing.employee_id:
                person.write({'employee_id': existing.employee_id.id, 'owner_type': 'employee'})
                return True
            if existing.contact_id:
                person.write({'partner_id': existing.contact_id.id, 'owner_type': 'contact'})
                return True
        return False

    def _step_people(self):
        run = self.run
        if not run.import_people:
            self._report(self.env._("People were left out on request."))
            return
        to_create = {'employee': [], 'contact': []}
        for person in run.person_ids.filtered(lambda p: p.include and p.card_ids):
            if person.employee_id or person.partner_id:
                continue
            if person.source == 'placeholder' and self._adopt_existing_owner(person):
                continue
            ref = self._person_ref(person)
            values = {'name': person.name, 'company_id': self.company.id}
            if person.pin and person.pin != '0000':
                values['hr_rfid_pin_code'] = person.pin
            if person.owner_type == 'employee':
                existing = self._find('hr.employee', 'emp', ref)
                if existing:
                    person.write({'employee_id': existing.id})
                    continue
                values['department_id'] = run.default_department_id.id
            else:
                existing = self._find('res.partner', 'partner', ref)
                if existing:
                    person.write({'partner_id': existing.id})
                    continue
                values.update(type='contact', company_type='person', is_company=False)
            to_create[person.owner_type].append((person, ref, values))
        # One create per kind, as the core's own import does.
        if to_create['employee']:
            records = self._ctx('hr.employee').create([values for _, _, values in to_create['employee']])
            for (person, ref, _), record in zip(to_create['employee'], records):
                person.write({'employee_id': record.id})
                self._mark(record, 'emp', ref)
        if to_create['contact']:
            records = self._ctx('res.partner').create([values for _, _, values in to_create['contact']])
            for (person, ref, _), record in zip(to_create['contact'], records):
                person.write({'partner_id': record.id})
                self._mark(record, 'partner', ref)
        employees = run.person_ids.filtered('employee_id')
        contacts = run.person_ids.filtered('partner_id')
        self._report(self.env._("%(employees)s employees and %(contacts)s contacts are in place.",
                                employees=len(employees), contacts=len(contacts)))

    # ------------------------------------------------------------ 5. cards

    def _step_cards(self):
        run = self.run
        if not run.import_cards:
            self._report(self.env._("Cards were left out on request."))
            return
        to_create = []
        for card in run.card_ids.filtered(lambda c: c.include and c.person_id):
            if card.card_rec_id:
                continue
            if card.existing_card_id:
                if self._resolution('conflict_card', card_id=card) == 'link':
                    self._mark(card.existing_card_id, 'card', card.number)
                    card.write({'card_rec_id': card.existing_card_id.id})
                else:
                    self._report(self.env._("Card %(number)s was left out (already registered).",
                                            number=card.number_display), card_id=card)
                continue
            existing = self._find('hr.rfid.card', 'card', card.number)
            if existing:
                card.write({'card_rec_id': existing.id})
                continue
            person = card.person_id
            if not (person.employee_id or person.partner_id):
                self._report(self.env._("Card %(number)s was left out: its owner was not imported.",
                                        number=card.number_display), card_id=card)
                continue
            values = {'number': card.number_display, 'card_input_type': self.company.card_input_type or 'w34',
                      'company_id': self.company.id}
            if person.employee_id:
                values['employee_id'] = person.employee_id.id
            else:
                values['contact_id'] = person.partner_id.id
            to_create.append((card, values))
        if to_create:
            records = self._ctx('hr.rfid.card').create([values for _, values in to_create])
            for (card, _), record in zip(to_create, records):
                card.write({'card_rec_id': record.id})
                self._mark(record, 'card', card.number)
        self._report(self.env._("%(n)s cards were created.", n=len(to_create)))

    # ------------------------------------------------------------ 6. access groups

    def _step_groups(self):
        run = self.run
        if not run.import_groups:
            self._report(self.env._("Access groups were left out on request."))
            return
        Group = self._ctx('hr.rfid.access.group')
        DoorRel = self._ctx('hr.rfid.access.group.door.rel')
        EmpRel = self._ctx('hr.rfid.access.group.employee.rel')
        ContactRel = self._ctx('hr.rfid.access.group.contact.rel')
        groups = run.group_ids.filtered('include')
        for group in groups.filtered(lambda g: not g.access_group_id):
            existing = self._find('hr.rfid.access.group', 'ag', group.holder_key)
            if not existing:
                existing = Group.create({'name': group.name, 'company_id': self.company.id})
                self._mark(existing, 'ag', group.holder_key)
            group.write({'access_group_id': existing.id})
        access_groups = groups.mapped('access_group_id')
        # What the groups already hold, read once.
        held = {(rel.access_group_id.id, rel.door_id.id)
                for rel in DoorRel.search([('access_group_id', 'in', access_groups.ids)])}
        door_rels = []
        for group in groups.filtered('access_group_id'):
            for right in group.right_ids:
                record = right.ctrl_id.ctrl_rec_id
                if not record:
                    self._report(self.env._(
                        "Access group %(group)s: %(door)s was not imported, so the right on it is left out.",
                        group=group.name, door=right.door_label), group_id=group)
                    continue
                door = record.door_ids.filtered(lambda d: d.number == right.door_number)[:1]
                if not door:
                    self._report(self.env._(
                        "Access group %(group)s: %(door)s has no door record, so the right on it is left out.",
                        group=group.name, door=right.door_label), group_id=group)
                    continue
                ts = self.run._company_ts(right.ts_number)
                if not ts:
                    # A right limited to a schedule the company does not have
                    # must not become a right without a schedule (that would
                    # open the door around the clock). It is left out, and said.
                    self._report(self.env._(
                        "Access group %(group)s: the right on %(door)s follows schedule %(n)s, which this "
                        "company does not have, so the right is left out.",
                        group=group.name, door=right.door_label, n=right.ts_number), group_id=group)
                    continue
                right.write({'door_rec_id': door.id})
                key = (group.access_group_id.id, door.id)
                if key in held:
                    continue
                held.add(key)
                door_rels.append({'access_group_id': group.access_group_id.id, 'door_id': door.id,
                                  'time_schedule_id': ts.id, 'alarm_rights': right.alarm})
        if door_rels:
            DoorRel.create(door_rels)
        # Employees may only hold groups their department allows: every
        # department that will receive a membership is opened for these
        # groups, not only the survey's default one (an adopted employee, or
        # one from an earlier survey, sits in their own department).
        members = groups.mapped('card_ids').mapped('person_id').filtered('include')
        employees = members.mapped('employee_id')
        without_department = employees.filtered(lambda e: not e.department_id)
        if without_department and run.default_department_id:
            without_department.with_context(**IMPORT_CONTEXT).sudo().write(
                {'department_id': run.default_department_id.id})
            self._report(self.env._(
                "%(n)s employees had no department and were put in %(department)s so that they can "
                "hold access groups.", n=len(without_department), department=run.default_department_id.name))
        departments = employees.mapped('department_id') | run.default_department_id
        if departments and access_groups:
            departments.with_context(**IMPORT_CONTEXT).sudo().write({
                'hr_rfid_allowed_access_groups': [Command.link(ag.id) for ag in access_groups]})
        emp_held = {(rel.access_group_id.id, rel.employee_id.id)
                    for rel in EmpRel.search([('access_group_id', 'in', access_groups.ids)])}
        contact_held = {(rel.access_group_id.id, rel.contact_id.id)
                        for rel in ContactRel.search([('access_group_id', 'in', access_groups.ids)])}
        emp_rels, contact_rels = [], []
        for group in groups.filtered('access_group_id'):
            for person in group.card_ids.mapped('person_id').filtered('include'):
                if person.employee_id:
                    if not person.employee_id.department_id:
                        self._report(self.env._(
                            "%(name)s has no department, so the membership in %(group)s is left out.",
                            name=person.name, group=group.name), person_id=person, group_id=group)
                        continue
                    key = (group.access_group_id.id, person.employee_id.id)
                    if key not in emp_held:
                        emp_held.add(key)
                        emp_rels.append({'access_group_id': key[0], 'employee_id': key[1]})
                elif person.partner_id:
                    key = (group.access_group_id.id, person.partner_id.id)
                    if key not in contact_held:
                        contact_held.add(key)
                        contact_rels.append({'access_group_id': key[0], 'contact_id': key[1]})
        if emp_rels:
            EmpRel.create(emp_rels)
        if contact_rels:
            ContactRel.create(contact_rels)
        self._report(self.env._("%(groups)s access groups and %(memberships)s memberships are in place.",
                                groups=len(groups.filtered('access_group_id')),
                                memberships=len(emp_rels) + len(contact_rels)))

    # ------------------------------------------------------------ 7. report

    def _step_report(self):
        run = self.run
        rels = self.env['hr.rfid.card.door.rel'].sudo().search_count(
            [('card_id', 'in', run.card_ids.mapped('card_rec_id').ids)])
        self._report(self.env._(
            "Result: %(modules)s modules, %(ctrls)s controllers, %(cards)s cards, %(rights)s door rights. "
            "No command was sent to the hardware.",
            modules=len(run.module_ids.filtered('webstack_id')), ctrls=len(run.ctrl_ids.filtered('ctrl_rec_id')),
            cards=len(run.card_ids.filtered('card_rec_id')), rights=rels))
