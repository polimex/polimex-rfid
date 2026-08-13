# -*- coding: utf-8 -*-
"""Sites - the tree of physical locations and what hangs off it.

Three things about ``hr.rfid.site`` shape this phase, and each of them fails
silently if ignored:

* ``create`` is not batch-aware (hr_rfid_site.py:223) and reaches for
  single-record fields inside, so a batch load raises Expected singleton.
* ``make_access_group`` makes the site build an access group of its own, which
  would sit next to the one coming from the source. Deleting the duplicate
  afterwards is manual, because the module refuses to unlink a group while its
  site still wants one.
* ``write`` reacts to make_access_group / door_ids / child_ids but NOT to
  parent_id (hr_rfid_site.py:243). The usual create-then-patch-the-parent
  pattern therefore leaves the ancestors' groups without the children's doors,
  with no error at all - so the tree is built top down instead.
"""
import logging
import time

from odoo.exceptions import AccessError, UserError

from .base_importer import BaseImporter
from .phase import PhaseImporter

_logger = logging.getLogger(__name__)


class SiteImporter(PhaseImporter):
    """Phase 3c: sites, then the hardware and people that point at them."""

    PHASE_ID = 'Phase 3c'
    NAME = 'Sites'
    REQUIRES_SOURCE = ('hr_rfid_site_manager',)
    REQUIRES_TARGET = ('hr.rfid.site', ('res.partner', 'site_ids'))
    OPTION = 'import_sites'
    WEIGHT = 4

    SITE_FIELDS = ('name', 'active', 'color', 'state')

    #: Models that carry a site_id and are imported by other phases. Their
    #: site link is filled in a second pass, once the sites exist.
    SITE_LINKED_MODELS = (
        'hr.rfid.webstack', 'hr.rfid.ctrl', 'hr.rfid.door',
        'hr.rfid.access.group', 'hr.rfid.ctrl.alarm.group',
    )

    def run(self, wizard):
        self._check_operator_may_write_sites()
        self._import_sites()
        self._link_sites_to_hardware()
        self._link_sites_to_partners()
        return self.results

    # ── Pre-flight ────────────────────────────────────────────

    def _check_operator_may_write_sites(self):
        """Fail with an explanation rather than an access traceback.

        Sites are granted to one group only. Running this with sudo() would
        quietly step around that, and a data transfer is the last place that
        should decide to ignore who is allowed to do what.
        """
        try:
            self.env['hr.rfid.site'].check_access('create')
        except AccessError as exc:
            raise UserError(self.env._(
                "You are not allowed to create sites here, so the sites and "
                "everything attached to them cannot be brought across. Ask an "
                "administrator for the rights to manage sites, then run the "
                "transfer again."
            )) from exc

    # ── Sites ─────────────────────────────────────────────────

    @staticmethod
    def _parent_first(records):
        """Sites ordered so that a parent always precedes its children.

        The tree has to be built downwards: parent_id must be set at creation
        time, because a later write does not rebuild the ancestors' groups.
        """
        by_id = {r['id']: r for r in records}
        ordered, placed = [], set()

        def place(rec):
            if rec['id'] in placed:
                return
            parent = rec.get('parent_id')
            parent_id = parent[0] if isinstance(parent, (list, tuple)) else parent
            if parent_id and parent_id in by_id and parent_id not in placed:
                place(by_id[parent_id])
            placed.add(rec['id'])
            ordered.append(rec)

        for rec in records:
            place(rec)
        return ordered

    def _import_sites(self):
        start = time.time()
        model = 'hr.rfid.site'
        source_fields = self.b._get_source_fields(model)
        target_fields = self.b._target_columns(model)
        wanted = [f for f in self.SITE_FIELDS
                  if f in source_fields and f in target_fields]

        source_records = self.b._read_all(
            model, self.b._company_domain(),
            ['company_id', 'parent_id', 'make_access_group'] + wanted,
        )

        imported = linked = skipped = 0
        wants_own_group = {}
        prefix = model.replace('.', '_')
        for rec in self._parent_first(source_records):
            target_company_id = self.b._map_company(rec.get('company_id'))
            if not target_company_id:
                skipped += 1
                continue
            existing = self.b.find_by_ledger(model, rec['id'], rec.get('name'))
            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
                linked += 1
                continue

            vals = {f: rec.get(f) for f in wanted if rec.get(f) not in (None, False)}
            vals['company_id'] = target_company_id
            if 'active' in wanted:
                vals['active'] = bool(rec.get('active'))
            vals['parent_id'] = self.b._map_m2o('hr.rfid.site', rec.get('parent_id'))
            # Always False at creation: with it on, the site builds an access
            # group of its own, which then sits beside the one arriving from
            # the source. The real value is restored once the source groups
            # know which site they belong to.
            vals['make_access_group'] = False

            # One record at a time - create() is not batch-aware here.
            created = self.b._load_records(model, [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': vals,
                'noupdate': True,
            }])
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1
                if rec.get('make_access_group'):
                    wants_own_group[rec['id']] = created.id
            else:
                skipped += 1

        self._pending_own_group = wants_own_group
        self.results.append(self.b._make_result(
            model, len(source_records), imported, linked, skipped,
            duration=time.time() - start,
        ))

    # ── Second passes ─────────────────────────────────────────

    def _link_sites_to_hardware(self):
        """Fill site_id on the equipment that was imported before the sites."""
        start = time.time()
        total = updated = 0
        for model in self.SITE_LINKED_MODELS:
            if model not in self.env or 'site_id' not in self.env[model]._fields:
                continue
            if not self.b._has_field(model, 'site_id'):
                continue
            records = self.b._read_all(
                model, [('site_id', '!=', False)], ['site_id'])
            total += len(records)
            for rec in records:
                target_id = self.b._get_target_id(model, rec['id'])
                site_id = self.b._map_m2o('hr.rfid.site', rec.get('site_id'))
                if not target_id or not site_id:
                    continue
                self.env[model].browse(target_id).write({'site_id': site_id})
                updated += 1

        self.results.append(self.b._make_result(
            'hr.rfid.site (equipment)', total, updated,
            skipped=total - updated, duration=time.time() - start,
        ))

    def _link_sites_to_partners(self):
        """Give the contacts back the sites they belong to."""
        start = time.time()
        model = 'res.partner'
        if not self.b._has_field(model, 'site_ids'):
            self.results.append(self.b._make_result(
                'res.partner (sites)', 0, 0, status='skipped'))
            return

        records = self.b._read_all(model, [('site_ids', '!=', False)], ['site_ids'])
        updated = 0
        for rec in records:
            target_id = self.b._get_target_id(model, rec['id'])
            if not target_id:
                continue
            site_ids = self.b._map_m2m('hr.rfid.site', rec.get('site_ids') or [])
            if not site_ids[0][2]:
                continue
            self.env[model].browse(target_id).write({'site_ids': site_ids})
            updated += 1

        self.results.append(self.b._make_result(
            'res.partner (sites)', len(records), updated,
            skipped=len(records) - updated, duration=time.time() - start,
        ))


