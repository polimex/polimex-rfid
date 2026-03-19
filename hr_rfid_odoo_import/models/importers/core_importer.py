# -*- coding: utf-8 -*-
import logging
import time

from odoo import _
from odoo.exceptions import UserError
from .base_importer import BaseImporter, IMPORT_CONTEXT

_logger = logging.getLogger(__name__)


class CoreImporter:
    """Phase 1 + Phase 3: Foundation + Hardware.

    Phase 1: card_type, employee.category, department (two passes),
             workcode, time.schedule
    Phase 3: alarm.group (two passes), emergency.group, webstack, ctrl,
             door, reader, input.mask, output.ts, alarm, th, zone, notification
    """

    def __init__(self, base: BaseImporter):
        self.b = base
        self.env = base.env
        self.results = []

    def run(self, wizard):
        """Execute Phase 1 + Phase 3."""
        # Phase 1: Foundation
        self._import_card_types()
        self._import_employee_categories()
        self._import_departments()
        self._import_workcodes()
        self._import_time_schedules()

        # Phase 3: Hardware
        if self.b.options.get('import_hardware'):
            self._import_alarm_groups()
            self._import_emergency_groups()
            self._import_webstacks()
            self._import_controllers()
            self._import_doors()
            self._import_readers()
            self._import_input_masks()
            self._import_output_ts()
            self._import_alarms()
            self._import_th_sensors()
            self._import_zones()
            self._import_notifications()

        return self.results

    def _make_result(self, model, source_count, imported_count, linked_count=0,
                     skipped_count=0, duration=0, status='done', error=''):
        return {
            'model': model,
            'source_count': source_count,
            'imported_count': imported_count,
            'linked_count': linked_count,
            'skipped_count': skipped_count,
            'duration': duration,
            'status': status,
            'error': error,
        }

    # ══════════════════════════════════════════════════════════
    # Phase 1: Foundation
    # ══════════════════════════════════════════════════════════

    def _import_card_types(self):
        """Step 1: hr.rfid.card.type — match by name."""
        start = time.time()
        model = 'hr.rfid.card.type'
        source_records = self.b._search_read(model, [], ['name'])
        imported = 0
        linked = 0

        for rec in source_records:
            # Match by name
            existing = self.env[model].search([
                ('name', '=', rec['name'])
            ], limit=1)
            if existing:
                self.b._set_target_id(model, rec['id'], existing.id)
                linked += 1
            else:
                prefix = model.replace('.', '_')
                data_list = [{
                    'xml_id': self.b._xml_id(prefix, rec['id']),
                    'values': {
                        'name': rec['name'],
                    },
                    'noupdate': True,
                }]
                created = self.b._load_records(model, data_list)
                if created:
                    self.b._set_target_id(model, rec['id'], created.id)
                    imported += 1

        self.results.append(self._make_result(
            model, len(source_records), imported, linked,
            duration=time.time() - start,
        ))

    def _import_employee_categories(self):
        """Step 2: hr.employee.category — match by name."""
        start = time.time()
        model = 'hr.employee.category'
        source_records = self.b._search_read(model, [], ['name', 'color'])
        imported = 0
        linked = 0

        for rec in source_records:
            existing = self.env[model].search([
                ('name', '=', rec['name'])
            ], limit=1)
            if existing:
                self.b._set_target_id(model, rec['id'], existing.id)
                linked += 1
            else:
                vals = {'name': rec['name']}
                if rec.get('color'):
                    vals['color'] = rec['color']
                prefix = model.replace('.', '_')
                data_list = [{
                    'xml_id': self.b._xml_id(prefix, rec['id']),
                    'values': vals,
                    'noupdate': True,
                }]
                created = self.b._load_records(model, data_list)
                if created:
                    self.b._set_target_id(model, rec['id'], created.id)
                    imported += 1

        self.results.append(self._make_result(
            model, len(source_records), imported, linked,
            duration=time.time() - start,
        ))

    def _import_departments(self):
        """Step 3: hr.department — TWO PASSES (parent_id self-ref).

        Pass 1: Create all departments without parent_id.
        Pass 2: Update parent_id with mapped IDs.
        """
        start = time.time()
        model = 'hr.department'
        co_domain = self.b._company_domain()
        source_records = self.b._search_read(
            model, co_domain,
            ['name', 'parent_id', 'company_id', 'color', 'note'],
        )
        imported = 0
        linked = 0

        # Pass 1: Create without parent_id
        for rec in source_records:
            target_company_id = self.b._map_company(rec['company_id'])
            if not target_company_id:
                continue

            # Match by name + company
            existing = self.env[model].search([
                ('name', '=', rec['name']),
                ('company_id', '=', target_company_id),
            ], limit=1)
            if existing:
                self.b._set_target_id(model, rec['id'], existing.id)
                linked += 1
            else:
                vals = {
                    'name': rec['name'],
                    'company_id': target_company_id,
                }
                if rec.get('color'):
                    vals['color'] = rec['color']
                if rec.get('note'):
                    vals['note'] = rec['note']
                prefix = model.replace('.', '_')
                data_list = [{
                    'xml_id': self.b._xml_id(prefix, rec['id']),
                    'values': vals,
                    'noupdate': True,
                }]
                created = self.b._load_records(model, data_list)
                if created:
                    self.b._set_target_id(model, rec['id'], created.id)
                    imported += 1

        # Pass 2: Update parent_id
        for rec in source_records:
            if not rec.get('parent_id'):
                continue
            target_id = self.b._get_target_id(model, rec['id'])
            if not target_id:
                continue
            parent_target_id = self.b._map_m2o(model, rec['parent_id'])
            if parent_target_id:
                self.env[model].browse(target_id).with_context(
                    **IMPORT_CONTEXT
                ).write({'parent_id': parent_target_id})

        self.results.append(self._make_result(
            model, len(source_records), imported, linked,
            duration=time.time() - start,
        ))

    def _import_workcodes(self):
        """Step 4: hr.rfid.workcode — filtered by company."""
        start = time.time()
        model = 'hr.rfid.workcode'
        if not self.b._has_model(model):
            return
        co_domain = self.b._company_domain()
        source_records = self.b._search_read(
            model, co_domain,
            ['name', 'number', 'company_id'],
        )
        imported = 0
        linked = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            target_company_id = self.b._map_company(rec['company_id'])
            if not target_company_id:
                continue

            existing = self.env[model].search([
                ('number', '=', rec['number']),
                ('company_id', '=', target_company_id),
            ], limit=1)
            if existing:
                self.b._set_target_id(model, rec['id'], existing.id)
                linked += 1
            else:
                data_list = [{
                    'xml_id': self.b._xml_id(prefix, rec['id']),
                    'values': {
                        'name': rec['name'],
                        'number': rec['number'],
                        'company_id': target_company_id,
                    },
                    'noupdate': True,
                }]
                created = self.b._load_records(model, data_list)
                if created:
                    self.b._set_target_id(model, rec['id'], created.id)
                    imported += 1

        self.results.append(self._make_result(
            model, len(source_records), imported, linked,
            duration=time.time() - start,
        ))

    def _import_time_schedules(self):
        """Step 5: hr.rfid.time.schedule — match by number + company."""
        start = time.time()
        model = 'hr.rfid.time.schedule'
        co_domain = self.b._company_domain()
        fields_to_read = ['name', 'number', 'company_id', 'ts_data']
        if self.b._has_field(model, 'is_empty'):
            fields_to_read.append('is_empty')
        source_records = self.b._search_read(model, co_domain, fields_to_read)
        imported = 0
        linked = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            target_company_id = self.b._map_company(rec['company_id'])
            if not target_company_id:
                continue

            existing = self.env[model].search([
                ('number', '=', rec['number']),
                ('company_id', '=', target_company_id),
            ], limit=1)
            if existing:
                # Update ts_data and name from source for linked records
                update_vals = {}
                if rec.get('ts_data') and rec['ts_data'] != existing.ts_data:
                    update_vals['ts_data'] = rec['ts_data']
                if rec.get('name') and rec['name'] != existing.name:
                    update_vals['name'] = rec['name']
                if update_vals:
                    existing.with_context(**IMPORT_CONTEXT).write(update_vals)
                self.b._set_target_id(model, rec['id'], existing.id)
                linked += 1
            else:
                vals = {
                    'name': rec['name'],
                    'number': rec['number'],
                    'company_id': target_company_id,
                }
                if rec.get('ts_data'):
                    vals['ts_data'] = rec['ts_data']
                data_list = [{
                    'xml_id': self.b._xml_id(prefix, rec['id']),
                    'values': vals,
                    'noupdate': True,
                }]
                created = self.b._load_records(model, data_list)
                if created:
                    self.b._set_target_id(model, rec['id'], created.id)
                    imported += 1

        self.results.append(self._make_result(
            model, len(source_records), imported, linked,
            duration=time.time() - start,
        ))

    # ══════════════════════════════════════════════════════════
    # Phase 3: Hardware
    # ══════════════════════════════════════════════════════════

    def _import_alarm_groups(self):
        """Step 8: hr.rfid.ctrl.alarm.group — TWO PASSES (parent_id self-ref)."""
        start = time.time()
        model = 'hr.rfid.ctrl.alarm.group'
        if not self.b._has_model(model):
            return
        co_domain = self.b._company_domain()
        source_records = self.b._search_read(
            model, co_domain,
            ['name', 'parent_id', 'company_id'],
        )
        imported = 0
        linked = 0
        prefix = model.replace('.', '_')

        # Pass 1: Create without parent_id
        for rec in source_records:
            target_company_id = self.b._map_company(rec['company_id'])
            if not target_company_id:
                continue
            vals = {
                'name': rec['name'],
                'company_id': target_company_id,
            }
            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        # Pass 2: Update parent_id
        for rec in source_records:
            if not rec.get('parent_id'):
                continue
            target_id = self.b._get_target_id(model, rec['id'])
            parent_target_id = self.b._map_m2o(model, rec['parent_id'])
            if target_id and parent_target_id:
                self.env[model].browse(target_id).with_context(
                    **IMPORT_CONTEXT
                ).write({'parent_id': parent_target_id})

        self.results.append(self._make_result(
            model, len(source_records), imported, linked,
            duration=time.time() - start,
        ))

    def _import_emergency_groups(self):
        """Step 9: hr.rfid.ctrl.emergency.group — company-level."""
        start = time.time()
        model = 'hr.rfid.ctrl.emergency.group'
        if not self.b._has_model(model):
            return
        co_domain = self.b._company_domain()
        source_records = self.b._search_read(
            model, co_domain,
            ['name', 'company_id'],
        )
        imported = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            target_company_id = self.b._map_company(rec['company_id'])
            if not target_company_id:
                continue
            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': {
                    'name': rec['name'],
                    'company_id': target_company_id,
                },
                'noupdate': True,
            }]
            created = self.b._load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        self.results.append(self._make_result(
            model, len(source_records), imported,
            duration=time.time() - start,
        ))

    def _import_webstacks(self):
        """Step 10: hr.rfid.webstack — filtered by company."""
        start = time.time()
        model = 'hr.rfid.webstack'
        co_domain = self.b._company_domain()

        # Get common fields between source and target
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        # Key fields to import
        fields_to_read = ['name', 'serial', 'key', 'company_id', 'active',
                          'behind_nat', 'available']
        # Add optional fields that may exist
        for f in ['last_ip', 'updated_at', 'version', 'is_sdk',
                  'tz', 'tz_offset', 'time_format']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)

        source_records = self.b._search_read(model, co_domain, fields_to_read)
        imported = 0
        linked = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            # Check if already mapped (from conflict resolution)
            existing_target = self.b._get_target_id(model, rec['id'])
            if existing_target:
                linked += 1
                continue
            if existing_target is None:
                # Explicitly skipped
                continue

            target_company_id = self.b._map_company(rec['company_id'])
            if not target_company_id:
                continue

            vals = {
                'name': rec['name'],
                'serial': rec['serial'],
                'key': rec['key'],
                'company_id': target_company_id,
                'active': rec.get('active', True),
                'behind_nat': rec.get('behind_nat', False),
                'available': rec.get('available', 'u'),
            }
            # Add optional fields
            for f in fields_to_read:
                if f not in vals and f in rec and f != 'company_id' and rec[f]:
                    vals[f] = rec[f]

            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        self.results.append(self._make_result(
            model, len(source_records), imported, linked,
            duration=time.time() - start,
        ))

    def _import_controllers(self):
        """Step 11: hr.rfid.ctrl — filtered by webstack."""
        start = time.time()
        model = 'hr.rfid.ctrl'
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        # Required fields (must exist in all RFID versions)
        fields_to_read = ['name', 'ctrl_id', 'webstack_id']
        # Optional fields - only read if they exist in BOTH source and target
        for f in ['serial_number', 'hw_version', 'sw_version', 'mode',
                  'external_db', 'max_cards_count', 'max_events_count',
                  'readers_count', 'time_schedules_count', 'io_table_lines',
                  'alarm_lines', 'is_relay_ctrl', 'temperature', 'humidity',
                  'system_voltage', 'input_voltage', 'emergency_group_id',
                  'inputs_mask', 'cash_contained', 'alarm_lines_setup', 'active']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)

        source_records = self.b._search_read(model, [], fields_to_read)
        imported = 0
        linked = 0
        skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            # Check if already mapped (conflict resolution)
            existing_target = self.b._get_target_id(model, rec['id'])
            if existing_target:
                linked += 1
                continue
            if existing_target is None:
                skipped += 1
                continue

            # Map webstack
            ws_target_id = self.b._map_m2o('hr.rfid.webstack', rec.get('webstack_id'))
            if not ws_target_id:
                skipped += 1
                continue

            vals = {
                'name': rec['name'],
                'ctrl_id': rec.get('ctrl_id', 0),
                'webstack_id': ws_target_id,
            }

            # M2O: emergency_group_id
            if rec.get('emergency_group_id') and 'emergency_group_id' in target_fields:
                eg_target = self.b._map_m2o(
                    'hr.rfid.ctrl.emergency.group', rec['emergency_group_id']
                )
                if eg_target:
                    vals['emergency_group_id'] = eg_target

            # Copy all other optional fields that were read
            skip_fields = {'name', 'ctrl_id', 'webstack_id', 'id',
                           'emergency_group_id'}
            for f in fields_to_read:
                if f in skip_fields or f in vals:
                    continue
                if f in rec and rec[f] is not False:
                    vals[f] = rec[f]

            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        self.results.append(self._make_result(
            model, len(source_records), imported, linked, skipped,
            duration=time.time() - start,
        ))

    def _import_doors(self):
        """Step 12: hr.rfid.door — filtered by ctrl→ws→company chain."""
        start = time.time()
        model = 'hr.rfid.door'
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        # Required fields
        fields_to_read = ['name', 'number', 'controller_id']
        # Optional fields
        for f in ['card_type', 'apb_mode', 'apb_time', 'active',
                  'lock_time_min', 'lock_time_max', 'close_time']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)

        source_records = self.b._search_read(model, [], fields_to_read)
        imported = 0
        skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            ctrl_target_id = self.b._map_m2o('hr.rfid.ctrl', rec.get('controller_id'))
            if not ctrl_target_id:
                skipped += 1
                continue

            card_type_target = False
            if rec.get('card_type'):
                card_type_target = self.b._map_m2o('hr.rfid.card.type', rec['card_type'])

            vals = {
                'name': rec['name'],
                'number': rec.get('number', 0),
                'controller_id': ctrl_target_id,
            }
            if card_type_target:
                vals['card_type'] = card_type_target
            for f in ['apb_mode', 'apb_time', 'active', 'lock_time_min',
                       'lock_time_max', 'close_time']:
                if f in rec and f in target_fields and rec[f] is not False:
                    vals[f] = rec[f]

            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        self.results.append(self._make_result(
            model, len(source_records), imported, 0, skipped,
            duration=time.time() - start,
        ))

    def _import_readers(self):
        """Step 13: hr.rfid.reader — filtered by ctrl."""
        start = time.time()
        model = 'hr.rfid.reader'
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        # Required fields
        fields_to_read = ['name', 'number', 'controller_id']
        # Optional fields
        for f in ['reader_type', 'door_ids', 'mode', 'active']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)

        source_records = self.b._search_read(model, [], fields_to_read)
        imported = 0
        skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            ctrl_target_id = self.b._map_m2o('hr.rfid.ctrl', rec.get('controller_id'))
            if not ctrl_target_id:
                skipped += 1
                continue

            vals = {
                'name': rec['name'],
                'number': rec.get('number', 0),
                'controller_id': ctrl_target_id,
            }
            if 'reader_type' in rec and 'reader_type' in target_fields:
                vals['reader_type'] = rec['reader_type']
            # Map door_ids M2M
            if rec.get('door_ids') and 'door_ids' in target_fields:
                vals['door_ids'] = self.b._map_m2m('hr.rfid.door', rec['door_ids'])
            for f in ['mode', 'active']:
                if f in rec and f in target_fields and rec[f] is not False:
                    vals[f] = rec[f]

            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        self.results.append(self._make_result(
            model, len(source_records), imported, 0, skipped,
            duration=time.time() - start,
        ))

    def _import_input_masks(self):
        """Step 14: hr.rfid.ctrl.input.mask — per controller."""
        start = time.time()
        model = 'hr.rfid.ctrl.input.mask'
        if not self.b._has_model(model):
            return
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())
        fields_to_read = ['controller_id']
        for f in ['name', 'mask']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)
        source_records = self.b._search_read(model, [], fields_to_read)
        imported = 0
        skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            ctrl_target_id = self.b._map_m2o('hr.rfid.ctrl', rec.get('controller_id'))
            if not ctrl_target_id:
                skipped += 1
                continue
            vals = {'controller_id': ctrl_target_id}
            for f in ['name', 'mask']:
                if f in rec and f in target_fields:
                    vals[f] = rec.get(f, '')
            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._try_load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1
            else:
                skipped += 1

        self.results.append(self._make_result(
            model, len(source_records), imported, 0, skipped,
            duration=time.time() - start,
        ))

    def _import_output_ts(self):
        """Step 15: hr.rfid.ctrl.output.ts — per controller."""
        start = time.time()
        model = 'hr.rfid.ctrl.output.ts'
        if not self.b._has_model(model):
            return
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())
        fields_to_read = ['controller_id']
        for f in ['name', 'time_schedule_id', 'output_number']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)
        source_records = self.b._search_read(model, [], fields_to_read)
        imported = 0
        skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            ctrl_target_id = self.b._map_m2o('hr.rfid.ctrl', rec.get('controller_id'))
            if not ctrl_target_id:
                skipped += 1
                continue
            ts_target_id = self.b._map_m2o(
                'hr.rfid.time.schedule', rec.get('time_schedule_id')
            )
            vals = {'controller_id': ctrl_target_id}
            for f in ['name', 'output_number']:
                if f in rec and f in target_fields:
                    vals[f] = rec[f]
            if ts_target_id and 'time_schedule_id' in target_fields:
                vals['time_schedule_id'] = ts_target_id
            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._try_load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1
            else:
                skipped += 1

        self.results.append(self._make_result(
            model, len(source_records), imported, 0, skipped,
            duration=time.time() - start,
        ))

    def _import_alarms(self):
        """Step 16: hr.rfid.ctrl.alarm — depends on ctrl + door + alarm_group."""
        start = time.time()
        model = 'hr.rfid.ctrl.alarm'
        if not self.b._has_model(model):
            return
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())
        fields_to_read = ['controller_id']
        for f in ['name', 'alarm_group_id', 'time_schedule_id',
                  'control_output', 'line_number', 'armed', 'door_id']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)
        source_records = self.b._search_read(model, [], fields_to_read)
        imported = 0
        skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            ctrl_target_id = self.b._map_m2o('hr.rfid.ctrl', rec.get('controller_id'))
            if not ctrl_target_id:
                skipped += 1
                continue
            vals = {'controller_id': ctrl_target_id}
            if 'name' in rec and 'name' in target_fields:
                vals['name'] = rec.get('name', '')
            # Simple scalar fields
            for sf in ['control_output', 'line_number', 'armed']:
                if sf in rec and sf in target_fields and rec[sf] is not False:
                    vals[sf] = rec[sf]
            if rec.get('door_id') and 'door_id' in target_fields:
                door_target = self.b._map_m2o('hr.rfid.door', rec['door_id'])
                if door_target:
                    vals['door_id'] = door_target
            if rec.get('alarm_group_id') and 'alarm_group_id' in target_fields:
                ag_target = self.b._map_m2o(
                    'hr.rfid.ctrl.alarm.group', rec['alarm_group_id']
                )
                if ag_target:
                    vals['alarm_group_id'] = ag_target
            if rec.get('time_schedule_id') and 'time_schedule_id' in target_fields:
                ts_target = self.b._map_m2o(
                    'hr.rfid.time.schedule', rec['time_schedule_id']
                )
                if ts_target:
                    vals['time_schedule_id'] = ts_target
            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._try_load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1
            else:
                skipped += 1

        self.results.append(self._make_result(
            model, len(source_records), imported, 0, skipped,
            duration=time.time() - start,
        ))

    def _import_th_sensors(self):
        """Step 17: hr.rfid.ctrl.th — depends on ctrl + door."""
        start = time.time()
        model = 'hr.rfid.ctrl.th'
        if not self.b._has_model(model):
            return
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())
        fields_to_read = ['controller_id']
        for f in ['name', 'door_id']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)
        source_records = self.b._search_read(model, [], fields_to_read)
        imported = 0
        skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            ctrl_target_id = self.b._map_m2o('hr.rfid.ctrl', rec.get('controller_id'))
            if not ctrl_target_id:
                skipped += 1
                continue
            vals = {'controller_id': ctrl_target_id}
            if 'name' in rec and 'name' in target_fields:
                vals['name'] = rec.get('name', '')
            if rec.get('door_id') and 'door_id' in target_fields:
                door_target = self.b._map_m2o('hr.rfid.door', rec['door_id'])
                if door_target:
                    vals['door_id'] = door_target
            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._try_load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1
            else:
                skipped += 1

        self.results.append(self._make_result(
            model, len(source_records), imported, 0, skipped,
            duration=time.time() - start,
        ))

    def _import_zones(self):
        """Step 18: hr.rfid.zone — M2M: door_ids, departments, categories, employees, contacts."""
        start = time.time()
        model = 'hr.rfid.zone'
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())
        fields_to_read = ['name']
        for f in ['door_ids', 'permitted_department_ids',
                  'permitted_employee_category_ids', 'employee_ids',
                  'contact_ids', 'anti_passback', 'anti_pass_back',
                  'attendance', 'auto_close_time_for_zone',
                  'max_time_in_zone', 'overwrite_check_in',
                  'overwrite_check_out', 'log_out_on_exit',
                  'delete_attendance_if_late_more_than']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)
        source_records = self.b._search_read(model, [], fields_to_read)
        imported = 0
        prefix = model.replace('.', '_')

        # M2M field → model mapping
        m2m_models = {
            'door_ids': 'hr.rfid.door',
            'permitted_department_ids': 'hr.department',
            'permitted_employee_category_ids': 'hr.employee.category',
            'employee_ids': 'hr.employee',
            'contact_ids': 'res.partner',
        }

        for rec in source_records:
            vals = {'name': rec['name']}
            # Add scalar fields that are in both source and target
            for sf in ['anti_passback', 'anti_pass_back', 'attendance',
                       'auto_close_time_for_zone', 'max_time_in_zone',
                       'overwrite_check_in', 'overwrite_check_out',
                       'log_out_on_exit', 'delete_attendance_if_late_more_than']:
                if sf in rec and sf in target_fields and rec[sf] is not False:
                    vals[sf] = rec[sf]
            # Map M2M fields (only if they were read and exist in target)
            for m2m_field, m2m_model in m2m_models.items():
                if rec.get(m2m_field) and m2m_field in target_fields:
                    vals[m2m_field] = self.b._map_m2m(m2m_model, rec[m2m_field])

            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        self.results.append(self._make_result(
            model, len(source_records), imported,
            duration=time.time() - start,
        ))

    def _import_notifications(self):
        """Step 19: hr.rfid.notification — depends on zone + notify_partner_ids."""
        start = time.time()
        model = 'hr.rfid.notification'
        if not self.b._has_model(model):
            return
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        fields_to_read = ['name', 'notify_partner_ids']
        # Add event type selection fields that may exist
        for f in ['user_event_ids', 'sys_event_ids', 'zone_id',
                   'controller_id', 'door_id']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)

        source_records = self.b._search_read(model, [], fields_to_read)
        imported = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            vals = {'name': rec.get('name', '')}

            if rec.get('notify_partner_ids'):
                vals['notify_partner_ids'] = self.b._map_m2m(
                    'res.partner', rec['notify_partner_ids']
                )
            if rec.get('zone_id'):
                zone_target = self.b._map_m2o('hr.rfid.zone', rec['zone_id'])
                if zone_target:
                    vals['zone_id'] = zone_target
            if rec.get('controller_id'):
                ctrl_target = self.b._map_m2o('hr.rfid.ctrl', rec['controller_id'])
                if ctrl_target:
                    vals['controller_id'] = ctrl_target
            if rec.get('door_id'):
                door_target = self.b._map_m2o('hr.rfid.door', rec['door_id'])
                if door_target:
                    vals['door_id'] = door_target

            # Copy selection fields directly (event type selections)
            for f in ['user_event_ids', 'sys_event_ids']:
                if f in rec and f in target_fields:
                    vals[f] = rec[f]

            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        self.results.append(self._make_result(
            model, len(source_records), imported,
            duration=time.time() - start,
        ))
