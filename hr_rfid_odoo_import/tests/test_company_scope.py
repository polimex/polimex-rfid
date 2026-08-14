# -*- coding: utf-8 -*-
"""Regression tests for per-company scoping and honest skip accounting.

Every case here corresponds to a defect found on a real pilot run of the
Odoo 15 cloud migration, where importing ONE tenant wrote other tenants'
data into the operator's company - or dropped data while reporting success:

* zones were read globally and created without ``company_id``, so the target
  default (``env.company``) claimed all of them;
* system events were scoped through ``controller_id``, which is NULL on the
  majority of them, and ``webstack_id`` - the only company link - was never
  written;
* several steps probed field names that exist in neither version
  (``alarm_right``, ``access_group_contact_rel_id``, ``i_mask`` as ``mask``),
  so the value was silently dropped;
* rows dropped by a ``continue`` were not counted, making "this client has no
  such data" indistinguishable from "every row was thrown away".
"""

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.base_importer import BaseImporter
from ..models.importers.core_importer import CoreImporter, ZoneImporter
from ..models.importers.event_importer import EventImporter
from ..models.importers.attendance_importer import AttendanceImporter
from ..models.importers.service_importer import ServiceImporter
from ..models.importers.vending_importer import VendingImporter

SRC_DB = "scope_src"


class _FakeSource(BaseImporter):
    """BaseImporter with the XML-RPC side replaced by in-memory fixtures.

    The target side stays real, so writes hit the actual v19 constraints.
    ``domains`` records what each step asked the source for, which is how the
    scoping contract is asserted: the defect was a literal empty domain.
    """

    def __init__(self, env, company_map, options, data):
        self.env = env
        self.source_db = SRC_DB
        # Двойникът не минава през `super().__init__` - идентичността на
        # източника трябва да се зададе изрично, иначе `_xml_id` гърми.
        self.source_slug = SRC_DB
        self.source_url = "http://localhost:1"
        self.source_uid = 1
        self.source_password = "x"
        self.company_map = company_map
        self.id_map = {}
        self.options = options
        self._field_cache = {}
        self._readable_cache = {}
        self.read_cursors = {}
        self._data = data
        self.domains = {}
        self.bulk_calls = []
        self.orm_calls = []

    # -- source stubs --------------------------------------------------
    def _has_model(self, model):
        return model in self._data

    def _get_source_fields(self, model):
        keys = set()
        for rec in self._data.get(model, []):
            keys |= set(rec)
        return {k: {} for k in keys}

    def _has_field(self, model, field_name):
        return field_name in self._get_source_fields(model)

    def _search_read(self, model, domain, fields, order='id asc', limit=0,
                     include_archived=True):
        self.domains[model] = domain
        return [dict(rec) for rec in self._data.get(model, [])]

    def _read_all(self, model, domain, fields, batch_size=1000, cursor_key=None):
        return self._search_read(model, domain, fields)

    # -- capture the bulk contract without touching the DB -------------
    def _direct_sql_insert_tracked(self, table, columns, rows, model,
                                   source_ids, batch_size=5000):
        self.bulk_calls.append({
            'table': table, 'columns': list(columns),
            'rows': list(rows), 'model': model, 'source_ids': list(source_ids),
        })
        return len(rows), 0, 0

    def _load_records(self, model_name, data_list):
        self.orm_calls.append((model_name, [dict(d['values']) for d in data_list]))
        return super()._load_records(model_name, data_list)

    def _try_load_records(self, model_name, data_list):
        self.orm_calls.append((model_name, [dict(d['values']) for d in data_list]))
        return super()._try_load_records(model_name, data_list)

    def vals_for(self, model):
        """Every values dict this run tried to write for `model`."""
        return [v for name, vals in self.orm_calls if name == model for v in vals]

    # -- helpers for assertions ----------------------------------------
    def domain_mentions_company(self, model):
        """True when the source read for `model` was restricted by company."""
        return any(
            isinstance(leaf, (list, tuple)) and str(leaf[0]).endswith('company_id')
            for leaf in self.domains.get(model, [])
        )

    def last_bulk(self, model):
        for call in reversed(self.bulk_calls):
            if call['model'] == model:
                return call
        return None


