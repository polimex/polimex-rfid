# -*- coding: utf-8 -*-
import logging
import time

from odoo import _, fields
from odoo.exceptions import UserError
from .base_importer import BaseImporter, IMPORT_CONTEXT
from .phase import PhaseImporter

_logger = logging.getLogger(__name__)


class AccessImporter(PhaseImporter):
    """Phase 4: Access Control.

    Steps: access.group (two passes for inherited_ids),
           AG door rels, AG employee rels, AG contact rels,
           cards (triggers chain regeneration),
           department second pass for AG back-references.
    """

    PHASE_ID = 'Phase 4'
    NAME = 'Access Control'
    REQUIRES_SOURCE = ('hr_rfid',)
    REQUIRES_TARGET = ('hr.rfid.access.group', 'hr.rfid.card')
    OPTION = 'import_access'
    WEIGHT = 13

    def run(self, wizard):
        """Execute Phase 4. Each step stands on its own."""
        return self.steps(
            self._import_access_groups,
            self._import_ag_door_rels,
            self._import_ag_employee_rels,
            self._import_ag_contact_rels,
            self._import_cards,
            self._department_second_pass,
        )

    def _import_access_groups(self):
        """Step 20: hr.rfid.access.group - TWO PASSES (inherited_ids M2M self-ref).

        Pass 1: Create all AGs without inherited_ids and department_ids.
        Pass 2: Update inherited_ids + department_ids with mapped IDs.
        """
        start = time.time()
        model = 'hr.rfid.access.group'
        co_domain = self.b._company_domain()
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        fields_to_read = ['name', 'company_id', 'inherited_ids', 'department_ids']
        for f in ['active', 'description', 'delay_between_events']:
            if f in source_fields_info:
                fields_to_read.append(f)

        source_records = self.b._search_read(model, co_domain, fields_to_read)
        imported = 0
        linked = 0
        prefix = model.replace('.', '_')

        # Pass 1: Create without inherited_ids / department_ids
        for rec in source_records:
            target_company_id = self.b._map_company(rec['company_id'])
            if not target_company_id:
                continue

            # Identity comes ONLY from the source id, through its external
            # ID. The text is a second check on the record already found, not
            # a key to search by.
            existing = self.b.find_by_external_id(model, rec['id'], rec.get('name'))
            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
                linked += 1
                continue

            vals = {
                'name': rec['name'],
                'company_id': target_company_id,
            }
            if rec.get('description'):
                vals['description'] = rec['description']
            if 'active' in rec:
                vals['active'] = rec['active']
            if rec.get('delay_between_events') and 'delay_between_events' in target_fields:
                vals['delay_between_events'] = rec['delay_between_events']

            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        # Pass 2: Update inherited_ids + department_ids
        for rec in source_records:
            # _map_m2o, not the in-memory map alone: a later pass builds a
            # fresh importer whose map starts empty, and the record of
            # finished steps stops pass 1 from filling it again. Read straight
            # from the map it would find nothing and do nothing, silently.
            target_id = self.b._map_m2o(model, rec['id'])
            if not target_id:
                continue
            update_vals = {}

            if rec.get('inherited_ids'):
                update_vals['inherited_ids'] = self.b._map_m2m(model, rec['inherited_ids'])

            if rec.get('department_ids'):
                update_vals['department_ids'] = self.b._map_m2m(
                    'hr.department', rec['department_ids']
                )

            if update_vals:
                self.env[model].browse(target_id).with_context(
                    **IMPORT_CONTEXT
                ).write(update_vals)

        self.results.append(self.b._make_result(
            model, len(source_records), imported, linked,
            duration=time.time() - start,
        ))

    def _import_ag_door_rels(self):
        """Step 21: hr.rfid.access.group.door.rel - AG↔Door relations.

        Chain: update_door_rels() fires but no AG employee rels yet → chain stops.
        write_ts_id() is suppressed by no_hardware_commands.
        """
        start = time.time()
        model = 'hr.rfid.access.group.door.rel'
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())
        fields_to_read = ['access_group_id', 'door_id']
        for f in ['time_schedule_id', 'alarm_rights']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)
        source_records = self.b._search_read(
            model, self.b._scoped_domain('access_group_id'), fields_to_read)
        imported = 0
        linked = 0
        skipped = 0
        unmapped = []
        prefix = model.replace('.', '_')

        for rec in source_records:
            # A door permission that is already here is recognised and left
            # alone. It cannot be refreshed even in principle: the model
            # forbids writing to it outright (hr_rfid_access_group.py, write()
            # raises), because a changed permission has to be taken away and
            # granted again for the doors to be told. Without this, every
            # repeat transfer tried the refused write on every permission,
            # ended the step with nothing landed, and reported the whole
            # transfer as stopped by a problem - over data that was already
            # correctly in place.
            existing = self.b.find_by_external_id(model, rec['id'])
            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
                linked += 1
                continue

            ag_target = self.b._map_m2o(
                'hr.rfid.access.group', rec.get('access_group_id')
            )
            door_target = self.b._map_m2o('hr.rfid.door', rec.get('door_id'))
            if not ag_target or not door_target:
                skipped += 1
                # The row must carry its own diagnosis (owner's rule,
                # 2026-08-15): a live protocol showed "4 skipped" and could not
                # say WHICH pointer failed for WHICH source record - the
                # operator had to ship the protocol out for a guess.
                unmapped.append(self.env._(
                    "permission %(rel)s: %(what)s №%(src)s from the other "
                    "system has no match here",
                    rel=rec['id'],
                    what=(self.env._("door")
                          if ag_target else self.env._("access group")),
                    src=self.b._m2o_id(
                        rec.get('door_id') if ag_target
                        else rec.get('access_group_id')),
                ))
                continue

            ts_target = False
            if rec.get('time_schedule_id'):
                ts_target = self.b._map_m2o(
                    'hr.rfid.time.schedule', rec['time_schedule_id']
                )

            vals = {
                'access_group_id': ag_target,
                'door_id': door_target,
            }
            if 'alarm_rights' in rec and 'alarm_rights' in target_fields:
                vals['alarm_rights'] = rec.get('alarm_rights', False)
            if ts_target and 'time_schedule_id' in target_fields:
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

        self.results.append(self.b._make_result(
            model, len(source_records), imported, linked, skipped,
            duration=time.time() - start,
            error='; '.join(unmapped[:8]),
        ))

    def _import_ag_employee_rels(self):
        """Step 22: hr.rfid.access.group.employee.rel - exact copy from source.

        Chain: _compute_state → _activate → update_card_rels
        But employees have no cards yet → chain stops at _activate.

        Rows the ORM path refuses are copied verbatim instead of being dropped
        (D41) - see :meth:`_copy_ag_employee_rels_verbatim`.
        """
        start = time.time()
        model = 'hr.rfid.access.group.employee.rel'
        source_fields_info = self.b._get_source_fields(model)

        fields_to_read = ['access_group_id', 'employee_id']
        # v15+ fields
        for f in ['state', 'internal_state', 'activate_on', 'expiration',
                   'visits_counting', 'permitted_visits', 'visits_counter']:
            if f in source_fields_info:
                fields_to_read.append(f)

        source_records = self.b._search_read(
            model, self.b._scoped_domain('access_group_id'), fields_to_read)
        imported = 0
        skipped = 0
        prefix = model.replace('.', '_')
        refused = []

        for rec in source_records:
            ag_target = self.b._map_m2o(
                'hr.rfid.access.group', rec.get('access_group_id')
            )
            emp_target = self.b._map_m2o('hr.employee', rec.get('employee_id'))
            if not ag_target or not emp_target:
                skipped += 1
                continue

            vals = {
                'access_group_id': ag_target,
                'employee_id': emp_target,
            }
            # v15+ fields with defaults for v14
            for f in ['state', 'internal_state']:
                if f in rec and rec[f]:
                    vals[f] = rec[f]
                elif f not in source_fields_info:
                    vals[f] = 'active'  # v14 default

            if 'activate_on' in rec and rec['activate_on']:
                vals['activate_on'] = rec['activate_on']
            if 'expiration' in rec and rec['expiration']:
                vals['expiration'] = rec['expiration']

            for f in ['visits_counting', 'permitted_visits', 'visits_counter']:
                if f in rec:
                    vals[f] = rec[f]

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
                refused.append((rec['id'], vals))

        copied = self._copy_ag_rels_verbatim(model, 'employee_id', refused)
        skipped += len(refused) - copied

        self.results.append(self.b._make_result(
            model, len(source_records), imported + copied, 0, skipped,
            duration=time.time() - start,
        ))

    # Written by the ORM, so a verbatim row must carry exactly these columns
    # (plus the owner FK, which differs per relation class).
    _AG_REL_COLUMNS = (
        'access_group_id', 'state', 'internal_state', 'activate_on',
        'expiration', 'visits_counting', 'permitted_visits', 'visits_counter',
    )

    def _copy_ag_rels_verbatim(self, model, owner_column, refused):
        """Copy memberships the v19 model layer refuses to create (D41).

        Both relation classes hold legacy rows that today's model layer would
        no longer accept - the check is word for word identical in v15, so the
        source could not recreate them either. Measured on the o15 cloud:

        * employees - ``hr.employee.check_access_group`` demands the access
          group be one of those allowed on the employee's DEPARTMENT, so an
          employee with no department matches an empty set and every group is
          rejected. 234 rows for one tenant: 210 active employees, 176 holding
          a live card, 2 120 card→door permissions. Dropping them means those
          people lose access at cutover.
        * contacts - ``_check_constrains_contacts`` rejects overlapping active
          periods for the same group. 3 rows, all expired service periods,
          two of them with an expiration BEFORE the activation.

        A migration copies, it does not clean (D15). The row is inserted
        exactly as the source holds it and the derived card→door permissions
        are then built by the MODULE'S OWN ``_activate`` - no reimplemented
        logic. Only the Python-level check is bypassed; every database
        constraint still applies, so a genuinely broken row is still rejected
        and reported rather than forced in.
        """
        if not refused:
            return 0
        Model = self.env[model]
        value_columns = list(self._AG_REL_COLUMNS) + [owner_column]
        # The model's OWN defaults for whatever the source did not carry, so a
        # verbatim row is indistinguishable from an ORM-created one except for
        # the check that was skipped.
        defaults = Model.default_get(value_columns)
        columns = value_columns + [
            'create_uid', 'write_uid', 'create_date', 'write_date']
        now = fields.Datetime.now()
        rows, source_ids = [], []
        for source_id, vals in refused:
            # Core does the Python->column conversion. Writing the raw values
            # would send a v14 selection string ('active') into a v19 Boolean
            # column - the ORM path coerces it silently, SQL does not.
            row = [
                Model._fields[c].convert_to_column_insert(
                    vals[c] if c in vals else defaults.get(c), Model)
                for c in value_columns
            ]
            rows.append(tuple(row + [self.env.uid, self.env.uid, now, now]))
            source_ids.append(source_id)

        # Isolated: these rows are inserted precisely BECAUSE the model layer
        # objected, so a failure here must cost the phase nothing. A rollback
        # takes the external IDs with it, so the next run retries cleanly.
        try:
            with self.env.cr.savepoint():
                inserted, already, rejected = self.b._direct_sql_insert_tracked(
                    Model._table, columns, rows, model, source_ids)
                copied = inserted + already
                if not copied:
                    return 0
                if inserted:
                    # The module's own activation builds the card→door
                    # permissions. It is a no-op while the tenant's cards are
                    # still unimported (they follow in step 24) - the card
                    # import then picks the rows up like any other.
                    #
                    # Only for rows this run actually inserted. Rows that were
                    # already here have been activated once and would come out
                    # the same; at one customer that is 2 120 permissions
                    # rebuilt on every later run for nothing.
                    target_ids = [
                        tid for tid in
                        (self.b._get_target_id(model, sid) for sid in source_ids) if tid]
                    if target_ids:
                        Model.browse(target_ids).with_context(**IMPORT_CONTEXT)._activate()
        except Exception:
            for sid in source_ids:
                self.b.id_map.get(model, {}).pop(sid, None)
            _logger.warning(
                "%s: the verbatim copy of %d refused membership(s) failed - "
                "they stay unmigrated and are reported as skipped",
                model, len(refused), exc_info=True)
            return 0

        if inserted or rejected:
            _logger.warning(
                "%s: %d membership(s) the v19 model layer refuses were copied "
                "verbatim from the source (D41); %d rejected by the database",
                model, inserted, rejected)
        else:
            # Every one of them was already here - a re-run over correct data,
            # not something an operator needs to be told about again.
            _logger.debug("%s: %d refused membership(s) already copied earlier",
                          model, already)
        return copied

    def _import_ag_contact_rels(self):
        """Step 23: hr.rfid.access.group.contact.rel - exact copy from source."""
        start = time.time()
        model = 'hr.rfid.access.group.contact.rel'
        source_fields_info = self.b._get_source_fields(model)

        fields_to_read = ['access_group_id', 'contact_id']
        for f in ['state', 'internal_state', 'activate_on', 'expiration',
                   'visits_counting', 'permitted_visits', 'visits_counter']:
            if f in source_fields_info:
                fields_to_read.append(f)
        # v14 typo: permited_visits
        if 'permited_visits' in source_fields_info and 'permitted_visits' not in source_fields_info:
            fields_to_read.append('permited_visits')

        source_records = self.b._search_read(
            model, self.b._scoped_domain('access_group_id'), fields_to_read)
        imported = 0
        skipped = 0
        prefix = model.replace('.', '_')
        refused = []

        for rec in source_records:
            ag_target = self.b._map_m2o(
                'hr.rfid.access.group', rec.get('access_group_id')
            )
            contact_target = self.b._map_m2o('res.partner', rec.get('contact_id'))
            if not ag_target or not contact_target:
                skipped += 1
                continue

            vals = {
                'access_group_id': ag_target,
                'contact_id': contact_target,
            }
            for f in ['state', 'internal_state']:
                if f in rec and rec[f]:
                    vals[f] = rec[f]
                elif f not in source_fields_info:
                    vals[f] = 'active'

            if 'activate_on' in rec and rec['activate_on']:
                vals['activate_on'] = rec['activate_on']
            if 'expiration' in rec and rec['expiration']:
                vals['expiration'] = rec['expiration']

            # Handle v14 typo: permited_visits → permitted_visits
            if 'permited_visits' in rec:
                vals['permitted_visits'] = rec['permited_visits']
            elif 'permitted_visits' in rec:
                vals['permitted_visits'] = rec['permitted_visits']

            for f in ['visits_counting', 'visits_counter']:
                if f in rec:
                    vals[f] = rec[f]

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
                refused.append((rec['id'], vals))

        copied = self._copy_ag_rels_verbatim(model, 'contact_id', refused)
        skipped += len(refused) - copied

        self.results.append(self.b._make_result(
            model, len(source_records), imported + copied, 0, skipped,
            duration=time.time() - start,
        ))

    def _import_cards(self):
        """Step 24: hr.rfid.card - with EXACT active state from source.

        Chain: update_card_rels → get_potential_access_doors → AG rels (from step 22/23)
              → AG door rels (from step 21) → check_relevance_fast → card_ready()
              → create CardDoorRel → _create_add_card_command → SUPPRESSED
        Card-door rels are REGENERATED here automatically!
        """
        start = time.time()
        model = 'hr.rfid.card'
        co_domain = self.b._company_domain()
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        # Required fields
        fields_to_read = ['number', 'company_id', 'active']
        # Optional fields
        for f in ['name', 'card_type', 'employee_id', 'contact_id',
                  'card_active', 'activate_on', 'deactivate_on', 'pin_code',
                  'card_input_type', 'cloud_card', 'card_reference',
                  'internal_number']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)

        source_records = self.b._read_all(model, co_domain, fields_to_read)
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

            target_company_id = self.b._map_company(rec.get('company_id'))
            if not target_company_id:
                skipped += 1
                continue

            card_type_target = False
            if rec.get('card_type'):
                card_type_target = self.b._map_m2o('hr.rfid.card.type', rec['card_type'])

            vals = {
                'number': rec['number'],
                'company_id': target_company_id,
                'active': rec.get('active', True),
            }
            # card_active: only if field exists in target (removed in v19)
            if 'card_active' in target_fields and 'card_active' in rec:
                vals['card_active'] = rec.get('card_active', True)
            # pin_code: computed in v19, skip
            if card_type_target:
                vals['card_type'] = card_type_target

            # Owner: employee or contact (not both)
            if rec.get('employee_id'):
                emp_target = self.b._require_target_id(
                    'hr.employee', rec['employee_id'],
                    context_msg=f"Card #{rec['id']} ({rec['number']})",
                )
                if emp_target:
                    vals['employee_id'] = emp_target
            elif rec.get('contact_id'):
                contact_target = self.b._require_target_id(
                    'res.partner', rec['contact_id'],
                    context_msg=f"Card #{rec['id']} ({rec['number']})",
                )
                if contact_target:
                    vals['contact_id'] = contact_target

            # Date fields
            if rec.get('activate_on'):
                vals['activate_on'] = rec['activate_on']
            if rec.get('deactivate_on'):
                vals['deactivate_on'] = rec['deactivate_on']

            # Optional fields
            if rec.get('card_input_type') and 'card_input_type' in target_fields:
                vals['card_input_type'] = rec['card_input_type']
            elif 'card_input_type' in target_fields and 'card_input_type' not in source_fields_info:
                vals['card_input_type'] = 'w34s'  # v14 default

            if rec.get('cloud_card') and 'cloud_card' in target_fields:
                vals['cloud_card'] = rec['cloud_card']

            # Additional card fields
            for f in ['card_reference', 'internal_number']:
                if rec.get(f) and f in target_fields:
                    vals[f] = rec[f]

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

        self.results.append(self.b._make_result(
            model, len(source_records), imported, linked, skipped,
            duration=time.time() - start,
        ))

    def _department_second_pass(self):
        """Step 25: hr.department SECOND PASS - update AG back-references.

        Sets hr_rfid_default_access_group and hr_rfid_allowed_access_groups
        which point from department to access groups.

        Always reports a line, even when there was nothing to set. Without one,
        "the other system keeps no default groups" and "this step never ran"
        look exactly alike in the protocol - and the second is what happens
        when a later pass finds the map in memory empty.
        """
        start = time.time()
        model = 'hr.department'
        label = f'{model} (AG refs)'
        co_domain = self.b._company_domain()
        source_fields_info = self.b._get_source_fields(model)

        if 'hr_rfid_default_access_group' not in source_fields_info:
            self.results.append(self.b._make_result(
                label, 0, 0, status='skipped',
                error=self.env._(
                    "The other system does not give departments a default "
                    "access group, so there was nothing to carry over."),
                duration=time.time() - start,
            ))
            return

        source_records = self.b._search_read(
            model, co_domain,
            ['hr_rfid_default_access_group', 'hr_rfid_allowed_access_groups'],
        )
        # Counted against the departments that actually carry a group, not
        # against every department: a department with nothing to set is not a
        # miss, while a department that HAS one and did not get it is.
        expected = 0
        updated = 0

        for rec in source_records:
            update_vals = {}
            if rec.get('hr_rfid_default_access_group'):
                ag_target = self.b._map_m2o(
                    'hr.rfid.access.group', rec['hr_rfid_default_access_group']
                )
                if ag_target:
                    update_vals['hr_rfid_default_access_group'] = ag_target

            if rec.get('hr_rfid_allowed_access_groups'):
                update_vals['hr_rfid_allowed_access_groups'] = self.b._map_m2m(
                    'hr.rfid.access.group', rec['hr_rfid_allowed_access_groups']
                )

            if not (rec.get('hr_rfid_default_access_group')
                    or rec.get('hr_rfid_allowed_access_groups')):
                continue
            expected += 1

            # _map_m2o, not the in-memory map alone: a later pass builds a
            # fresh importer whose map starts empty, and the record of
            # finished steps stops the department step from filling it again.
            # Read straight from the map this found nothing and left every
            # department without its default access group, silently.
            target_id = self.b._map_m2o(model, rec['id'])
            if not target_id or not update_vals:
                continue

            self.env[model].browse(target_id).with_context(
                **IMPORT_CONTEXT
            ).write(update_vals)
            updated += 1

        self.results.append(self.b._make_result(
            label, expected, updated,
            skipped_count=expected - updated,
            duration=time.time() - start,
        ))
