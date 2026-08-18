# -*- coding: utf-8 -*-
import logging
import time

from odoo import _
from odoo.exceptions import UserError
from .base_importer import BaseImporter, IMPORT_CONTEXT
from .phase import PhaseImporter

_logger = logging.getLogger(__name__)


#: The vending profile of a person: the money, the limits and the permissions.
#: Every name exists on the target model - asserted by a test. The previous
#: list named seven that exist in NEITHER version ('..._auto_refill_amount',
#: '..._limit_type', '..._pin', '..._negbal' among them) and left out five that
#: do, so everybody arrived with a balance and none of the rules that govern
#: spending it. Computed ones are deliberately absent: the current balance and
#: today's spend are worked out from these.
EMPLOYEE_VENDING_FIELDS = [
    'hr_rfid_vending_in_attendance', 'hr_rfid_vending_limit',
    'hr_rfid_vending_balance', 'hr_rfid_vending_auto_refill',
    'hr_rfid_vending_refill_amount', 'hr_rfid_vending_refill_type',
    'hr_rfid_vending_refill_max', 'hr_rfid_vending_negative_balance',
    'hr_rfid_vending_daily_limit', 'hr_rfid_vending_recharge_balance',
]

#: What a refill RUN is: when it happened and how much money it moved. The
#: total is REQUIRED on the record, and the step used to ask for 'amount' and
#: 'period' - names in neither version - so every run was refused by the
#: database and every balance entry pointing at one lost its link.
AUTO_REFILL_OPTIONAL_FIELDS = ['auto_refill_total', 'create_date']