@tagged("post_install", "-at_install", "rfid_odoo_import", "rfid_import_scope")
class TestCompanyScope(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mine = cls.env['res.company'].create({'name': 'Scope Tenant A'})
        cls.other = cls.env['res.company'].create({'name': 'Scope Tenant B'})
        # Source company 101 is in scope, 202 is another tenant entirely.
        cls.company_map = {101: cls.mine.id}
        cls.webstack = cls.env['hr.rfid.webstack'].create({
            'name': 'Scope Stack', 'serial': '987654', 'key': '0000',
            'company_id': cls.mine.id, 'available': 'a',
            'tz': 'Europe/Sofia', 'active': True,
        })
        cls.ctrl = cls.env['hr.rfid.ctrl'].create({
            'name': 'Scope Controller', 'ctrl_id': 91,
            'webstack_id': cls.webstack.id,
        })
        # v19 refuses a notification it cannot deliver (check_recipients), so
        # a recipient that survives the mapping is part of the fixture.
        cls.recipient = cls.env['res.partner'].create({
            'name': 'Alerts Recipient', 'email': 'alerts@example.com',
            'company_id': cls.mine.id,
        })

    def _importer(self, data, **options):
        opts = {'import_hardware': True}
        opts.update(options)
        return _FakeSource(self.env, dict(self.company_map), opts, data)

    # ---------------------------------------------------------------- zones
    def test_zone_import_is_company_scoped_and_stamped(self):
        """The reproduced leak: a tenant owning no zones got everyone else's.

        On the pilot, importing a client with zero zones created all nine
        zones of the other clients inside company 1.
        """
        base = self._importer({'hr.rfid.zone': [
            {'id': 1, 'name': 'Zone of tenant A', 'company_id': [101, 'A']},
            {'id': 2, 'name': 'Zone of tenant B', 'company_id': [202, 'B']},
        ]})
        results = ZoneImporter(base).run(None)

        self.assertTrue(
            base.domain_mentions_company('hr.rfid.zone'),
            "zones must be read per company; a global read is what let one "
            "tenant's zones be created inside another's company",
        )
        zone_result = next(r for r in results if r['model'] == 'hr.rfid.zone')
        self.assertEqual(zone_result['imported_count'], 1)
        self.assertEqual(
            zone_result['skipped_count'], 1,
            "the out-of-scope zone must be counted, not dropped in silence",
        )

        created = self.env['hr.rfid.zone'].browse(
            base._get_target_id('hr.rfid.zone', 1))
        self.assertEqual(
            created.company_id, self.mine,
            "the zone must carry the mapped company; leaving it to the target "
            "default (env.company) is exactly how the leak happened",
        )
        self.assertFalse(
            base._get_target_id('hr.rfid.zone', 2),
            "a zone of a company that is not being imported must not be created",
        )

    # -------------------------------------------------------- notifications
    def test_notification_uses_the_fields_that_exist(self):
        """`user_event`/`system_event`, not the `*_ids` names that never matched.

        The old code also wrote `name` (computed, no column) and created
        without a savepoint, so a single bad row rolled back the whole phase.
        """
        base = self._importer({
            'hr.rfid.zone': [
                {'id': 1, 'name': 'Zone with alerts', 'company_id': [101, 'A']},
            ],
            'hr.rfid.notification': [
                {'id': 7, 'zone_id': [1, 'Zone with alerts'],
                 'notification_type': 'email', 'system_event': '30',
                 'user_event': False, 'notify_followers': False,
                 'notify_partner_ids': [55]},
                # Names no event at all -> the target check constraint refuses
                # it. It must be skipped, NOT take the phase down with it.
                {'id': 8, 'zone_id': [1, 'Zone with alerts'],
                 'notification_type': 'email', 'system_event': False,
                 'user_event': False, 'notify_followers': False},
            ],
        })
        base._set_target_id('res.partner', 55, self.recipient.id)
        results = ZoneImporter(base).run(None)

        notif_result = next(
            r for r in results if r['model'] == 'hr.rfid.notification')
        self.assertEqual(notif_result['imported_count'], 1)
        self.assertEqual(notif_result['skipped_count'], 1)

        created = self.env['hr.rfid.notification'].browse(
            base._get_target_id('hr.rfid.notification', 7))
        self.assertEqual(created.system_event, '30')
        self.assertEqual(created.notification_type, 'email')
        self.assertEqual(created.notify_partner_ids, self.recipient)
        self.assertEqual(
            created.zone_id.company_id, self.mine,
            "a notification follows the company of the zone it belongs to",
        )

    # -------------------------------------------------------- system events
    def test_system_events_carry_the_webstack_and_skip_unowned_rows(self):
        """webstack_id is the only company link a system event has."""
        base = self._importer({'hr.rfid.event.system': [
            {'id': 11, 'timestamp': '2026-01-02 03:04:05',
             'webstack_id': [5, 'Module'], 'controller_id': False,
             'event_action': '99', 'occurrences': False, 'siren': False},
            {'id': 12, 'timestamp': '2026-01-02 03:04:06',
             'webstack_id': False, 'controller_id': False,
             'event_action': '99', 'occurrences': 2, 'siren': True},
        ]}, import_system_events=True)
        base._set_target_id('hr.rfid.webstack', 5, 4242)

        results = EventImporter(base).run(None)
        call = base.last_bulk('hr.rfid.event.system')

        self.assertIn(
            'webstack_id', call['columns'],
            "without webstack_id every system event lands unattributable - "
            "112 397 rows did exactly that on the pilot",
        )
        self.assertEqual(call['source_ids'], [11],
                         "an event with no owning module cannot be attributed")
        result = next(r for r in results
                      if r['model'] == 'hr.rfid.event.system')
        self.assertEqual(result['skipped_count'], 1)

        row = dict(zip(call['columns'], call['rows'][0]))
        self.assertEqual(row['webstack_id'], 4242)
        self.assertEqual(
            row['occurrences'], 1,
            "bulk SQL bypasses the ORM, so a field default must be supplied "
            "explicitly or the column lands NULL",
        )
        self.assertIs(row['siren'], False)

    def test_orphan_cutoff_limits_only_the_controller_less_events(self):
        """Events naming a controller are always taken in full."""
        base = self._importer({'hr.rfid.event.system': [
            {'id': 21, 'timestamp': '2026-01-01 00:00:00',
             'webstack_id': [5, 'M'], 'controller_id': False},
        ]}, import_system_events=True, orphan_event_cutoff='2026-04-27')
        base._set_target_id('hr.rfid.webstack', 5, 4242)
        EventImporter(base).run(None)

        domain = base.domains['hr.rfid.event.system']
        self.assertIn('|', domain, "the cutoff must be an OR branch, not a "
                                   "blanket date filter on all system events")
        self.assertIn(('controller_id', '!=', False), domain)
        self.assertIn(('timestamp', '>=', '2026-04-27'), domain)
        self.assertTrue(base.domain_mentions_company('hr.rfid.event.system'))

    def test_events_are_scoped_through_a_link_that_is_never_null(self):
        """A dotted domain is an EXISTS - a nullable link drops rows silently.

        door_id is nullable on both event models (the source writes it as
        False for alarm-line actions, and it is False on 100% of vending
        events), so the scope must go through reader_id, which the model
        declares required.
        """
        base = self._importer({'hr.rfid.event.user': [
            {'id': 31, 'event_time': '2026-01-02 03:04:05',
             'door_id': [9, 'D'], 'reader_id': [3, 'R'], 'event_action': '3'},
        ]}, import_user_events=True)
        base._set_target_id('hr.rfid.door', 9, 91)
        base._set_target_id('hr.rfid.reader', 3, 31)
        EventImporter(base).run(None)
        self.assertEqual(
            base.domains['hr.rfid.event.user'],
            [('reader_id.controller_id.webstack_id.company_id', 'in', [101])])

    def test_vending_events_survive_a_null_door(self):
        """Regression: scoping vending events on door_id dropped all 32046.

        Every vending event in the source has door_id = NULL, so a scope
        through door_id matched nothing and the whole vending history
        vanished while the protocol printed source_count = 0 - identical to
        a client that never had a vending machine.
        """
        base = self._importer({'hr.rfid.vending.event': [
            {'id': 41, 'event_time': '2026-01-02 03:04:05', 'door_id': False,
             'reader_id': [3, 'R'], 'controller_id': [1, 'C'],
             'event_action': '47', 'transaction_price': 1.5},
        ]}, import_vending=True)
        base._set_target_id('hr.rfid.reader', 3, 31)
        base._set_target_id('hr.rfid.ctrl', 1, self.ctrl.id)
        VendingImporter(base)._import_vending_events()

        self.assertNotIn(
            'door_id', str(base.domains['hr.rfid.vending.event']),
            "door_id is NULL on every source vending event; scoping on it "
            "silently drops the entire vending history",
        )
        call = base.last_bulk('hr.rfid.vending.event')
        self.assertIsNotNone(call, "a door-less vending event must still import")
        self.assertEqual(call['source_ids'], [41])

    def test_imported_user_lands_in_its_own_company(self):
        """res.users.company_id/company_ids default to the operator's company.

        Left to the default, a client's staff account becomes an internal
        user of whichever company the operator happened to be in - able to
        read that company, unable to see their own.
        """
        base = self._importer({
            'hr.employee': [{'id': 5, 'name': 'Emp', 'user_id': [9, 'u'],
                             'company_id': [101, 'A']}],
            'res.users': [{'id': 9, 'name': 'Tenant User',
                           'login': 'scope.tenant.user@example.com',
                           'active': True, 'partner_id': False,
                           'groups_id': [], 'company_id': [101, 'A']}],
        }, import_users=True)
        from ..models.importers.people_importer import PeopleImporter
        PeopleImporter(base)._import_users()

        user = self.env['res.users'].browse(base._get_target_id('res.users', 9))
        self.assertTrue(user, "the user must be created")
        self.assertEqual(user.company_id, self.mine)
        self.assertEqual(user.company_ids, self.mine)

    # ----------------------------------------------------------- attendance
    def test_attendance_counts_what_it_drops(self):
        """0 imported / 0 skipped hid whether there was any data at all."""
        base = self._importer({'hr.attendance': [
            {'id': 41, 'employee_id': [77, 'Someone else'],
             'check_in': '2026-01-02 08:00:00', 'check_out': False},
        ]}, import_attendance=True)
        results = AttendanceImporter(base).run(None)

        self.assertTrue(base.domain_mentions_company('hr.attendance'))
        result = next(r for r in results if r['model'] == 'hr.attendance')
        self.assertEqual(result['imported_count'], 0)
        self.assertEqual(
            result['skipped_count'], 1,
            "an unresolved employee must show up as skipped; otherwise "
            "'no attendance for this client' reads the same as "
            "'every attendance was thrown away'",
        )

    # -------------------------------------------------------- service sales
    def test_service_sale_writes_the_columns_that_exist(self):
        base = self._importer({'rfid.service.sale': [
            {'id': 51, 'service_id': [2, 'Svc'], 'partner_id': False,
             'card_id': False, 'create_date': '2026-01-02 03:04:05',
             'name': 'SALE/0001', 'state': 'active',
             'start_date': '2026-01-02', 'end_date': '2026-02-02',
             'access_group_contact_rel': [6, 'rel']},
        ]}, import_service=True)
        base._set_target_id('rfid.service', 2, 22)
        base._set_target_id('hr.rfid.access.group.contact.rel', 6, 66)
        ServiceImporter(base)._import_service_sales()

        call = base.last_bulk('rfid.service.sale')
        self.assertIn(
            'access_group_contact_rel', call['columns'],
            "the column has no _id suffix; the old probe never matched, so "
            "the link driving visit counting and cancellation was dropped",
        )
        self.assertNotIn('access_group_contact_rel_id', call['columns'])
        self.assertIn(
            'name', call['columns'],
            "the bulk path bypasses the ir.sequence default, so the human "
            "sale reference has to be carried over explicitly",
        )
        row = dict(zip(call['columns'], call['rows'][0]))
        self.assertEqual(row['access_group_contact_rel'], 66)
        self.assertEqual(row['name'], 'SALE/0001')
        self.assertTrue(base.domain_mentions_company('rfid.service.sale'))

    # ----------------------------------------------------- hardware details
    def test_th_sensor_and_input_mask_write_their_required_fields(self):
        """Both classes were rejected wholesale, then reported as "skipped".

        hr.rfid.ctrl.th.sensor_number is NOT NULL and was never read; the
        input mask was probed as name/mask while the real columns are
        i_number/i_mask. 116 masks and 1 sensor in the source produced 0 rows
        in the target, with no error anywhere.
        """
        base = self._importer({
            'hr.rfid.ctrl.th': [
                {'id': 61, 'controller_id': [1, 'C'], 'name': 'T1',
                 'sensor_number': 2, 'door_id': False},
            ],
            'hr.rfid.ctrl.input.mask': [
                {'id': 71, 'controller_id': [1, 'C'], 'i_number': 3,
                 'i_mask': True},
            ],
        })
        base._set_target_id('hr.rfid.ctrl', 1, self.ctrl.id)
        core = CoreImporter(base)
        core._import_th_sensors()
        core._import_input_masks()

        th_vals = base.vals_for('hr.rfid.ctrl.th')
        self.assertTrue(th_vals, "the TH sensor step must attempt a write")
        self.assertEqual(th_vals[0].get('sensor_number'), 2,
                         "sensor_number is NOT NULL in the target")

        mask_vals = base.vals_for('hr.rfid.ctrl.input.mask')
        self.assertTrue(mask_vals, "the input-mask step must attempt a write")
        self.assertEqual(mask_vals[0].get('i_number'), 3)
        self.assertIs(mask_vals[0].get('i_mask'), True)
        self.assertNotIn('mask', mask_vals[0],
                         "'mask' is not a field in either version")

        # The point of the fix is that the rows survive the target's NOT NULL
        # constraints - building the right vals is not enough.
        self.assertEqual(
            self.env['hr.rfid.ctrl.th'].browse(
                base._get_target_id('hr.rfid.ctrl.th', 61)).sensor_number, 2)
        self.assertEqual(
            self.env['hr.rfid.ctrl.input.mask'].browse(
                base._get_target_id('hr.rfid.ctrl.input.mask', 71)).i_number, 3)

    def test_workcode_uses_the_source_field_name(self):
        """o15 hr.rfid.workcode has `workcode`; reading `number` faults."""
        base = self._importer({'hr.rfid.workcode': [
            {'id': 81, 'name': 'Lunch', 'workcode': '0021',
             'user_action': 'start', 'company_id': [101, 'A']},
        ]})
        CoreImporter(base)._import_workcodes()
        vals = base.vals_for('hr.rfid.workcode')
        self.assertTrue(vals)
        self.assertEqual(vals[0].get('workcode'), '0021')
        self.assertEqual(vals[0].get('company_id'), self.mine.id)
        self.assertNotIn('number', vals[0])

    def test_failed_phase_does_not_leave_stale_ids_behind(self):
        """id_map живее в паметта и не се откатва със savepoint-а.

        Наблюдавано на живо: Phase 2 падна с hr_employee_user_uniq, а фази
        3b/4/5/6a/6b после гръмнаха една по една с ForeignKeyViolation, защото
        id_map още сочеше към откатнатите служители. По-опасният вариант е
        тих - освободеният id може да бъде преизползван от друг запис и FK-ът
        да сочи към ЧУЖДИ данни, без никаква грешка.
        """
        wiz = self.env['hr.rfid.odoo.import.wiz'].create({
            'source_url': 'http://localhost:1', 'source_login': 'x',
            'source_password': 'x',
        })
        base = self._importer({})
        base._set_target_id('hr.employee', 1, 111)   # отпреди фазата - остава

        class _Boom:
            def __init__(self, b):
                self.b = b

            def run(self, wizard):
                # фазата мапва нещо и после пада
                self.b._set_target_id('hr.employee', 2, 222)
                raise ValueError("phase blew up")

        wiz._run_phase('Phase X', 'Broken', _Boom(base), 0, 1)

        self.assertEqual(
            base._get_target_id('hr.employee', 1), 111,
            "мапингите отпреди фазата трябва да оцелеят")
        self.assertFalse(
            base._get_target_id('hr.employee', 2),
            "мапинг, направен във фаза, която се е откатила, НЕ бива да остане - "
            "иначе следващите фази пишат FK към несъществуващ запис")

    def test_scoped_domain_builds_direct_and_chained_restrictions(self):
        base = self._importer({})
        self.assertEqual(base._scoped_domain(),
                         [('company_id', 'in', [101])])
        self.assertEqual(base._scoped_domain('webstack_id'),
                         [('webstack_id.company_id', 'in', [101])])
        self.assertEqual(
            base._scoped_domain('door_id.controller_id.webstack_id'),
            [('door_id.controller_id.webstack_id.company_id', 'in', [101])])


class _RecordingProxy:
    """Captures the kwargs each source call was made with."""

    def __init__(self):
        self.calls = []

    def execute_kw(self, db, uid, password, model, method, args, kwargs=None):
        self.calls.append({'model': model, 'method': method,
                           'domain': args[0] if args else None,
                           'kwargs': kwargs or {}})
        if method == 'fields_get':
            # door/reader carry no `active` field in the source - exactly the
            # models the archived-chain defect hit.
            return {} if model in ('hr.rfid.door', 'hr.rfid.reader') else {'active': {}}
        if method == 'search':
            return [7, 3, 9]          # deliberately NOT sorted
        if method == 'read':
            return [{'id': 3, 'name': 'c'}, {'id': 9, 'name': 'i'},
                    {'id': 7, 'name': 'g'}]   # and returned in yet another order
        return 0


@tagged("post_install", "-at_install", "rfid_odoo_import", "rfid_import_scope")
class TestSourceReadsIncludeArchivedChain(TransactionCase):
    """An archived record must not hide everything hanging off it.

    Measured on the live source (company 1): the scoped domain
    ``controller_id.webstack_id.company_id`` returned 21 doors and 25 readers,
    but 22 and 29 with ``active_test=False`` - one door and four readers sat
    under two archived webstacks, and 143 of their events were dropped after
    them. The ``('active', 'in', [True, False])`` leaf could never have caught
    it: it only covers the model being read, and neither door nor reader even
    HAS an ``active`` field. The ORM applies ``active_test`` to the
    INTERMEDIATE models of a chained domain.
    """

    def _importer(self):
        base = BaseImporter.__new__(BaseImporter)
        base.env = self.env
        base.source_db = 'src'
        base.source_uid = 1
        base.source_password = 'x'
        base.company_map = {101: self.env.company.id}
        base.id_map = {}
        base.options = {}
        base._field_cache = {}
        base.rpc_models = _RecordingProxy()
        base.refused_fields = {}
        return base

    def test_search_read_disables_active_test_on_both_calls(self):
        """search AND read must carry the context.

        The source's own record rule is a dotted company check, so with
        active_test on it cannot see a record under an archived webstack and
        DENIES it. A single search_read raised AccessError on exactly that
        record; the split call, with the context on both halves, returns it.
        """
        base = self._importer()
        base._search_read('hr.rfid.reader',
                          [('controller_id.webstack_id.company_id', 'in', [101])],
                          ['name'])
        methods = [c['method'] for c in base.rpc_models.calls]
        self.assertNotIn(
            'search_read', methods,
            "search_read evaluates the source record rule in a context that "
            "cannot see archived intermediates - use search + read",
        )
        for method in ('search', 'read'):
            call = [c for c in base.rpc_models.calls if c['method'] == method][0]
            self.assertFalse(
                call['kwargs'].get('context', {}).get('active_test', True),
                "%s must pass active_test=False, otherwise an archived webstack "
                "hides its controllers, doors, readers and events" % method,
            )

    def test_search_read_preserves_the_searched_order(self):
        """_read_all paginates on the last id seen - order cannot be left to read()."""
        base = self._importer()
        rows = base._search_read('hr.rfid.reader', [('id', '>', 0)], ['name'])
        self.assertEqual(
            [r['id'] for r in rows], [7, 3, 9],
            "rows must come back in the order search returned them, not the "
            "order read() happened to produce",
        )

    def test_search_count_uses_the_same_axis_as_the_read(self):
        """The preview count must not promise more than the import delivers."""
        base = self._importer()
        base._search_count('hr.rfid.reader',
                           [('controller_id.webstack_id.company_id', 'in', [101])])
        call = [c for c in base.rpc_models.calls if c['method'] == 'search_count'][0]
        self.assertFalse(
            call['kwargs'].get('context', {}).get('active_test', True),
            "count and read must use the same axis or the operator is shown a "
            "number the import will not deliver",
        )

    def test_active_leaf_still_added_when_the_model_has_the_field(self):
        base = self._importer()
        base._search_read('hr.rfid.card', [('company_id', 'in', [101])], ['name'])
        call = [c for c in base.rpc_models.calls if c['method'] == 'search'][0]
        self.assertIn(('active', 'in', [True, False]), call['domain'])