class SiteGroupImporter(PhaseImporter):
    """Phase 4b: give sites back their own access group, after the real ones.

    Kept apart from the sites themselves on purpose. The site builds its group
    the moment the flag is set, so setting it before the source's groups have
    arrived and claimed their site produces a duplicate that cannot be deleted
    while the flag stays on.
    """

    PHASE_ID = 'Phase 4b'
    NAME = 'Site Groups'
    REQUIRES_SOURCE = ('hr_rfid_site_manager',)
    REQUIRES_TARGET = ('hr.rfid.site',)
    OPTION = 'import_sites'
    WEIGHT = 1

    def run(self, wizard):
        start = time.time()
        model = 'hr.rfid.site'
        source_records = self.b._read_all(
            model, self.b._company_domain(), ['make_access_group'])
        wanted = [r for r in source_records if r.get('make_access_group')]

        restored = skipped = 0
        for rec in wanted:
            target_id = self.b._get_target_id(model, rec['id'])
            if not target_id:
                skipped += 1
                continue
            site = self.env[model].browse(target_id)
            if site.access_group_ids:
                # The source's own group already claimed this site - turning
                # the flag on now would add a second one beside it.
                skipped += 1
                continue
            site.write({'make_access_group': True})
            restored += 1

        self.results.append(self.b._make_result(
            'hr.rfid.site (own group)', len(wanted), restored,
            skipped=skipped, duration=time.time() - start,
        ))
        return self.results
