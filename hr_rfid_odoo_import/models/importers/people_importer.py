# -*- coding: utf-8 -*-
import logging
import time

from odoo import _
from odoo.exceptions import UserError
from .base_importer import BaseImporter, IMPORT_CONTEXT

_logger = logging.getLogger(__name__)


class PeopleImporter:
    """Phase 2: People (res.partner, res.users, hr.employee).

    Import order follows Odoo 19 auto-creation chain:
      res.partner → res.users (optional) → hr.employee
    """

    def __init__(self, base: BaseImporter):
        self.b = base
        self.env = base.env
        self.results = []

    def run(self, wizard):
        """Execute Phase 2."""
        self._import_partners()
        if self.b.options.get('import_users'):
            self._import_users()
        self._import_employees()
        return self.results

    def _import_partners(self):
        """Step 5: res.partner - scope depends on user choice."""
        start = time.time()
        model = 'res.partner'
        co_domain = self.b._company_domain()

        if self.b.options.get('import_all_partners'):
            domain = co_domain
        else:
            # Only partners with RFID cards
            card_partner_ids = self.b._search_read(
                'hr.rfid.card', co_domain,
                ['contact_id']
            )
            partner_ids = list(set(
                r['contact_id'][0] for r in card_partner_ids
                if r.get('contact_id')
            ))
            if not partner_ids:
                self.results.append(self.b._make_result(
                    model, 0, 0, duration=time.time() - start,
                ))
                return
            domain = [('id', 'in', partner_ids)]

        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())
        # Required fields
        fields_to_read = ['name', 'company_id', 'active']
        # Optional fields (company_name needed for name fallback)
        for f in ['email', 'phone', 'mobile', 'vat', 'street', 'street2',
                  'city', 'zip', 'country_id', 'company_type', 'is_company',
                  'parent_id', 'company_name', 'comment', 'type', 'tz',
                  'function', 'website', 'ref', 'lang', 'title']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)
        if self.b.options.get('import_images') and 'image_1920' in source_fields_info:
            fields_to_read.append('image_1920')

        source_records = self.b._read_all(model, domain, fields_to_read)
        imported = 0
        linked = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            target_company_id = self.b._map_company(rec.get('company_id'))

            # Try to match existing partner by email or vat (within same company)
            existing = False
            company_domain = [('company_id', '=', target_company_id)] if target_company_id else []
            if rec.get('email'):
                existing = self.env[model].with_context(active_test=False).search(
                    [('email', '=', rec['email'])] + company_domain,
                    limit=1,
                )
            # VAT matching only for company-type partners (child contacts share parent VAT)
            if not existing and rec.get('vat') and rec.get('is_company'):
                existing = self.env[model].with_context(active_test=False).search(
                    [('vat', '=', rec['vat']), ('is_company', '=', True)] + company_domain,
                    limit=1,
                )

            if existing:
                self.b._set_target_id(model, rec['id'], existing.id)
                linked += 1
                continue

            # Name fallback: name → company_name → email → 'Partner #ID'
            partner_name = (
                rec.get('name')
                or rec.get('company_name')
                or rec.get('email')
                or f"Partner #{rec['id']}"
            )
            vals = {
                'name': partner_name,
                'active': rec.get('active', True),
            }
            if rec.get('company_name') and 'company_name' in target_fields:
                vals['company_name'] = rec['company_name']
            # Simple fields
            for f in ['email', 'phone', 'mobile', 'vat', 'street', 'street2',
                       'city', 'zip', 'company_type', 'is_company',
                       'comment', 'type', 'tz', 'function', 'website',
                       'ref', 'lang']:
                if rec.get(f) and f in target_fields:
                    val = rec[f]
                    # Map deprecated selection values
                    if f == 'type' and val == 'private':
                        val = 'other'
                    vals[f] = val

            if target_company_id:
                vals['company_id'] = target_company_id

            # Country mapping by name
            if rec.get('country_id'):
                country = self.env['res.country'].search([
                    ('id', '=', rec['country_id'][0])
                ], limit=1) or self.env['res.country'].search([
                    ('name', '=', rec['country_id'][1])
                ], limit=1)
                if country:
                    vals['country_id'] = country.id

            # Image
            if rec.get('image_1920'):
                vals['image_1920'] = rec['image_1920']

            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            created = self.b._load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        # Pass 2: parent_id (each write in its own savepoint to skip cycles)
        for rec in source_records:
            if not rec.get('parent_id'):
                continue
            target_id = self.b._get_target_id(model, rec['id'])
            parent_target = self.b._map_m2o(model, rec['parent_id'])
            if target_id and parent_target:
                try:
                    with self.env.cr.savepoint():
                        self.env[model].browse(target_id).with_context(
                            **IMPORT_CONTEXT
                        ).write({'parent_id': parent_target})
                except Exception as e:
                    _logger.warning(
                        "Cannot set parent_id on partner %s → %s: %s",
                        target_id, parent_target, e,
                    )

        self.results.append(self.b._make_result(
            model, len(source_records), imported, linked,
            duration=time.time() - start,
        ))

    def _import_users(self):
        """Step 6: res.users - optional, match by login."""
        start = time.time()
        model = 'res.users'
        co_domain = self.b._company_domain()

        # Get users linked to employees in selected companies
        source_employees = self.b._search_read(
            'hr.employee', co_domain, ['user_id']
        )
        user_ids = list(set(
            e['user_id'][0] for e in source_employees
            if e.get('user_id')
        ))
        if not user_ids:
            self.results.append(self.b._make_result(
                model, 0, 0, duration=time.time() - start,
            ))
            return

        source_records = self.b._search_read(
            model,
            [('id', 'in', user_ids)],
            ['name', 'login', 'partner_id', 'groups_id', 'active', 'company_id'],
        )
        imported = 0
        linked = 0
        skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            # Match by login
            existing = self.env[model].with_context(active_test=False).search([
                ('login', '=', rec['login'])
            ], limit=1)
            if existing:
                self.b._set_target_id(model, rec['id'], existing.id)
                linked += 1
                continue

            # res.users.company_id/company_ids both default to env.company.
            # Left to the default, a tenant's staff account is created inside
            # whichever company the operator happens to be in - an internal
            # user who can read THAT company and cannot see their own.
            target_company_id = self.b._map_company(rec.get('company_id'))
            if not target_company_id:
                skipped += 1
                continue

            # Create new user
            partner_target_id = self.b._map_m2o('res.partner', rec.get('partner_id'))
            vals = {
                'name': rec['name'],
                'login': rec['login'],
                'active': rec.get('active', True),
                'password': 'ChangeMe123!',
                'company_id': target_company_id,
                'company_ids': [(6, 0, [target_company_id])],
            }
            if partner_target_id:
                vals['partner_id'] = partner_target_id

            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            try:
                created = self.b._load_records(model, data_list)
                if created:
                    self.b._set_target_id(model, rec['id'], created.id)
                    imported += 1

                    # Transfer groups by xml_id if requested
                    if self.b.options.get('import_user_groups') and rec.get('groups_id'):
                        self._transfer_groups(created, rec['groups_id'])
            except Exception as e:
                skipped += 1
                _logger.warning("Failed to create user %s: %s", rec['login'], e,
                                exc_info=True)

        self.results.append(self.b._make_result(
            model, len(source_records), imported, linked, skipped,
            duration=time.time() - start,
        ))

    def _transfer_groups(self, user, source_group_ids):
        """Transfer user groups from source by matching xml_id."""
        # Get source group xml_ids
        source_groups = self.b._search_read(
            'ir.model.data',
            [('model', '=', 'res.groups'), ('res_id', 'in', source_group_ids)],
            ['module', 'name', 'res_id'],
        )
        target_group_ids = []
        for sg in source_groups:
            xml_id = f"{sg['module']}.{sg['name']}"
            try:
                target_group = self.env.ref(xml_id, raise_if_not_found=False)
                if target_group:
                    target_group_ids.append(target_group.id)
            except Exception:
                _logger.warning(
                    "Could not resolve source group %s for user %s - the "
                    "group is not transferred", xml_id, user.login,
                    exc_info=True)

        if target_group_ids:
            user.with_context(**IMPORT_CONTEXT).write({
                'groups_id': [(4, gid) for gid in target_group_ids]
            })

    def _import_employees(self):
        """Step 7: hr.employee - scope depends on user choice."""
        start = time.time()
        model = 'hr.employee'
        co_domain = self.b._company_domain()

        if self.b.options.get('import_all_employees'):
            domain = co_domain
        else:
            # Only employees with RFID cards
            card_emp_ids = self.b._search_read(
                'hr.rfid.card', co_domain,
                ['employee_id']
            )
            emp_ids = list(set(
                r['employee_id'][0] for r in card_emp_ids
                if r.get('employee_id')
            ))
            if not emp_ids:
                self.results.append(self.b._make_result(
                    model, 0, 0, duration=time.time() - start,
                ))
                return
            domain = [('id', 'in', emp_ids)]

        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        # Required fields
        fields_to_read = ['name', 'company_id', 'active']
        # Optional fields
        for f in ['department_id', 'user_id', 'job_id', 'job_title',
                  'work_phone', 'work_email', 'barcode', 'pin',
                  'hr_rfid_pin_code', 'hr_rfid_access_group_ids',
                  'mobile_phone', 'certificate', 'birthday',
                  'emergency_contact', 'emergency_phone',
                  'gender', 'marital', 'identification_id', 'passport_id',
                  'country_of_birth', 'place_of_birth']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)
        if self.b.options.get('import_images') and 'image_1920' in source_fields_info:
            fields_to_read.append('image_1920')

        source_records = self.b._read_all(model, domain, fields_to_read)
        imported = 0
        linked = 0
        skipped = 0
        prefix = model.replace('.', '_')

        for rec in source_records:
            target_company_id = self.b._map_company(rec.get('company_id'))
            if not target_company_id:
                skipped += 1
                continue

            # Try to match by barcode (unique) or name+company (only if unique)
            existing = False
            if rec.get('barcode'):
                existing = self.env[model].with_context(active_test=False).search([
                    ('barcode', '=', rec['barcode']),
                    ('company_id', '=', target_company_id),
                ], limit=1)
            if not existing:
                name_matches = self.env[model].with_context(active_test=False).search([
                    ('name', '=', rec['name']),
                    ('company_id', '=', target_company_id),
                ])
                # Only link if exactly one match (avoid duplicate name collisions)
                if len(name_matches) == 1:
                    existing = name_matches

            if existing:
                self.b._set_target_id(model, rec['id'], existing.id)
                linked += 1
                continue

            vals = {
                'name': rec['name'],
                'company_id': target_company_id,
                'active': rec.get('active', True),
            }

            # Department
            if rec.get('department_id'):
                dept_target = self.b._map_m2o('hr.department', rec['department_id'])
                if dept_target:
                    vals['department_id'] = dept_target

            # User
            if rec.get('user_id'):
                user_target = self.b._map_m2o('res.users', rec['user_id'])
                if user_target:
                    vals['user_id'] = user_target

            # Simple fields
            for f in ['job_title', 'work_phone', 'work_email', 'barcode', 'pin',
                       'mobile_phone', 'certificate', 'birthday',
                       'emergency_contact', 'emergency_phone',
                       'gender', 'marital', 'identification_id', 'passport_id',
                       'place_of_birth']:
                if rec.get(f) and f in target_fields:
                    vals[f] = rec[f]

            # RFID pin code
            if rec.get('hr_rfid_pin_code') and 'hr_rfid_pin_code' in target_fields:
                vals['hr_rfid_pin_code'] = rec['hr_rfid_pin_code']

            # Image
            if rec.get('image_1920'):
                vals['image_1920'] = rec['image_1920']

            data_list = [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }]
            # no_hardware_commands prevents auto add_acc_gr in Employee.create()
            created = self.b._load_records(model, data_list)
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1

        self.results.append(self.b._make_result(
            model, len(source_records), imported, linked, skipped,
            duration=time.time() - start,
        ))
