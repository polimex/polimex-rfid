# -*- coding: utf-8 -*-
"""Phase 2c: Leaves - types, allocations and the absences themselves.

The owner's request (2026-08-14): being an HR system, customers usually run
the employees-and-leaves modules too, so the transfer carries them across.

hr.leave guards its lifecycle hard - state machines, double validation, mail
to approvers. Migrated absences are HISTORY: they were already approved on
the other system, so they enter through core's own import path -
``leave_fast_create`` + ``leave_skip_state_check``
(odoo/addons/hr_holidays/models/hr_leave.py:765,:890) - which core itself
uses to create leaves without replaying the approval theatre. No mail, no
activities, and hr_rfid_leave_block's card snapshot stays quiet: it reacts to
the validate ACTION, which history never fires again.
"""
import logging
import time

from .base_importer import IMPORT_CONTEXT
from .phase import PhaseImporter

_logger = logging.getLogger(__name__)

#: Lifecycle states worth carrying: approved history and requests mid-flight.
#: Refused and draft ones are the other system's noise.
LEAVE_STATES = ('confirm', 'validate1', 'validate')


class LeaveImporter(PhaseImporter):
    """Leave types, allocations, leaves - in that order (each needs the last)."""

    PHASE_ID = 'Phase 2c'
    NAME = 'Leaves'
    REQUIRES_SOURCE = ('hr_holidays',)
    REQUIRES_TARGET = ('hr.leave', 'hr.leave.type', 'hr.leave.allocation')
    OPTION = 'import_leaves'
    WEIGHT = 5

    def run(self, wizard):
        return self.steps(
            self._import_leave_types,
            self._import_allocations,
            self._import_leaves,
        )

    def _leave_env(self, model):
        """The model, entered the way core imports leaves - quietly."""
        return self.env[model].with_context(
            **IMPORT_CONTEXT,
            leave_fast_create=True,
            leave_skip_state_check=True,
        )

    def _import_leave_types(self):
        """Step 2c-1: hr.leave.type.

        Both sides ship standard types with the module - matched by their OWN
        external ids first (the card-type lesson: creating them again makes a
        second "Paid Time Off" the application does not recognise).
        """
        start = time.time()
        model = 'hr.leave.type'
        source_fields = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        fields_to_read = ['name'] + [
            f for f in ('active', 'requires_allocation', 'request_unit',
                        'time_type', 'color')
            if f in source_fields and f in target_fields]
        source_records = self.b._search_read(model, [], fields_to_read)
        shipped = self.b._match_by_external_id(
            model, [r['id'] for r in source_records])
        imported = linked = skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            if rec['id'] in shipped:
                linked += 1
                continue
            existing = self.b.find_by_external_id(model, rec['id'],
                                                  rec.get('name'))
            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
                linked += 1
                continue
            vals = {f: rec[f] for f in fields_to_read
                    if f != 'active' and rec.get(f) not in (None, False)}
            if 'active' in fields_to_read:
                vals['active'] = bool(rec.get('active'))
            created = self.b._load_records(model, [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }])
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1
            else:
                skipped += 1

        self.results.append(self.b._make_result(
            model, len(source_records), imported, linked, skipped,
            duration=time.time() - start,
        ))

    def _import_allocations(self):
        """Step 2c-2: hr.leave.allocation - approved balances only."""
        start = time.time()
        model = 'hr.leave.allocation'
        source_fields = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        fields_to_read = ['employee_id', 'holiday_status_id', 'state'] + [
            f for f in ('name', 'number_of_days', 'date_from', 'date_to',
                        'allocation_type')
            if f in source_fields and f in target_fields]
        source_records = self.b._read_all(
            model,
            [('state', '=', 'validate')] + self.b._scoped_domain('employee_id'),
            fields_to_read, cursor_key='leaves:%s' % model)
        imported = linked = skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            if rec.get('state') != 'validate':
                skipped += 1
                continue
            emp = self.b._map_m2o('hr.employee', rec.get('employee_id'))
            ltype = self.b._map_m2o('hr.leave.type', rec.get('holiday_status_id'))
            if not emp or not ltype:
                skipped += 1
                continue
            existing = self.b.find_by_external_id(model, rec['id'])
            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
                linked += 1
                continue
            # The allocation model refuses to be BORN approved ("Incorrect
            # state for new allocation") - so it enters the way a person
            # would: written down first, approved right after, both under the
            # quiet import contexts so nobody is asked to approve it again.
            vals = {
                'employee_id': emp,
                'holiday_status_id': ltype,
                'state': 'confirm',
            }
            for f in ('name', 'number_of_days', 'date_from', 'date_to',
                      'allocation_type'):
                if f in fields_to_read and rec.get(f) not in (None, False):
                    vals[f] = rec[f]
            created = self.b._try_load_records_quiet_env(
                self._leave_env(model), [{
                    'xml_id': self.b._xml_id(prefix, rec['id']),
                    'values': vals,
                    'noupdate': True,
                }])
            if created:
                try:
                    with self.env.cr.savepoint():
                        created.with_context(
                            **IMPORT_CONTEXT,
                            leave_skip_state_check=True,
                        ).write({'state': 'validate'})
                except Exception as exc:
                    _logger.warning(
                        "Allocation %s stayed unapproved: %s",
                        rec['id'], exc, exc_info=True)
                    self.b.note_skip_reason(str(exc).split('\n')[0][:160])
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1
            else:
                skipped += 1

        self.results.append(self.b._make_result(
            model, len(source_records), imported, linked, skipped,
            duration=time.time() - start,
        ))

    def _import_leaves(self):
        """Step 2c-3: hr.leave - the absences, in their real states."""
        start = time.time()
        model = 'hr.leave'
        source_fields = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        fields_to_read = ['employee_id', 'holiday_status_id', 'state',
                          'date_from', 'date_to'] + [
            f for f in ('request_date_from', 'request_date_to',
                        'number_of_days', 'name')
            if f in source_fields and f in target_fields]
        source_records = self.b._read_all(
            model,
            [('state', 'in', list(LEAVE_STATES))]
            + self.b._scoped_domain('employee_id'),
            fields_to_read, cursor_key='leaves:%s' % model)
        imported = linked = skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            # Belt over the domain: refused and draft ones are the other
            # system's noise and must not appear here even if a source hands
            # them over anyway.
            if rec.get('state') not in LEAVE_STATES:
                skipped += 1
                continue
            emp = self.b._map_m2o('hr.employee', rec.get('employee_id'))
            ltype = self.b._map_m2o('hr.leave.type', rec.get('holiday_status_id'))
            if not emp or not ltype:
                skipped += 1
                continue
            existing = self.b.find_by_external_id(model, rec['id'])
            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
                linked += 1
                continue
            vals = {
                'employee_id': emp,
                'holiday_status_id': ltype,
                'state': rec.get('state') or 'validate',
                'date_from': rec.get('date_from'),
                'date_to': rec.get('date_to'),
            }
            for f in ('request_date_from', 'request_date_to',
                      'number_of_days', 'name'):
                if f in fields_to_read and rec.get(f) not in (None, False):
                    vals[f] = rec[f]
            created = self.b._try_load_records_quiet_env(
                self._leave_env(model), [{
                    'xml_id': self.b._xml_id(prefix, rec['id']),
                    'values': vals,
                    'noupdate': True,
                }])
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1
            else:
                skipped += 1

        self.results.append(self.b._make_result(
            model, len(source_records), imported, linked, skipped,
            duration=time.time() - start,
        ))
