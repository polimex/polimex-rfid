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

#: "Does this kind of leave need a balance first?" - asked with words on the
#: older systems ('yes' / 'no', where "no" is labelled "No Limit") and with a
#: yes/no box here. Carried over as it stands, the WORD "no" is a non-empty
#: string, so it arrives as YES: a kind of leave that needed no balance at all
#: starts demanding one, and every absence of that kind is then refused on the
#: way in - "%(name)s does not have a valid allocation". Measured on the cloud:
#: 14 of its 22 kinds said "no", and 72 of 1 083 approved absences were turned
#: away, with the message blaming the employee.
NEEDS_BALANCE_WORDS = {'yes': True, 'true': True, '1': True,
                       'no': False, 'false': False, '0': False, '': False,
                       # Odoo 14 asks the same question under another name and
                       # with three answers: "No Limit", "Allow Employees
                       # Requests", "Set by Time Off Officer". Only the first
                       # means no balance is needed. Unread, every kind of
                       # leave arrived demanding one, and 2 848 of an Odoo 14
                       # tenant's 3 300 approved absences were refused - 86 per
                       # cent of its history.
                       'fixed': True, 'fixed_allocation': True,
                       'unlimited': False}


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

    @staticmethod
    def _needs_balance(value):
        """The older system's word for it, as the yes/no box here.

        An unknown word keeps the strict answer (a balance IS needed) rather
        than quietly making a kind of leave more permissive than the other
        system had it - a refusal is loud and can be put right; a policy
        loosened behind the operator's back is not.
        """
        if isinstance(value, str):
            known = NEEDS_BALANCE_WORDS.get(value.strip().lower())
            if known is None:
                _logger.warning(
                    "Leave type says %r about needing a balance - a word this "
                    "transfer does not know; kept as 'needed'", value)
                return True
            return known
        return bool(value)

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
                        'time_type', 'color', 'company_id')
            if f in source_fields and f in target_fields]
        # The same question under the name the older versions use. Read
        # separately because the field does not exist HERE, so the intersection
        # above would drop it.
        older_name = ('allocation_type'
                      if 'requires_allocation' not in fields_to_read
                      and 'allocation_type' in source_fields else None)
        if older_name:
            fields_to_read.append(older_name)
        # Every tenant, because a type belongs to one: read without a company
        # filter, but each one lands under ITS OWN company below. Created
        # without one, all 22 types of the 27-tenant cloud became global and
        # every tenant was offered the other twenty-six's leave types.
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
                    if f not in ('active', 'company_id')
                    and rec.get(f) not in (None, False)}
            if 'active' in fields_to_read:
                vals['active'] = bool(rec.get('active'))
            if older_name:
                vals.pop(older_name, None)
                if 'requires_allocation' in target_fields:
                    vals['requires_allocation'] = self._needs_balance(
                        rec.get(older_name))
            if 'requires_allocation' in vals:
                vals['requires_allocation'] = self._needs_balance(
                    vals['requires_allocation'])
            if 'company_id' in fields_to_read:
                # A type of a tenant that is NOT part of this transfer must
                # not arrive as a global one - it would be offered to every
                # tenant in the base. Left out entirely instead.
                if rec.get('company_id'):
                    target_company = self.b._map_company(rec['company_id'])
                    if not target_company:
                        skipped += 1
                        continue
                    vals['company_id'] = target_company
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

        # Read in one go (a handful of types) - no slicing, no running totals.
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
        cursor_key = 'leaves:%s' % model
        source_records = self.b._read_all(
            model,
            [('state', '=', 'validate')] + self.b._scoped_domain('employee_id'),
            fields_to_read, cursor_key)
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

        self.results.append(self.b.accumulated_result(
            cursor_key, model, len(source_records), imported, linked, skipped,
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
        cursor_key = 'leaves:%s' % model
        source_records = self.b._read_all(
            model,
            [('state', 'in', list(LEAVE_STATES))]
            + self.b._scoped_domain('employee_id'),
            fields_to_read, cursor_key)
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

        note = ''
        if skipped:
            # The reasons underneath are this system's own words, and they read
            # as if the person were at fault ("X does not have a valid
            # allocation"). What actually happened is that the absence was
            # approved over there under a rule this system applies more
            # strictly, so the operator needs to know it is about balances and
            # that the transfer will finish the job once they exist.
            note = self.env._(
                "%(count)s absence(s) already approved on the other system "
                "were not accepted here: this system requires a balance that "
                "covers them, and it does not. Two ways on, both of them "
                "yours to choose: give those people the missing allocation, "
                "or - if that kind of leave never needed a balance over there "
                "- untick \"Requires allocation\" on it here. Then run the "
                "transfer again: it brings exactly the ones still missing.",
                count=skipped)
        self.results.append(self.b.accumulated_result(
            cursor_key, model, len(source_records), imported, linked, skipped,
            duration=time.time() - start, error=note,
        ))
