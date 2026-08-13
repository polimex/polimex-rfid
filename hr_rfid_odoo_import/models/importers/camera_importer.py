# -*- coding: utf-8 -*-
"""Cameras, their readers and doors, and the plates they hold.

The camera side of the topology hangs off the camera, not off a controller:
its readers have no ``controller_id`` and its doors have no webstack. Every
scope in the core phases walks the controller chain, so none of it is visible
to them - the cameras, their readers, their doors and their plate lists all
have to be brought across here.
"""
import logging
import time

from odoo.exceptions import UserError

from .base_importer import BaseImporter
from .phase import PhaseImporter

_logger = logging.getLogger(__name__)

#: Only two buckets exist on the hardware. Older installations carried extra
#: values ('graylist', 'yellolist', 'otherlist'); the module itself resolves
#: them the safe way (migrations/19.0.1.5.0/post-migration.py), and so do we.
#: Mapping an unknown bucket to 'whitelist' would OPEN access that used to be
#: refused - the one mistake here that lets a vehicle through a barrier.
SAFE_LIST_CATEGORY = 'blacklist'
KNOWN_LIST_CATEGORIES = ('whitelist', 'blacklist')


class CameraImporter(PhaseImporter):
    """Phase 7: ANPR cameras, their topology and their plate lists."""

    PHASE_ID = 'Phase 7'
    NAME = 'Cameras'
    REQUIRES_SOURCE = ('polimex_ip_cam',)
    REQUIRES_TARGET = ('cctv.camera', 'cctv.camera.rfid.rel',
                       ('hr.rfid.reader', 'camera_id'))
    OPTION = 'import_cameras'
    WEIGHT = 5

    #: Settings that describe the camera itself.
    CONFIG_FIELDS = (
        'name', 'active', 'tz', 'behind_nat', 'ip_address', 'port',
        'username', 'password', 'brand', 'description', 'server_setup',
        'entrance_setup', 'integration_type',
    )
    #: How the camera is recognised. These look like metadata but are not:
    #: incoming plate events are matched to a camera by sub_serial_number,
    #: falling back to serial_number. Leave them behind and every camera
    #: stops accepting events after the move.
    IDENTITY_FIELDS = ('model', 'serial_number', 'sub_serial_number', 'firmware')

    def run(self, wizard):
        self._check_credentials_are_readable()
        self._import_cameras()
        self._import_camera_readers()
        self._import_camera_doors()
        self._import_plate_links()
        return self.results

    # ── Pre-flight ────────────────────────────────────────────

    def _check_credentials_are_readable(self):
        """Stop early if the other system will not hand over the passwords.

        The password field is restricted to camera managers on both sides. A
        user without that right reads it as empty, and the transfer would
        quietly produce cameras nobody can connect to - discovered only when
        someone opens one and presses Check Connection, long after the move.
        """
        cameras = self.b._search_read(
            'cctv.camera', self.b._company_domain(), ['name', 'password'],
            limit=5,
        )
        if not cameras:
            return
        if all(not c.get('password') for c in cameras):
            raise UserError(self.env._(
                "The cameras came across without their access details. The "
                "account used to read the other system is not allowed to see "
                "them. Give that account camera-manager rights there and run "
                "the transfer again."
            ))

    # ── Cameras ───────────────────────────────────────────────

    def _import_cameras(self):
        start = time.time()
        model = 'cctv.camera'
        source_fields = self.b._get_source_fields(model)
        target_fields = self.b._target_columns(model)

        wanted = [f for f in self.CONFIG_FIELDS + self.IDENTITY_FIELDS
                  if f in source_fields and f in target_fields]
        fields_to_read = ['company_id'] + wanted
        source_records = self.b._read_all(
            model, self.b._company_domain(), fields_to_read)

        imported = linked = skipped = 0
        prefix = model.replace('.', '_')
        for rec in source_records:
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
            # 'active' is meaningful even when False - an archived camera must
            # stay archived, and the loop above drops falsy values.
            if 'active' in wanted:
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

    # ── Readers and doors that hang off a camera ──────────────

    def _import_camera_readers(self):
        """Readers bound to a camera rather than to a controller.

        The core hardware phase scopes readers by controller_id.webstack_id and
        skips whatever it cannot map, so these never arrive through it.
        """
        start = time.time()
        model = 'hr.rfid.reader'
        source_fields = self.b._get_source_fields(model)
        target_fields = self.b._target_columns(model)
        if 'camera_id' not in source_fields:
            self.results.append(self.b._make_result(model, 0, 0, status='skipped'))
            return

        wanted = [f for f in ('name', 'number', 'reader_type', 'mode', 'active')
                  if f in source_fields and f in target_fields]
        source_records = self.b._read_all(
            model,
            [('camera_id', '!=', False)] + self.b._scoped_domain('camera_id'),
            ['camera_id'] + wanted,
        )

        imported = linked = skipped = 0
        prefix = model.replace('.', '_')
        for rec in source_records:
            camera_id = self.b._map_m2o('cctv.camera', rec.get('camera_id'))
            if not camera_id:
                skipped += 1
                continue
            existing = self.b.find_by_ledger(model, rec['id'], rec.get('name'))
            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
                linked += 1
                continue
            vals = {f: rec.get(f) for f in wanted if rec.get(f) not in (None, False)}
            vals['camera_id'] = camera_id
            if 'active' in wanted:
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

    def _import_camera_doors(self):
        """Doors whose readers belong to a camera."""
        start = time.time()
        model = 'hr.rfid.door'
        source_fields = self.b._get_source_fields(model)
        target_fields = self.b._target_columns(model)
        if 'camera_id' not in source_fields:
            self.results.append(self.b._make_result(model, 0, 0, status='skipped'))
            return

        wanted = [f for f in ('name', 'number', 'card_type', 'active')
                  if f in source_fields and f in target_fields]
        source_records = self.b._read_all(
            model,
            [('camera_id', '!=', False)] + self.b._scoped_domain('camera_id'),
            ['camera_id', 'reader_ids'] + wanted,
        )

        imported = linked = skipped = 0
        prefix = model.replace('.', '_')
        for rec in source_records:
            if not self.b._map_m2o('cctv.camera', rec.get('camera_id')):
                skipped += 1
                continue
            existing = self.b.find_by_ledger(model, rec['id'], rec.get('name'))
            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
                linked += 1
                continue
            vals = {f: rec.get(f) for f in wanted if rec.get(f) not in (None, False)}
            if 'card_type' in wanted and rec.get('card_type'):
                vals['card_type'] = self.b._map_m2o(
                    'hr.rfid.card.type', rec['card_type']) or False
                if not vals['card_type']:
                    vals.pop('card_type')
            if 'active' in wanted:
                vals['active'] = bool(rec.get('active'))
            vals['reader_ids'] = self.b._map_m2m(
                'hr.rfid.reader', rec.get('reader_ids') or [])
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

    # ── Plate lists ───────────────────────────────────────────

    def _import_plate_links(self):
        """Which plate sits in which bucket on which camera."""
        start = time.time()
        model = 'cctv.camera.rfid.rel'
        source_records = self.b._read_all(
            model, self.b._scoped_domain('camera_id'),
            ['camera_id', 'card_id', 'list_category'],
        )

        imported = linked = skipped = 0
        coerced = 0
        prefix = model.replace('.', '_')
        for rec in source_records:
            camera_id = self.b._map_m2o('cctv.camera', rec.get('camera_id'))
            card_id = self.b._map_m2o('hr.rfid.card', rec.get('card_id'))
            if not camera_id or not card_id:
                skipped += 1
                continue
            existing = self.b.find_by_ledger(model, rec['id'])
            if existing:
                self.b.link_existing(model, rec['id'], existing.id)
                linked += 1
                continue
            category = rec.get('list_category')
            if category not in KNOWN_LIST_CATEGORIES:
                category = SAFE_LIST_CATEGORY
                coerced += 1
            created = self.b._load_records(model, [{
                'xml_id': self.b._xml_id(prefix, rec['id']),
                'values': {
                    'camera_id': camera_id,
                    'card_id': card_id,
                    'list_category': category,
                },
                'noupdate': True,
            }])
            if created:
                self.b._set_target_id(model, rec['id'], created.id)
                imported += 1
            else:
                skipped += 1

        note = ''
        if coerced:
            # Reported, not just logged: the operator needs to know some plates
            # were moved to the deny bucket, because the alternative reading
            # would have granted them access.
            note = self.env._(
                "%(count)s plate(s) came from an unrecognised list and were "
                "placed in the deny list.", count=coerced,
            )
            _logger.warning("%s: %d plates coerced to %s",
                            model, coerced, SAFE_LIST_CATEGORY)

        self.results.append(self.b._make_result(
            model, len(source_records), imported, linked, skipped,
            duration=time.time() - start, error=note,
        ))
