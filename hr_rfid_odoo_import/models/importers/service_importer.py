# -*- coding: utf-8 -*-
import logging
import time

from odoo import _
from odoo.exceptions import UserError
from .base_importer import BaseImporter, IMPORT_CONTEXT

_logger = logging.getLogger(__name__)


class ServiceImporter:
    """Phase 6c: Service data.

    Steps: rfid.service.tags, rfid.service, rfid.service.sale
    """

    def __init__(self, base: BaseImporter):
        self.b = base
        self.env = base.env
        self.results = []

    def run(self, wizard):
        """Execute Phase 6c."""
        self._import_service_tags()
        self._import_services()
        self._import_service_sales()
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

    def _import_service_tags(self):
        """Step 38: rfid.service.tags — ORM create."""
        start = time.time()
        model = 'rfid.service.tags'
        if not self.b._has_model(model):
            return
        source_records = self.b._search_read(model, [], ['name', 'color'])
        imported = 0
        linked = 0
        prefix = model.replace('.', '_')

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

    def _import_services(self):
        """Step 39: rfid.service — depends on AG, zone, partner, card_type, tags."""
        start = time.time()
        model = 'rfid.service'
        if not self.b._has_model(model):
            return

        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        fields_to_read = ['name', 'tag_ids', 'access_group_id', 'zone_id',
                          'card_type', 'company_id']
        for f in ['mail_template_id', 'print_template_id', 'active',
                   'duration', 'max_visits', 'description']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)

        co_domain = self.b._company_domain()
        source_records = self.b._search_read(model, co_domain, fields_to_read)
        imported = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            target_company_id = self.b._map_company(rec.get('company_id'))
            if not target_company_id:
                continue

            vals = {
                'name': rec['name'],
                'company_id': target_company_id,
            }

            # M2M tags
            if rec.get('tag_ids'):
                vals['tag_ids'] = self.b._map_m2m('rfid.service.tags', rec['tag_ids'])

            # M2O fields
            if rec.get('access_group_id'):
                ag_target = self.b._map_m2o(
                    'hr.rfid.access.group', rec['access_group_id']
                )
                if ag_target:
                    vals['access_group_id'] = ag_target
                else:
                    _logger.warning(
                        "Skipping service %s: access_group_id %s not found in target",
                        rec['name'], rec['access_group_id'],
                    )
                    continue
            if rec.get('zone_id'):
                zone_target = self.b._map_m2o('hr.rfid.zone', rec['zone_id'])
                if zone_target:
                    vals['zone_id'] = zone_target
            if rec.get('card_type'):
                ct_target = self.b._map_m2o('hr.rfid.card.type', rec['card_type'])
                if ct_target:
                    vals['card_type'] = ct_target

            # mail_template_id / print_template_id — match by xml_id
            for template_field in ['mail_template_id', 'print_template_id']:
                if rec.get(template_field):
                    template_target = self._resolve_template_by_xmlid(
                        rec[template_field],
                        'mail.template' if 'mail' in template_field else 'ir.actions.report',
                    )
                    if template_target:
                        vals[template_field] = template_target

            # Simple fields
            for f in ['active', 'duration', 'max_visits', 'description']:
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
            model, len(source_records), imported,
            duration=time.time() - start,
        ))

    def _resolve_template_by_xmlid(self, source_val, model):
        """Resolve template M2O by xml_id from source ir.model.data."""
        if not source_val:
            return False
        source_id = source_val[0] if isinstance(source_val, (list, tuple)) else source_val
        try:
            imd_records = self.b._search_read(
                'ir.model.data',
                [('model', '=', model), ('res_id', '=', source_id)],
                ['module', 'name'],
            )
            if imd_records:
                xml_id = f"{imd_records[0]['module']}.{imd_records[0]['name']}"
                target_rec = self.env.ref(xml_id, raise_if_not_found=False)
                if target_rec:
                    return target_rec.id
        except Exception:
            pass
        _logger.warning(
            "Could not resolve %s template ID %s by xml_id. Setting to False.",
            model, source_val,
        )
        return False

    def _import_service_sales(self):
        """Step 40: rfid.service.sale — Direct SQL batch."""
        start = time.time()
        model = 'rfid.service.sale'
        table = 'rfid_service_sale'

        if not self.b._has_model(model):
            return

        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        fields_to_read = ['service_id', 'partner_id', 'card_id', 'create_date']
        for f in ['state', 'start_date', 'end_date', 'visits_count',
                   'access_group_contact_rel_id']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)

        source_records = self.b._read_all(model, [], fields_to_read, batch_size=2000)
        imported = 0

        columns = ['service_id', 'partner_id', 'card_id', 'create_date']
        for f in ['state', 'start_date', 'end_date', 'visits_count',
                   'access_group_contact_rel_id']:
            if f in fields_to_read:
                columns.append(f)

        rows = []
        for rec in source_records:
            service_target = self.b._map_m2o('rfid.service', rec.get('service_id'))
            if not service_target:
                continue
            partner_target = self.b._map_m2o('res.partner', rec.get('partner_id'))
            card_target = self.b._map_m2o('hr.rfid.card', rec.get('card_id'))

            row = [
                service_target,
                partner_target or None,
                card_target or None,
                rec.get('create_date'),
            ]
            for f in columns[4:]:
                if f == 'access_group_contact_rel_id':
                    rel_target = self.b._map_m2o(
                        'hr.rfid.access.group.contact.rel', rec.get(f)
                    )
                    row.append(rel_target or None)
                else:
                    row.append(rec.get(f) if rec.get(f) is not False else None)

            rows.append(tuple(row))

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported = self.b._direct_sql_insert(table, columns, rows)
            except Exception as e:
                _logger.error("Failed to insert service events: %s", e)
                self.results.append(self._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self._make_result(
            model, len(source_records), imported,
            duration=time.time() - start,
        ))