class VendingImporter(PhaseImporter):
    """Phase 6a: Vending data.

    Steps: product.template, vending.row, vending.settings,
           auto.refill, vending.event, balance.history,
           employee vending fields.
    """

    PHASE_ID = 'Phase 6a'
    NAME = 'Vending'
    REQUIRES_SOURCE = ('hr_rfid_vending',)
    REQUIRES_TARGET = ('hr.rfid.vending.event', 'hr.rfid.ctrl.vending.row')
    OPTION = 'import_vending'
    WEIGHT = 10

    def run(self, wizard):
        """Execute Phase 6a: Vending."""
        self._import_products()
        self._import_vending_rows()
        self._import_vending_settings()
        self._import_auto_refill()
        self._import_vending_events()
        self._import_balance_history()
        self._update_employee_vending_fields()
        return self.results

    def _import_products(self):
        """Step 29: product.template - match by default_code, fallback name."""
        start = time.time()
        model = 'product.template'

        # Check if product_id field exists in vending rows (not in all versions)
        vrow_fields = self.b._get_source_fields('hr.rfid.ctrl.vending.row')
        if 'product_id' not in vrow_fields:
            return

        # Products used in vending rows - AND the ones only the sales
        # mention. A row says what a machine offers TODAY; an event says what
        # was actually sold, including from a slot since re-stocked. Taking
        # only the rows left 2 907 of the cloud's 31 118 sales pointing at a
        # product that never arrived, so the vending report cannot say what
        # was bought.
        vending_rows = self.b._search_read(
            'hr.rfid.ctrl.vending.row', [],
            ['product_id'],
        )
        referenced = [r.get('product_id') for r in vending_rows]
        event_fields = self.b._get_source_fields('hr.rfid.vending.event')
        if 'item_sold_id' in event_fields:
            referenced += [
                r.get('item_sold_id') for r in self.b._search_read(
                    'hr.rfid.vending.event',
                    self.b._scoped_domain('reader_id.controller_id.webstack_id')
                    + [('item_sold_id', '!=', False)],
                    ['item_sold_id'])]
        product_ids = list({self.b._m2o_id(value)
                            for value in referenced if value})
        if not product_ids:
            return

        source_records = self.b._search_read(
            model,
            [('id', 'in', product_ids)],
            ['name', 'default_code', 'list_price', 'type'],
        )
        imported = 0
        linked = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            # Identity comes ONLY from the source id, through its external
            # ID. The text is a second check on the record already found, not
            # a key to search by.
            existing = self.b.find_by_external_id(model, rec['id'], rec.get('name'))

            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
                linked += 1
            else:
                vals = {
                    'name': rec['name'],
                    'list_price': rec.get('list_price', 0.0),
                    'type': rec.get('type', 'consu'),
                }
                if rec.get('default_code'):
                    vals['default_code'] = rec['default_code']
                data_list = [{
                    'xml_id': self.b._xml_id(prefix, rec['id']),
                    'values': vals,
                    'noupdate': True,
                }]
                created = self.b._load_records(model, data_list)
                if created:
                    self.b._set_target_id(model, rec['id'], created.id)
                    imported += 1

        self.results.append(self.b._make_result(
            model, len(source_records), imported, linked,
            duration=time.time() - start,
        ))

    def _import_vending_rows(self):
        """Step 30: hr.rfid.ctrl.vending.row - depends on ctrl + product."""
        start = time.time()
        model = 'hr.rfid.ctrl.vending.row'
        source_fields_info = self.b._get_source_fields(model)
        # Real columns only - a non-stored field in a raw INSERT is an
        # UndefinedColumn that kills the whole step.
        target_fields = self.b._target_columns(model)
        fields_to_read = ['controller_id']
        # row_number (v15) or row_num (v19) - detect source field name
        for f in ['name', 'product_id', 'row_number', 'row_num', 'price']:
            if f in source_fields_info:
                fields_to_read.append(f)
        source_records = self.b._search_read(
            model, self.b._scoped_domain('controller_id.webstack_id'), fields_to_read,
        )
        imported = 0
        skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            ctrl_target = self.b._map_m2o('hr.rfid.ctrl', rec.get('controller_id'))
            if not ctrl_target:
                skipped += 1
                continue
            vals = {
                'controller_id': ctrl_target,
            }
            if rec.get('name') and 'name' in target_fields:
                vals['name'] = rec['name']
            # Map row_number (source v15) → row_num (target v19)
            row_val = rec.get('row_num') or rec.get('row_number')
            if row_val is not None and 'row_num' in target_fields:
                vals['row_num'] = row_val
            elif row_val is not None and 'row_number' in target_fields:
                vals['row_number'] = row_val
            if rec.get('price') is not None and 'price' in target_fields:
                vals['price'] = rec.get('price', 0.0)
            if rec.get('product_id'):
                product_target = self.b._map_m2o('product.template', rec['product_id'])
                if product_target:
                    vals['product_id'] = product_target

            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._try_load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        self.results.append(self.b._make_result(
            model, len(source_records), imported, 0, skipped,
            duration=time.time() - start,
        ))

    def _import_vending_settings(self):
        """Step 31: hr.rfid.ctrl.vending.settings - depends on ctrl."""
        start = time.time()
        model = 'hr.rfid.ctrl.vending.settings'
        if not self.b._has_model(model):
            self.results.append(self.b._make_result(model, 0, 0, status='skipped'))
            return
        source_records = self.b._search_read(
            model, self.b._scoped_domain('controller_id.webstack_id'),
            ['name', 'controller_id', 'vending_row_ids'],
        )
        imported = 0
        skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            ctrl_target = self.b._map_m2o('hr.rfid.ctrl', rec.get('controller_id'))
            if not ctrl_target:
                skipped += 1
                continue
            vals = {
                'name': rec.get('name', ''),
                'controller_id': ctrl_target,
            }
            if rec.get('vending_row_ids'):
                vals['vending_row_ids'] = self.b._map_m2m(
                    'hr.rfid.ctrl.vending.row', rec['vending_row_ids']
                )
            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        self.results.append(self.b._make_result(
            model, len(source_records), imported, 0, skipped,
            duration=time.time() - start,
        ))

    def _import_auto_refill(self):
        """Step 32: hr.rfid.vending.auto.refill - company-level."""
        start = time.time()
        model = 'hr.rfid.vending.auto.refill'
        if not self.b._has_model(model):
            self.results.append(self.b._make_result(model, 0, 0, status='skipped'))
            return
        co_domain = self.b._company_domain()
        source_fields_info = self.b._get_source_fields(model)
        # Real columns only - a non-stored field in a raw INSERT is an
        # UndefinedColumn that kills the whole step.
        target_fields = self.b._target_columns(model)

        # What a refill RUN is: when it happened and how much money it put on
        # people's balances. The total is required on the record, and it was
        # never read at all - the step asked for 'amount' and 'period', which
        # exist in neither version - so all 3 546 runs of the cloud were
        # refused by the database ("null value in column auto_refill_total")
        # and every balance entry that pointed at one lost the link.
        fields_to_read = ['name', 'company_id']
        for f in AUTO_REFILL_OPTIONAL_FIELDS:
            if f in source_fields_info:
                fields_to_read.append(f)

        source_records = self.b._search_read(
            model, co_domain, fields_to_read,
        )
        imported = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            target_company_id = self.b._map_company(rec.get('company_id'))
            if not target_company_id:
                continue
            vals = {
                'name': rec.get('name', ''),
                'company_id': target_company_id,
            }
            for f in AUTO_REFILL_OPTIONAL_FIELDS:
                if f in fields_to_read and f in target_fields \
                        and rec.get(f) not in (None, False):
                    vals[f] = rec[f]
            if 'auto_refill_total' in target_fields:
                # Required on the record: a run that says nothing about how
                # much it moved is refused outright, and with it goes the
                # link from every balance entry it produced.
                vals.setdefault('auto_refill_total', 0.0)
            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._try_load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        self.results.append(self.b._make_result(
            model, len(source_records), imported,
            duration=time.time() - start,
        ))

    def _import_vending_events(self):
        """Step 33: hr.rfid.vending.event - Direct SQL batch (separate table)."""
        start = time.time()
        model = 'hr.rfid.vending.event'
        table = 'hr_rfid_vending_event'

        domain = []
        date_from = self.b.options.get('event_date_from')
        if date_from:
            domain.append(('event_time', '>=', date_from))

        source_fields_info = self.b._get_source_fields(model)
        # Real columns only - a non-stored field in a raw INSERT is an
        # UndefinedColumn that kills the whole step.
        target_fields = self.b._target_columns(model)
        fields_to_read = ['event_time']
        for f in ['event_action', 'door_id', 'reader_id', 'card_id',
                  'employee_id', 'contact_id', 'controller_id',
                  'transaction_price', 'item_sold', 'item_sold_id']:
            if f in source_fields_info:
                fields_to_read.append(f)
        cursor_key = 'vending:%s' % model
        source_records = self.b._read_all(
            # Scope on reader_id, NOT door_id: the source leaves door_id NULL on
            # every vending event (32046/32046), and a dotted domain compiles to
            # EXISTS - a NULL link never matches, so scoping there would drop the
            # whole vending history while reporting "this client has none".
            # reader_id is required=True on the model and NOT NULL in the target.
            model, self.b._scoped_domain('reader_id.controller_id.webstack_id') + domain,
            fields_to_read, cursor_key, batch_size=2000,
        )
        imported = 0
        already = 0
        rejected = 0
        skipped = 0

        columns = ['event_time']
        for f in ['event_action', 'door_id', 'reader_id', 'card_id',
                  'employee_id', 'contact_id', 'controller_id',
                  'transaction_price', 'item_sold', 'item_sold_id']:
            if f in target_fields and f in fields_to_read:
                columns.append(f)

        # M2O field → (model, skip_if_unmapped)
        m2o_models = {
            'door_id': ('hr.rfid.door', True),
            'reader_id': ('hr.rfid.reader', True),
            'card_id': ('hr.rfid.card', False),
            'employee_id': ('hr.employee', False),
            'contact_id': ('res.partner', False),
            'controller_id': ('hr.rfid.ctrl', False),
            'item_sold_id': ('product.template', False),
        }

        rows = []
        src_ids = []
        for rec in source_records:
            row = []
            skip_row = False
            for col in columns:
                if col == 'event_time':
                    row.append(rec['event_time'])
                elif col in m2o_models:
                    model_name, skip_if_unmapped = m2o_models[col]
                    if rec.get(col):
                        target = self.b._map_m2o(model_name, rec[col])
                        if not target and skip_if_unmapped:
                            skip_row = True
                            break
                        row.append(target or None)
                    else:
                        row.append(None)
                else:
                    row.append(rec.get(col) if rec.get(col) is not False else None)
            if skip_row:
                skipped += 1
                continue
            rows.append(tuple(row))
            src_ids.append(rec['id'])

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported, already, rejected = self.b._direct_sql_insert_tracked(
                        table, columns, rows, model, src_ids)
            except Exception as e:
                _logger.error("Failed to insert vending events: %s", e, exc_info=True)
                self.b.rewind_cursors(cursor_key)
                self.results.append(self.b._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self.b.accumulated_result(
            cursor_key, model, len(source_records), imported, already,
            skipped, duration=time.time() - start,
            rejected_count=rejected,
        ))

    def _import_balance_history(self):
        """Step 34: hr.rfid.vending.balance.history - Direct SQL batch."""
        start = time.time()
        model = 'hr.rfid.vending.balance.history'
        table = 'hr_rfid_vending_balance_history'

        if not self.b._has_model(model):
            self.results.append(self.b._make_result(model, 0, 0, status='skipped'))
            return

        source_fields_info = self.b._get_source_fields(model)
        # Real columns only - a non-stored field in a raw INSERT is an
        # UndefinedColumn that kills the whole step.
        target_fields = self.b._target_columns(model)

        # Required fields
        fields_to_read = ['employee_id']
        # Optional - check source availability
        for f in ['balance_change', 'balance_result', 'vending_event_id',
                  'auto_refill_id', 'person_responsible', 'create_date']:
            if f in source_fields_info:
                fields_to_read.append(f)

        cursor_key = 'vending:%s' % model
        source_records = self.b._read_all(
            model, self.b._scoped_domain('employee_id'), fields_to_read,
            cursor_key, batch_size=5000)
        imported = 0
        already = 0
        rejected = 0
        skipped = 0

        # Build target columns
        columns = ['employee_id']
        for f in ['balance_change', 'balance_result', 'vending_event_id',
                  'auto_refill_id', 'person_responsible', 'create_date']:
            if f in target_fields and f in fields_to_read:
                columns.append(f)

        m2o_map = {
            'vending_event_id': 'hr.rfid.vending.event',
            'auto_refill_id': 'hr.rfid.vending.auto.refill',
        }

        rows = []
        src_ids = []
        for rec in source_records:
            emp_target = self.b._map_m2o('hr.employee', rec.get('employee_id'))
            if not emp_target:
                skipped += 1
                continue

            row = [emp_target]
            for col in columns[1:]:
                if col in m2o_map:
                    target = self.b._map_m2o(m2o_map[col], rec.get(col))
                    row.append(target or None)
                elif col == 'person_responsible':
                    # Skip user mapping - just set None
                    row.append(None)
                else:
                    val = rec.get(col)
                    row.append(val if val is not False else None)

            rows.append(tuple(row))
            src_ids.append(rec['id'])

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported, already, rejected = self.b._direct_sql_insert_tracked(
                        table, columns, rows, model, src_ids)
            except Exception as e:
                _logger.error("Failed to insert balance history: %s", e, exc_info=True)
                self.b.rewind_cursors(cursor_key)
                self.results.append(self.b._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self.b.accumulated_result(
            cursor_key, model, len(source_records), imported, already,
            skipped, duration=time.time() - start,
            rejected_count=rejected,
        ))

    def _update_employee_vending_fields(self):
        """Step 35: Update employees with vending balance fields.

        Always reports a line, even when there was nothing to set. Without one,
        "nobody over there has a vending balance" and "this step never ran"
        look exactly alike in the protocol - and the second is what happens
        when a later pass finds the map in memory empty.
        """
        start = time.time()
        co_domain = self.b._company_domain()
        label = 'hr.employee (vending fields)'

        vending_fields = EMPLOYEE_VENDING_FIELDS

        # Check which fields exist in source
        source_fields_info = self.b._get_source_fields('hr.employee')
        target_fields = set(self.env['hr.employee']._fields.keys())
        fields_to_read = ['id'] + [
            f for f in vending_fields
            if f in source_fields_info and f in target_fields
        ]

        if len(fields_to_read) <= 1:
            self.results.append(self.b._make_result(
                label, 0, 0, status='skipped',
                error=self.env._(
                    "The other system keeps no vending balances on its people, "
                    "so there was nothing to carry over."),
                duration=time.time() - start,
            ))
            return

        source_records = self.b._search_read(
            'hr.employee', co_domain, fields_to_read,
        )
        # Counted against the people who actually carry vending values, not
        # against everyone: someone with nothing to set is not a miss, while
        # someone who HAS a balance and did not get it is.
        expected = 0
        updated = 0

        for rec in source_records:
            vals = {}
            for f in fields_to_read:
                if f == 'id':
                    continue
                if rec.get(f) is not False and rec[f] is not None:
                    # Everything here is a plain value. "Gets topped up
                    # automatically" is a yes/no box on the person, not a link
                    # to a refill run - read as a link, the answer "yes" was
                    # looked up as record number True, found nothing, and the
                    # box was left unticked for 1 401 people while the
                    # protocol filled up with "Auto Refill Events No True has
                    # no match here".
                    vals[f] = rec[f]

            if not vals:
                continue
            expected += 1

            # _map_m2o, not the in-memory map alone: a later pass builds a
            # fresh importer whose map starts empty, and the record of
            # finished steps stops the people step from filling it again. Read
            # straight from the map this found nobody and left every balance
            # behind, silently.
            emp_target = self.b._map_m2o('hr.employee', rec['id'])
            if not emp_target:
                continue

            self.env['hr.employee'].browse(emp_target).with_context(
                **IMPORT_CONTEXT
            ).write(vals)
            updated += 1

        self.results.append(self.b._make_result(
            label, expected, updated, skipped_count=expected - updated,
            duration=time.time() - start,
        ))
