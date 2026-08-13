# -*- coding: utf-8 -*-
import logging
import time

from odoo import _
from odoo.exceptions import UserError
from .base_importer import BaseImporter, IMPORT_CONTEXT
from .phase import PhaseImporter

_logger = logging.getLogger(__name__)


class PeopleImporter(PhaseImporter):
    """Phase 2: People (res.partner, res.users, hr.employee).

    Import order follows Odoo 19 auto-creation chain:
      res.partner → res.users (optional) → hr.employee
    """

    PHASE_ID = 'Phase 2'
    NAME = 'People'
    REQUIRES_SOURCE = ('hr_rfid',)
    REQUIRES_TARGET = ('hr.employee', 'res.partner')
    OPTION = 'import_people'
    WEIGHT = 15

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

            # Идентичност САМО по source id (ledger). Текстът е втора
            # проверка на вече намерения запис, не ключ за търсене.
            existing = self.b.find_by_ledger(model, rec['id'], rec.get('name'))

            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
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

            # Държавата е справочник на самата платформа - съпоставя се по
            # СТАБИЛЕН ISO код през external ID-то на base (`base.bg`), не по
            # преводимо име и не по сурово id (id-тата на res.country не са
            # гарантирано еднакви между инсталации).
            if rec.get('country_id'):
                country = self._resolve_country(rec['country_id'])
                if country:
                    vals['country_id'] = country

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

    def _resolve_country(self, source_country):
        """ID на държавата в целта, по ISO код от external ID-то на източника.

        `res.country` е справочник на Odoo, не мигриран обект: и двете страни го
        носят с един и същ external ID (`base.bg`), който кодира ISO кода.
        Сравняване по `name` е превод-зависимо, а по сурово `id` - зависи от
        реда на инсталация.
        """
        source_id = source_country[0] if isinstance(source_country, (list, tuple)) else source_country
        if not hasattr(self, '_country_cache'):
            self._country_cache = {}
        if source_id in self._country_cache:
            return self._country_cache[source_id]
        result = False
        imd = self.b._search_read(
            'ir.model.data',
            [('model', '=', 'res.country'), ('res_id', '=', source_id)],
            ['module', 'name'],
        )
        if imd:
            rec = self.env.ref('%s.%s' % (imd[0]['module'], imd[0]['name']),
                               raise_if_not_found=False)
            if rec:
                result = rec.id
        if not result:
            _logger.warning("Държава %s от източника не се резолва по external ID "
                            "- оставя се празна", source_country)
        self._country_cache[source_id] = result
        return result

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
            # Идентичност САМО по source id (ledger). Текстът е втора
            # проверка на вече намерения запис, не ключ за търсене.
            existing = self.b.find_by_ledger(model, rec['id'], rec.get('login'), 'login')
            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
                linked += 1
                continue

            # Няма ледгер => НОВ потребител. Ако login-ът вече е зает в целта,
            # това е КОНФЛИКТ за докладване, не покана за сливане: login-ът е
            # credential, не идентичност. Най-честият случай е системният
            # потребител на източника (admin), закачен за служител - целта си
            # има свой и не бива да бъде пренаписан.
            clash = self.env[model].sudo().with_context(active_test=False).search(
                [('login', '=', rec['login'])], limit=1)
            if clash:
                skipped += 1
                _logger.warning(
                    "Потребител %s от източника не е внесен: login-ът вече е зает "
                    "от %s в целта, а ледгерът не сочи към него - изисква решение "
                    "на оператора, не автоматично сливане", rec['login'], clash.id)
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
                # v19 преименува res.users.groups_id -> group_ids. Източникът
                # (о15) още го чете като groups_id - преименуването е само от
                # страната на записа.
                'group_ids': [(4, gid) for gid in target_group_ids]
            })

    def _import_employees(self):
        """Step 7: hr.employee - scope depends on user choice."""
        start = time.time()
        model = 'hr.employee'
        co_domain = self.b._company_domain()
        # Потребителите, които вече са заети от служител В ЦЕЛТА (заварени +
        # създадени в този прогон). v19 налага един служител на потребител.
        claimed_users = set(self.env['hr.employee'].sudo().with_context(
            active_test=False).search([('user_id', '!=', False)]).mapped('user_id').ids)

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

            # Идентичност САМО по source id. Съпоставянето по име сля
            # съименници: от 1059 души на един клиент в целта влязоха 1022
            # (точно броят различни имена), заедно с картите и събитията им.
            existing = self.b.find_by_ledger(model, rec['id'], rec.get('name'))

            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
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

            # User. v19 налага UNIQUE(user_id) на hr.employee, а източникът
            # НЕ го налага - admin (uid 2) виси на служители в две различни
            # фирми. Взимаме връзката само ако потребителят е свободен; иначе
            # служителят се внася без нея, вместо цялата фаза да падне.
            if rec.get('user_id'):
                user_target = self.b._map_m2o('res.users', rec['user_id'])
                if user_target and user_target not in claimed_users:
                    vals['user_id'] = user_target
                    claimed_users.add(user_target)
                elif user_target:
                    _logger.info(
                        "Служител %s не е свързан с потребител %s - вече е зает "
                        "от друг служител (v19 позволява един)",
                        rec.get('name'), user_target)

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
