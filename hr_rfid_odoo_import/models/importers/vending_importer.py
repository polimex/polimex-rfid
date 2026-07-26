# -*- coding: utf-8 -*-
import logging
import time

from odoo import _
from odoo.exceptions import UserError
from .base_importer import BaseImporter, IMPORT_CONTEXT

_logger = logging.getLogger(__name__)


class VendingImporter:
    """Phase 6a: Vending data.

    Steps: product.template, vending.row, vending.settings,
           auto.refill, vending.event, balance.history,
           employee vending fields.
    """

    def __init__(self, base: BaseImporter):
        self.b = base
        self.env = base.env
        self.results = []

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

        # Get products used in vending rows
        vending_rows = self.b._search_read(
            'hr.rfid.ctrl.vending.row', [],
            ['product_id'],
        )
        product_ids = list(set(
            r['product_id'][0] for r in vending_rows
            if r.get('product_id')
        ))
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
            # Идентичност САМО по source id (ledger). Текстът е втора
            # проверка на вече намерения запис, не ключ за търсене.
            existing = self.b.find_by_ledger(model, rec['id'], rec.get('name'))

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

        fields_to_read = ['name', 'company_id']
        for f in ['amount', 'period']:
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
            if 'amount' in rec and rec.get('amount') is not None and 'amount' in target_fields:
                vals['amount'] = rec.get('amount', 0.0)
            if rec.get('period') and 'period' in target_fields:
                vals['period'] = rec['period']
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
        source_records = self.b._read_all(
            # Scope on reader_id, NOT door_id: the source leaves door_id NULL on
            # every vending event (32046/32046), and a dotted domain compiles to
            # EXISTS - a NULL link never matches, so scoping there would drop the
            # whole vending history while reporting "this client has none".
            # reader_id is required=True on the model and NOT NULL in the target.
            model, self.b._scoped_domain('reader_id.controller_id.webstack_id') + domain,
            fields_to_read, batch_size=2000,
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
                self.results.append(self.b._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self.b._make_result(
            model, len(source_records), imported, already, skipped,
            duration=time.time() - start, rejected_count=rejected,
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

        source_records = self.b._read_all(
            model, self.b._scoped_domain('employee_id'), fields_to_read,
            batch_size=5000)
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
                self.results.append(self.b._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self.b._make_result(
            model, len(source_records), imported, already, skipped,
            duration=time.time() - start, rejected_count=rejected,
        ))

    def _update_employee_vending_fields(self):
        """Step 35: Update employees with vending balance fields."""
        start = time.time()
        co_domain = self.b._company_domain()

        vending_fields = [
            'hr_rfid_vending_in_attendance', 'hr_rfid_vending_limit',
            'hr_rfid_vending_balance', 'hr_rfid_vending_auto_refill',
            'hr_rfid_vending_auto_refill_amount', 'hr_rfid_vending_refill_amount',
            'hr_rfid_vending_auto_refill_action', 'hr_rfid_vending_limit_type',
            'hr_rfid_vending_limit_amount', 'hr_rfid_vending_limit_period',
            'hr_rfid_vending_pin', 'hr_rfid_vending_negbal',
        ]

        # Check which fields exist in source
        source_fields_info = self.b._get_source_fields('hr.employee')
        target_fields = set(self.env['hr.employee']._fields.keys())
        fields_to_read = ['id'] + [
            f for f in vending_fields
            if f in source_fields_info and f in target_fields
        ]

        if len(fields_to_read) <= 1:
            return  # No vending fields to import

        source_records = self.b._search_read(
            'hr.employee', co_domain, fields_to_read,
        )
        updated = 0

        for rec in source_records:
            emp_target = self.b._get_target_id('hr.employee', rec['id'])
            if not emp_target:
                continue

            vals = {}
            for f in fields_to_read:
                if f == 'id':
                    continue
                if rec.get(f) is not False and rec[f] is not None:
                    # Handle M2O auto_refill
                    if f == 'hr_rfid_vending_auto_refill' and rec[f]:
                        ar_target = self.b._map_m2o(
                            'hr.rfid.vending.auto.refill', rec[f]
                        )
                        if ar_target:
                            vals[f] = ar_target
                    else:
                        vals[f] = rec[f]

            if vals:
                self.env['hr.employee'].browse(emp_target).with_context(
                    **IMPORT_CONTEXT
                ).write(vals)
                updated += 1

        if updated:
            self.results.append(self.b._make_result(
                'hr.employee (vending fields)', len(source_records), updated,
                duration=time.time() - start,
            ))
