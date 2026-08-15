# -*- coding: utf-8 -*-
import logging
import time
import xmlrpc.client

from odoo import _
from odoo.tools import mute_logger
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ir.model.data module used for every imported record's external ID.
# Matches the standard Odoo import convention (odoo/orm/models.py load():
# context.get('module', '__import__')), so imports stay idempotent on re-run.
EXTERNAL_ID_MODULE = '__import__'

# Every external ID this transfer writes starts with this, followed by the
# source identity - see _xml_id_name(). Read by anything that has to recognise
# a record this transfer brought over.
EXTERNAL_ID_PREFIX = 'rfid_import_'

# How many rows refused by a database constraint are probed one-by-one to name
# the exact constraint in the protocol. Rejections are rare (a handful per
# run); the cap only guards against a pathological source.
MAX_REJECT_PROBES = 10


def normalise_source_slug(value):
    """The source identity as it appears inside an external ID.

    An external ID name may not carry dots, so the same rule has to be applied
    everywhere the identity is built or compared - otherwise a check answers
    about one spelling while the transfer writes another.
    """
    return (value or '').replace('-', '_').replace('.', '_')


# Context flags for suppressing side-effects during import
IMPORT_CONTEXT = {
    'no_hardware_commands': True,
    'tracking_disable': True,
    'mail_create_nolog': True,
    'mail_create_nosubscribe': True,
    'mail_activity_automation_skip': True,
    'no_reset_password': True,
}


class BaseImporter:
    """Base class for all importers.

    Handles XML-RPC reading from source and ORM writing to target.
    Maintains a global id_map for cross-phase lookups.
    """

    def __init__(self, env, source_url, source_db, source_uid, source_password,
                 company_map, options, source_slug=None):
        self.env = env
        # XML-RPC connection (source - read only)
        self.source_url = source_url
        self.source_db = source_db
        # Identity of the SOURCE SYSTEM in the external IDs. Defaults to the
        # database name (right for a one-shot import); set explicitly when the
        # same source is read from more than one place - backup for the bulk,
        # live server for the delta - so both write the SAME external IDs.
        self.source_slug = normalise_source_slug(source_slug or source_db)
        self.source_uid = source_uid
        self.source_password = source_password
        self.rpc_models = xmlrpc.client.ServerProxy(
            f'{source_url}/xmlrpc/2/object',
            allow_none=True,
        )
        # Mapping
        self.company_map = company_map      # {source_co_id: target_co_id}
        self.id_map = {}                    # {model: {source_id: target_id}}
        self.options = options              # wizard options dict
        # Cache
        self._field_cache = {}             # {model: {field_name: field_info}}
        self._readable_cache = {}          # {(model, fields): proven-readable}
        #: Optional callable answering "is my time up?". Set by a background
        #: run so a long read can stop between pages instead of running past
        #: the worker's time limit and taking the server down with it.
        self.time_is_up = None
        #: True once a read stopped early. The phase is then incomplete, not
        #: finished, and the run knows to come back to it.
        self.stopped_early = False
        #: Where each paged read got to, so the next pass carries on rather
        #: than starting the same read from the beginning. Persisted by the
        #: run record between passes.
        self.read_cursors = {}
        #: {model: {field, ...}} the source refused to hand over (field-level
        #: groups= on the source side). Remembered so later pages skip the
        #: probing, and reported so nothing is left behind silently.
        self.refused_fields = {}
        #: {(model, source_id) | (None, text): count} - why rows were left
        #: behind since the last protocol line. Filled by the mapping
        #: chokepoints themselves, so every step reports its reasons without
        #: each of the fifty-nine skip sites having to remember to write them.
        #: Drained by _make_result into the line being written (owner's rule,
        #: 2026-08-15: the log carries the real picture, nobody guesses).
        self._pending_skips = {}

    # ── Source reading (XML-RPC) ──────────────────────────────

    #: Context for every source read. ``active_test=False`` is REQUIRED, not a
    #: nicety: the ``('active', 'in', [True, False])`` leaf below only covers the
    #: model being read, while a scoped domain walks a CHAIN
    #: (``controller_id.webstack_id.company_id``) and the ORM applies
    #: ``active_test`` to the INTERMEDIATE models. An archived device therefore
    #: hides everything hanging off it, silently and with no count to notice it
    #: by. Measured against the live source: company 1 returned 21 doors and 25
    #: readers with the leaf alone, 22 and 29 with this context - one door and
    #: four readers lived under two archived webstacks, and 143 of their events
    #: were dropped after them. Neither door nor reader even HAS an ``active``
    #: field, so no leaf could ever have saved them.
    SOURCE_READ_CONTEXT = {'active_test': False}

    def _search_read(self, model, domain, fields, order='id asc', limit=0,
                     include_archived=True):
        """Read records from source via XML-RPC, as ``search`` + ``read``.

        Includes archived records (the model's own and any along a chained
        domain) so the transfer is complete - see ``SOURCE_READ_CONTEXT``.

        The two calls are NOT a stylistic choice. The source's own record rule
        is ``[('webstack_id.company_id', 'in', company_ids)]``, and with
        ``active_test`` on, that dotted check cannot see a record whose webstack
        is archived - so the source DENIES a record that by its own data belongs
        to the company. A single ``search_read`` raises AccessError on it (the
        run died on two tenants); ``search`` then ``read``, both carrying the
        context, returns it. Verified against the live source: door id 1 of
        company 1, under an archived webstack.
        """
        read_domain = list(domain)
        context = {}
        if include_archived:
            context = dict(self.SOURCE_READ_CONTEXT)
            if self._has_field(model, 'active'):
                # Kept next to the context on purpose: it states the intent on
                # the model being read even if a caller passes its own context.
                if not any(d[0] == 'active' for d in read_domain if isinstance(d, (list, tuple)) and len(d) >= 1):
                    read_domain.append(('active', 'in', [True, False]))

        search_kwargs = {'order': order}
        if limit:
            search_kwargs['limit'] = limit
        if context:
            search_kwargs['context'] = dict(context)
        ids = self._search_dropping_refused_filters(
            model, read_domain, search_kwargs)
        if not ids:
            return []
        # ``_classic_write`` returns a Many2one as a bare id instead of
        # [id, display_name]. The names are of no use here - every mapping goes
        # through the id - and asking for them makes the SOURCE compute
        # display_name for each one. On a real Odoo 17 that raised outright:
        # reading hr.rfid.door failed because the controller's display_name
        # touches a field that database no longer has, and with the doors gone
        # every reader, every access right and all 44 756 events had nothing to
        # attach to. Not asking for what we do not need makes the read immune
        # to whatever the other system's display names depend on.
        read_kwargs = {'load': '_classic_write'}
        if context:
            read_kwargs['context'] = dict(context)
        records = self._read_dropping_refused_fields(
            model, ids, fields, read_kwargs)
        # `read()` does not promise the searched order, and `_read_all` paginates
        # on the LAST id it saw - an unordered page would skip or repeat rows.
        by_id = {r['id']: r for r in records}
        return [by_id[i] for i in ids if i in by_id]

    #: xmlrpc fault code the source raises for AccessError - the same constant
    #: on every version we read (odoo18 addons/base/controllers/rpc.py:28,
    #: RPC_FAULT_CODE_ACCESS_ERROR = 4; historically in service/wsgi_server.py).
    #: Matching the CODE, never the message: the message arrives in whatever
    #: language the source speaks.
    RPC_FAULT_ACCESS_ERROR = 4

    def _search_dropping_refused_filters(self, model, domain, search_kwargs):
        """Search, and when the source refuses a FIELD used in the filter,
        drop that filter - never the whole step.

        The read half of this pair was not enough: the live migration that
        forced it (company_id on the emergency-signal groups, readable only by
        the multi-company group) failed AGAIN on the re-run, because the step
        filters BY that same field - the refusal now came from the search call.
        Dropping the filter is sound where it matters: on a single-company
        source a company filter selects everything anyway, and the source's own
        record rules still bound what this account may see.
        """
        def _search(dom):
            return self.rpc_models.execute_kw(
                self.source_db, self.source_uid, self.source_password,
                model, 'search', [dom], search_kwargs,
            )

        known = self.refused_fields.get(model)
        if known:
            domain = self._domain_without_fields(domain, known)
        try:
            return _search(domain)
        except xmlrpc.client.Fault as fault:
            if fault.faultCode != self.RPC_FAULT_ACCESS_ERROR:
                raise
        # Which filtered field is the refused one? Try the domain without each
        # in turn - domains here carry a handful of leaves at most.
        for field in self._domain_fields(domain):
            try:
                ids = _search(self._domain_without_fields(domain, {field}))
            except xmlrpc.client.Fault as fault:
                if fault.faultCode != self.RPC_FAULT_ACCESS_ERROR:
                    raise
                continue
            self.refused_fields.setdefault(model, set()).add(field)
            _logger.warning(
                "%s: the source refuses filtering by %r - reading without "
                "that filter; its own access rules still apply", model, field)
            return ids
        # No single field explains it (the rows themselves are refused, say):
        # the original failure stands and the step isolation records it.
        return _search(domain)

    @staticmethod
    def _domain_fields(domain):
        """Field names a domain filters by, dotted paths by their first hop."""
        seen = []
        for leaf in domain:
            if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                root = str(leaf[0]).split('.')[0]
                if root not in seen:
                    seen.append(root)
        return seen

    @staticmethod
    def _domain_without_fields(domain, fields_):
        """The same domain minus every leaf on the given fields.

        Operators ('|', '&', '!') are rebuilt by dropping one prefix operator
        per removed leaf - the shapes used in this module (plain AND lists and
        a leading OR pair) survive that; anything more exotic would need a real
        polish-notation rewrite and does not occur here.
        """
        kept = []
        removed = 0
        for leaf in domain:
            if (isinstance(leaf, (list, tuple)) and len(leaf) == 3
                    and str(leaf[0]).split('.')[0] in fields_):
                removed += 1
            else:
                kept.append(leaf)
        while removed and kept and kept[0] in ('|', '&'):
            kept.pop(0)
            removed -= 1
        return kept

    def _read_dropping_refused_fields(self, model, ids, fields, read_kwargs):
        """Read, and when the source refuses a FIELD, leave the field - never
        the records.

        A field can carry its own groups= restriction. hr_rfid ships exactly
        one that bites here: company_id on the emergency-signal groups is
        readable only by the multi-company group, and on a single-company
        source the admin account is not in it. The refusal of that one field
        took the whole hardware phase down at a live migration (192.168.0.99,
        2026-08-14) - no controllers, no doors, no cards, 20 851 events with
        nothing to attach to. On a single-company source the CONTENT of such a
        field is worthless anyway: which company records land in is decided by
        the operator's company mapping, not by the source.

        The refused fields are found by probing one field at a time against a
        single record - only after a refusal, so the happy path stays two RPC
        calls. Dropped fields are remembered per model and reported in the
        protocol, because data left behind silently is the defect this module
        exists to avoid.
        """
        known = self.refused_fields.get(model)
        if known:
            # Later pages of the same model skip both the doomed attempt and
            # the field-by-field probing - at 20 851 events that would be
            # thousands of pointless round trips.
            fields = [f for f in fields if f not in known]
        try:
            return self.rpc_models.execute_kw(
                self.source_db, self.source_uid, self.source_password,
                model, 'read', [ids, fields], read_kwargs,
            )
        except xmlrpc.client.Fault as fault:
            if fault.faultCode != self.RPC_FAULT_ACCESS_ERROR:
                raise
        refused = []
        for field in fields:
            try:
                self.rpc_models.execute_kw(
                    self.source_db, self.source_uid, self.source_password,
                    model, 'read', [ids[:1], [field]], read_kwargs,
                )
            except xmlrpc.client.Fault as fault:
                if fault.faultCode != self.RPC_FAULT_ACCESS_ERROR:
                    raise
                refused.append(field)
        if not refused:
            # The refusal was not about a field after all (a record rule that
            # denies the rows themselves, say) - nothing to drop, so the
            # original failure stands and the step's own isolation records it.
            return self.rpc_models.execute_kw(
                self.source_db, self.source_uid, self.source_password,
                model, 'read', [ids, fields], read_kwargs,
            )
        newly = set(refused) - self.refused_fields.setdefault(model, set())
        if newly:
            self.refused_fields[model].update(newly)
            _logger.warning(
                "%s: the source refuses to hand over field(s) %s - reading "
                "without them; records still come across in full otherwise",
                model, ', '.join(sorted(newly)))
        kept = [f for f in fields if f not in self.refused_fields[model]]
        return self.rpc_models.execute_kw(
            self.source_db, self.source_uid, self.source_password,
            model, 'read', [ids, kept], read_kwargs,
        )

    #: Marks a read that has reached the end of the source.
    CURSOR_FINISHED = -1

    def _read_all(self, model, domain, fields, batch_size=1000, cursor_key=None):
        """ID-based pagination for large datasets.

        Stops between pages when the caller's time is up, and REMEMBERS where
        it stopped when given a ``cursor_key``. Without that memory the next
        pass starts from the first page again: on a real customer with 44 756
        events, each pass re-read the same opening pages, ran out of time in
        the same place, and the transfer never advanced - measured, 29 passes
        that moved nothing. Skipping already-imported rows is not enough,
        because the cost is the reading, not the writing.

        The cursor is kept by the caller (the run record) so it survives the
        process, and is set to CURSOR_FINISHED once the source is exhausted, so
        a completed read is not repeated at all.
        """
        if cursor_key and self.read_cursors.get(cursor_key) == self.CURSOR_FINISHED:
            return []

        all_records = []
        last_id = self.read_cursors.get(cursor_key, 0) if cursor_key else 0
        while True:
            batch_domain = [('id', '>', last_id)] + domain
            records = self._search_read(
                model, batch_domain, fields, order='id asc', limit=batch_size
            )
            if not records:
                if cursor_key:
                    self.read_cursors[cursor_key] = self.CURSOR_FINISHED
                break
            all_records.extend(records)
            last_id = records[-1]['id']
            if cursor_key:
                self.read_cursors[cursor_key] = last_id
            if self.time_is_up and self.time_is_up():
                self.stopped_early = True
                _logger.info(
                    "%s: read %d records up to id %s - out of time for this "
                    "pass, will carry on from there",
                    model, len(all_records), last_id)
                break
        return all_records

    def _search_count(self, model, domain):
        """Count records in source (including archived - see SOURCE_READ_CONTEXT).

        The preview count MUST use the same axis as the read that follows it,
        or the operator is shown a number the import will not deliver.
        """
        count_domain = list(domain)
        if self._has_field(model, 'active'):
            if not any(d[0] == 'active' for d in count_domain if isinstance(d, (list, tuple)) and len(d) >= 1):
                count_domain.append(('active', 'in', [True, False]))
        return self.rpc_models.execute_kw(
            self.source_db, self.source_uid, self.source_password,
            model, 'search_count', [count_domain],
            {'context': dict(self.SOURCE_READ_CONTEXT)},
        )

    def _has_field(self, model, field_name):
        """Check if field exists in source model via fields_get()."""
        if model not in self._field_cache:
            self._field_cache[model] = self.rpc_models.execute_kw(
                self.source_db, self.source_uid, self.source_password,
                model, 'fields_get', [],
                {'attributes': ['type', 'relation', 'required', 'store']}
            )
        return field_name in self._field_cache[model]

    def _has_stored_field(self, model, field_name):
        """Whether the source can actually READ that field back.

        Presence in ``fields_get`` is not enough. It also lists computed
        fields that were never stored, and asking for one of those in a
        ``read`` makes the source raise UndefinedColumn - which takes the whole
        phase down. Measured against a live Odoo 15: hr.rfid.event.user
        advertises department_id, and selecting it fails because the column
        does not exist there.

        Older sources may not report the attribute at all; treat that as
        stored, which is the pre-existing behaviour.
        """
        fields_info = self._get_source_fields(model)
        if field_name not in fields_info:
            return False
        return (fields_info[field_name] or {}).get('store', True)

    def _readable_fields(self, model, candidates):
        """The subset of ``candidates`` this source can actually hand over.

        Asked outright, the source can be wrong about itself. Measured against
        a live Odoo 15: ``hr.rfid.event.user.department_id`` is declared
        ``store=True`` (it is a stored related field) and the column does not
        exist in the database - the model and the schema had drifted apart
        there long before this migration. Selecting it raises UndefinedColumn
        and takes the whole step down.

        So the set is PROVEN, not trusted: one cheap read of a single row. If
        that fails, the fields are tried one at a time and the offenders are
        left out, with a warning naming them - a column the source cannot
        produce is worth knowing about even though the transfer goes on.
        """
        wanted = [f for f in candidates if self._has_stored_field(model, f)]
        if not wanted:
            return []
        cache_key = (model, tuple(wanted))
        if cache_key in self._readable_cache:
            return self._readable_cache[cache_key]

        if self._can_read_fields(model, wanted):
            self._readable_cache[cache_key] = wanted
            return wanted

        usable, refused = [], []
        for field in wanted:
            (usable if self._can_read_fields(model, [field]) else refused).append(field)
        if refused:
            _logger.warning(
                "%s: the other system cannot return %s - those columns are "
                "missing there. Carrying on without them.",
                model, ', '.join(refused))
        self._readable_cache[cache_key] = usable
        return usable

    def _can_read_fields(self, model, fields):
        """Whether one row of ``model`` can be read with exactly these fields."""
        if not getattr(self, 'rpc_models', None):
            # Nothing to ask (a stand-in source in the tests). Take the
            # declaration at face value, which is the behaviour that was there
            # before the probe existed.
            return True
        try:
            self.rpc_models.execute_kw(
                self.source_db, self.source_uid, self.source_password,
                model, 'search_read', [[]],
                {'fields': list(fields), 'limit': 1,
                 'context': dict(self.SOURCE_READ_CONTEXT)},
            )
            return True
        except xmlrpc.client.Fault:
            return False

    def _get_source_fields(self, model):
        """Get all source fields metadata (cached)."""
        if model not in self._field_cache:
            self._has_field(model, '_dummy_')  # populate cache
        return self._field_cache[model]

    def _has_model(self, model):
        """Check if model exists in source."""
        try:
            self.rpc_models.execute_kw(
                self.source_db, self.source_uid, self.source_password,
                model, 'search_count', [[]]
            )
            return True
        except xmlrpc.client.Fault:
            return False

    # ── Target writing (ORM) ──────────────────────────────────

    def _load_records(self, model_name, data_list):
        """Create by external ID, or refresh what that external ID already names.

        A record is never created twice: the external ID is looked up first and
        an existing one is written to instead (odoo/orm/models.py:5150-5169).

        A SECOND RUN THEREFORE REFRESHES FROM THE SOURCE. That is the intended
        behaviour, decided by the owner. The ``'noupdate': True`` carried in
        ``data_list`` is recorded on the metadata row but changes nothing here:
        core only honours it when it is called with ``update=True``
        (``if not (update and d_noupdate)``, odoo/orm/models.py:5165), and this
        call does not. So anything altered here since the last transfer - a
        corrected name, a card switched off - is put back to what the other
        system holds. The operator is told this before starting; see the
        wizard's warnings.

        Args:
            model_name: Target model name (e.g. 'hr.rfid.webstack')
            data_list: List of dicts with keys: xml_id, values, noupdate

        Returns:
            Created/updated recordset
        """
        if not data_list:
            return self.env[model_name]
        Model = self.env[model_name].with_context(**IMPORT_CONTEXT)
        return Model._load_records(data_list)

    def _try_load_records(self, model_name, data_list, note=True):
        """Load records with savepoint - skip silently on failure.

        Use this for records that may have incompatible schemas between versions
        (e.g., hardware sub-records like input_mask, output_ts, alarm, th).

        Returns:
            Recordset on success, empty recordset on failure.
        """
        if not data_list:
            return self.env[model_name]
        try:
            with self.env.cr.savepoint():
                return self._load_records(model_name, data_list)
        except Exception as e:
            _logger.warning("Skipped %s create: %s", model_name, e)
            # The refusal reaches the protocol line, not only the server log -
            # UserError/ValidationError texts are already written for people.
            # note=False is for callers with their own recovery: the verbatim
            # membership copy lands exactly these rows a moment later, and a
            # live protocol read "done - Cannot change the employee, 64 rows"
            # over a step that had in fact delivered all sixty-four.
            if note:
                self.note_skip_reason(str(e).split('\n')[0][:160])
            return self.env[model_name]

    def _direct_sql_insert(self, table, columns, rows, batch_size=5000):
        """Direct SQL INSERT into target DB - bypass ORM.

        Uses execute_values for performance. Skips duplicates via ON CONFLICT.

        WARNING - NOT idempotent on re-run: rows are inserted with a fresh
        auto-generated ``id`` and the target tables only have a PK, so
        ``ON CONFLICT DO NOTHING`` never matches and a second run DUPLICATES
        every row. Use :meth:`_direct_sql_insert_tracked` for migration data
        (it records an ``ir.model.data`` external ID per row, exactly like the
        ORM import path, which makes re-runs idempotent).
        """
        if not rows:
            return 0
        from psycopg2.extras import execute_values
        total = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            placeholders = ', '.join(['%s'] * len(columns))
            cols = ', '.join(columns)
            execute_values(
                self.env.cr._obj,
                f"INSERT INTO {table} ({cols}) VALUES %s ON CONFLICT DO NOTHING",
                batch,
                template=f"({placeholders})",
            )
            total += len(batch)
        return total

    def already_imported(self, model, source_ids):
        """Map source ids that were already imported to their target ids.

        Mirrors the ORM import dedup (ir.model.data) for bulk-inserted rows.
        The lookup JOINs the target table, so an external ID whose row is gone
        (deleted, or cascaded away) does NOT count as imported - the record is
        re-imported instead of being silently skipped forever.

        Returns:
            dict: {source_id: target_id} for the records already present.
        """
        if not source_ids:
            return {}
        prefix = model.replace('.', '_')
        by_name = {self._xml_id_name(prefix, sid): sid for sid in source_ids}
        # Model-derived table name (trusted, not user input).
        table = self.env[model]._table
        found = {}
        names = list(by_name)
        for i in range(0, len(names), 10000):
            chunk = names[i:i + 10000]
            self.env.cr.execute(
                f"SELECT d.name, d.res_id FROM ir_model_data d "
                f'JOIN "{table}" t ON t.id = d.res_id '
                f"WHERE d.module = %s AND d.model = %s AND d.name = ANY(%s)",
                (EXTERNAL_ID_MODULE, model, chunk),
            )
            for name, res_id in self.env.cr.fetchall():
                found[by_name[name]] = res_id
        return found

    def _match_by_external_id(self, model, source_ids):
        """Map source records to the SAME records shipped with our modules.

        For reference data that both systems get from the same module - card
        types, and anything else defined in module data - the external id is a
        stable code shared by both sides. Bringing such a record across as a
        new row creates a second one that the application does not recognise
        as the original, because the code refers to the shipped one.

        Returns {source_id: target_id} for those that exist on both sides.
        """
        if not source_ids:
            return {}
        try:
            rows = self._search_read(
                'ir.model.data',
                [('model', '=', model), ('res_id', 'in', list(source_ids))],
                ['module', 'name', 'res_id'],
            )
        except Exception:
            _logger.warning(
                "Could not read the external ids of %s from the other system; "
                "records that ship with the modules may be duplicated instead "
                "of matched", model, exc_info=True)
            return {}
        matched = {}
        for row in rows:
            if row['module'].startswith('__'):
                # Written by an import on the source side, not shipped data.
                continue
            target = self.env.ref('%s.%s' % (row['module'], row['name']),
                                  raise_if_not_found=False)
            if target and target._name == model:
                matched[row['res_id']] = target.id
        return matched

    def prefetch_external_ids(self, model, source_ids):
        """Load what a previous pass already imported into the in-memory map.

        ``id_map`` lives in memory (see __init__). A new process - the next
        cron cycle, or another worker picking the job up - starts with it
        empty, so every relation resolves to False and the row is counted as
        skipped. The protocol then looks perfectly normal while the data is
        not there. The external IDs are the durable half of that map; this
        reads them back in one query instead of one per lookup.
        """
        if not source_ids:
            return 0
        found = self.already_imported(model, source_ids)
        for source_id, target_id in found.items():
            self._set_target_id(model, source_id, target_id)
        return len(found)

    def find_by_external_id(self, model, source_id, expect_text=None,
                            text_field='name'):
        """The only identity allowed: the source id, through its external ID.

        Matching by TEXT (name, e-mail, number) merges DIFFERENT things that
        happen to read alike, and splits one thing in two when the text drifts
        by a single character. Both are silent. Measured live: this transfer
        matched employees by ``name`` and 1059 people at one customer arrived
        as 1022 - exactly the number of distinct names; the missing ones were
        merged into their namesakes together with their cards and events.

        ``expect_text`` is a SECOND check on the record already found by id -
        it confirms we landed on the right one. A mismatch does NOT send the
        search elsewhere; it is reported, because it means either the record
        metadata or the data itself has moved.

        Returns:
            recordset - the record found, or empty when no external ID names
            it (=> NEW).
        """
        Model = self.env[model].sudo().with_context(active_test=False)
        target_id = self._get_target_id(model, source_id)
        if not target_id:
            target_id = self._resolve_from_imd(model, source_id)
        if not target_id:
            return Model.browse()
        rec = Model.browse(target_id).exists()
        if rec and expect_text and text_field in rec._fields:
            actual = rec[text_field] or ''
            if actual.strip().lower() != (expect_text or '').strip().lower():
                _logger.warning(
                    "%s source=%s: the external ID points at record %s whose "
                    "%s is %r while the source says %r - the match by id "
                    "stands, but the difference needs a look",
                    model, source_id, rec.id, text_field, actual, expect_text)
        return rec

    #: Temporary bridge under the old name. The camera, people and service
    #: importers still call it and are outside the scope of this change;
    #: remove once those three have been renamed too.
    find_by_ledger = find_by_external_id

    def link_existing(self, model, source_id, target_id):
        """Record a source->target mapping for a record we did NOT create.

        The external ID IS the migration's source->target map, so it has to
        exist whether the target record was created by this import or matched
        to one that was already present. Without it, reconciliation counts the
        class as missing even though the data is there and correctly mapped -
        measured on the pilot: 16 time schedules linked, reconciliation
        reported 0 in the target for both pilot tenants.
        """
        self._set_target_id(model, source_id, target_id)
        self.env.cr.execute(
            "INSERT INTO ir_model_data "
            "(module, name, model, res_id, noupdate, create_date, write_date) "
            "VALUES (%s, %s, %s, %s, TRUE, now() at time zone \'UTC\', "
            "now() at time zone \'UTC\') "
            "ON CONFLICT (module, name) DO NOTHING",
            (EXTERNAL_ID_MODULE, self._xml_id_name(model.replace('.', '_'), source_id),
             model, target_id),
        )

    def _direct_sql_insert_tracked(self, table, columns, rows, model, source_ids,
                                   batch_size=5000):
        """Idempotent bulk INSERT: SQL speed + ``ir.model.data`` external ID.

        This is the bulk counterpart of the standard Odoo import: every row gets
        an external ID (``__import__.rfid_import_{source_slug}_{model}_{source_id}``)
        exactly like ORM-loaded records, so a second run skips what is already
        there instead of duplicating it.

        ``rows[i]`` must correspond to ``source_ids[i]``.

        Target ids are drawn from the table sequence UP FRONT (rather than read
        back with ``RETURNING``) so the source→target mapping stays exact even
        when a batch is partially skipped. An external ID is written ONLY for a
        row the database actually accepted, so "external ID exists" always
        means "row exists".

        Returns:
            tuple[int, int, int]: (inserted now, already imported before,
            rejected by a constraint). ``rejected`` is reported so the phase
            log can distinguish "nothing to do" from "the database refused
            every row" - a rejection that is only logged is invisible to the
            operator reading the import protocol.
        """
        if not rows:
            return 0, 0, 0
        if len(rows) != len(source_ids):
            raise UserError(_(
                "Bulk import bug: %(rows)d rows but %(ids)d source ids for %(model)s.",
                rows=len(rows), ids=len(source_ids), model=model,
            ))
        from psycopg2.extras import execute_values

        done = self.already_imported(model, source_ids)
        # A resumed run must still resolve these for later phases/relations,
        # otherwise FKs pointing at bulk models would silently become NULL.
        for sid, target_id in done.items():
            self._set_target_id(model, sid, target_id)

        pending = [(r, sid) for r, sid in zip(rows, source_ids) if sid not in done]
        if not pending:
            _logger.info("%s: all %d rows already imported (external ID) - skipped",
                         model, len(rows))
            return 0, len(done), 0

        prefix = model.replace('.', '_')
        cols = ', '.join(['id'] + list(columns))
        placeholders = ', '.join(['%s'] * (len(columns) + 1))
        inserted = 0
        rejected = 0
        # Buffered: only published once every batch succeeded, so a savepoint
        # rollback in the caller cannot leave stale ids behind in id_map.
        mapped = []

        for i in range(0, len(pending), batch_size):
            batch = pending[i:i + batch_size]
            # Reserve target ids from the table sequence (exact, ordered mapping).
            self.env.cr.execute(
                "SELECT nextval(pg_get_serial_sequence(%s, 'id')) "
                "FROM generate_series(1, %s)",
                (table, len(batch)),
            )
            new_ids = [r[0] for r in self.env.cr.fetchall()]

            returned = execute_values(
                self.env.cr._obj,
                f"INSERT INTO {table} ({cols}) VALUES %s "
                f"ON CONFLICT DO NOTHING RETURNING id",
                [(nid,) + tuple(row) for nid, (row, _sid) in zip(new_ids, batch)],
                template=f"({placeholders})",
                fetch=True,
            )
            accepted_ids = {r[0] for r in returned}
            accepted = [(nid, sid) for nid, (_row, sid) in zip(new_ids, batch)
                        if nid in accepted_ids]
            if len(accepted) != len(batch):
                refused = [(row, sid) for nid, (row, sid)
                           in zip(new_ids, batch) if nid not in accepted_ids]
                rejected += len(refused)
                _logger.warning(
                    "%s: %d of %d rows rejected by a constraint - no external ID "
                    "(they will be retried on the next run)",
                    model, len(refused), len(batch),
                )
                self._explain_refused_rows(table, columns, model, refused)
            if not accepted:
                continue

            execute_values(
                self.env.cr._obj,
                "INSERT INTO ir_model_data "
                "(module, name, model, res_id, noupdate, create_date, write_date) "
                "VALUES %s ON CONFLICT (module, name) DO NOTHING",
                [
                    (EXTERNAL_ID_MODULE, self._xml_id_name(prefix, sid), model, nid, True)
                    for nid, sid in accepted
                ],
                template="(%s, %s, %s, %s, %s, now() at time zone 'UTC', now() at time zone 'UTC')",
            )
            mapped.extend(accepted)
            inserted += len(accepted)

        # Publish the mapping only after the whole call succeeded.
        for nid, sid in mapped:
            self._set_target_id(model, sid, nid)

        _logger.info("%s: inserted %d rows (%d already imported, %d rejected)",
                     model, inserted, len(done), rejected)
        return inserted, len(done), rejected

    # ── ID Mapping ────────────────────────────────────────────

    def _explain_refused_rows(self, table, columns, model, refused):
        """Name the exact constraint behind every refused row, in the protocol.

        ON CONFLICT DO NOTHING skips a row without saying which constraint
        stopped it - the protocol showed "1 rejected" and nothing else, and
        the owner's rule stands: the log carries the cause, nobody guesses.
        Each refused row (they are rare - capped by MAX_REJECT_PROBES) is
        retried alone inside a savepoint WITHOUT the conflict clause; the
        database then names the constraint and the colliding values itself,
        and the attempt is rolled back either way.
        """
        from psycopg2 import IntegrityError, errors as pg_errors
        by_cause = {}
        for row, sid in refused[:MAX_REJECT_PROBES]:
            try:
                with mute_logger('odoo.sql_db'), self.env.cr.savepoint():
                    self.env.cr.execute(
                        "INSERT INTO %s (%s) VALUES (%s)" % (
                            table, ', '.join(columns),
                            ', '.join(['%s'] * len(columns))),
                        tuple(row),
                    )
                    # It went in this time (the collision was with a row of
                    # the same batch, say) - still refused: keep behaviour
                    # identical and let the next run take it.
                    raise pg_errors.UniqueViolation()
            except IntegrityError as exc:
                diag = getattr(exc, 'diag', None)
                cause = (getattr(diag, 'message_detail', '')
                         or getattr(diag, 'constraint_name', '')
                         or str(exc).split('\n')[0])
                by_cause.setdefault(cause, []).append(sid)
            except Exception:
                _logger.warning("Could not probe refused %s row %s",
                                model, sid, exc_info=True)
        for cause, sids in by_cause.items():
            shown = ', '.join(self.env._("№%(num)s", num=x) for x in sids[:3])
            if len(sids) > 3:
                shown = self.env._(
                    "%(first)s and %(more)s more", first=shown,
                    more=len(sids) - 3)
            self.note_skip_reason(self.env._(
                "record(s) %(which)s were refused by the database: %(cause)s",
                which=shown, cause=cause,
            ), count=len(sids))
        left = len(refused) - MAX_REJECT_PROBES
        if left > 0:
            self.note_skip_reason(self.env._(
                "%(count)s more refused row(s) were not examined one by one",
                count=left,
            ), count=left)

    def _xml_id_name(self, model_prefix, source_id):
        """Name part of the external ID (without the module prefix).

        Carries the source identity so that records from different systems
        cannot collide - and so that the SAME system read from two places
        (a restored backup, then the live server) writes one set of ids.
        Format: rfid_import_{source_slug}_{model_prefix}_{source_id}
        """
        return f'{EXTERNAL_ID_PREFIX}{self.source_slug}_{model_prefix}_{source_id}'

    def _xml_id(self, model_prefix, source_id):
        """Full XML ID for ir.model.data.

        Format: __import__.rfid_import_{source_slug}_{model_prefix}_{source_id}
        """
        return f'{EXTERNAL_ID_MODULE}.{self._xml_id_name(model_prefix, source_id)}'

    def _get_target_id(self, model, source_id):
        """Get target ID from previously imported record.

        Returns:
            int: Target record ID, or None if skipped, or False if not found.
        """
        if model not in self.id_map:
            return False
        if source_id not in self.id_map[model]:
            return False
        return self.id_map[model][source_id]  # None=skipped, int=mapped

    def _set_target_id(self, model, source_id, target_id):
        """Store source → target ID mapping."""
        self.id_map.setdefault(model, {})[source_id] = target_id

    def _require_target_id(self, model, source_id, context_msg=''):
        """Get target ID or raise error if not found (fail hard).

        Args:
            model: Model name for lookup
            source_id: Source record ID (can be [id, name] tuple from M2O)
            context_msg: Additional context for error message

        Returns:
            int: Target record ID

        Raises:
            UserError: If mapping not found (indicates bug in previous phase)
        """
        if not source_id:
            return False
        # Handle M2O format [id, name]
        sid = source_id[0] if isinstance(source_id, (list, tuple)) else source_id
        target_id = self._get_target_id(model, sid)
        if target_id is None:
            # None = explicitly skipped by conflict resolution
            return False
        if not target_id:
            # Check ir.model.data as fallback
            target_id = self._resolve_from_imd(model, sid)
            if target_id:
                return target_id
            raise UserError(_(
                "Cannot map %(model)s ID=%(source_id)d to target. "
                "This indicates a bug in a previous import phase. %(context)s",
                model=model, source_id=sid, context=context_msg,
            ))
        return target_id

    def _resolve_from_imd(self, model, source_id):
        """Try to resolve target ID from ir.model.data."""
        prefix = model.replace('.', '_')
        name = self._xml_id_name(prefix, source_id)
        imd = self.env['ir.model.data'].sudo().search([
            ('module', '=', EXTERNAL_ID_MODULE),
            ('name', '=', name),
            ('model', '=', model),
        ], limit=1)
        if imd and imd.res_id:
            self._set_target_id(model, source_id, imd.res_id)
            return imd.res_id
        return False

    # ── Company mapping ───────────────────────────────────────

    def describe_unmatched_door(self, source_id):
        """One sentence from the SOURCE about a door we could not match.

        Read live at diagnosis time. Three protocols in a row said only
        "door N has no match here" and the operator had to guess which of
        three very different situations that was - the log has to carry the
        real picture by itself (owner's rule, 2026-08-15):

        - the door was DELETED on the other system -> the permission points at
          nothing and never will; skipping it is the correct final outcome;
        - the door belongs to a COMPANY not included in this transfer -> the
          operator decides: add the company, or accept the skip;
        - the door is in scope and still did not arrive -> a real defect in
          the hardware step, and only then is the row a genuine error.

        Returns (sentence, is_a_real_problem).
        """
        try:
            doors = self._search_read(
                'hr.rfid.door', [('id', '=', source_id)],
                ['name', 'controller_id'])
            if not doors:
                return self.env._(
                    "the other system no longer has door №%(num)s - the "
                    "permission points at a door deleted over there",
                    num=source_id,
                ), False
            door = doors[0]
            company_id = False
            ctrl_id = self._m2o_id(door.get('controller_id'))
            if ctrl_id:
                ctrls = self._search_read(
                    'hr.rfid.ctrl', [('id', '=', ctrl_id)], ['webstack_id'])
                ws_id = ctrls and self._m2o_id(ctrls[0].get('webstack_id'))
                if ws_id:
                    wss = self._search_read(
                        'hr.rfid.webstack', [('id', '=', ws_id)],
                        ['company_id'])
                    company_id = wss and self._m2o_id(wss[0].get('company_id'))
            elif self._has_model('cctv.camera'):
                cams = self._search_read(
                    'cctv.camera', [('door_id', '=', source_id)],
                    ['name', 'company_id'])
                if cams:
                    company_id = self._m2o_id(cams[0].get('company_id'))
            if company_id and company_id not in self.company_map:
                names = self._search_read(
                    'res.company', [('id', '=', company_id)], ['name'])
                return self.env._(
                    "door №%(num)s \"%(name)s\" belongs to company "
                    "\"%(company)s\", which is not included in this "
                    "transfer - add that company on the first page to bring "
                    "its doors",
                    num=source_id, name=door.get('name') or '?',
                    company=(names and names[0].get('name')) or company_id,
                ), False
            # In scope and still missing: before blaming the hardware step,
            # say what the TARGET side holds - the identity searched for, and
            # whether a door of the same name arrived under another identity.
            # Three live protocols dead-ended exactly here.
            expected = self._xml_id_name('hr_rfid_door', source_id)
            _logger.warning(
                "door %s is in scope but unmatched; searched %s.%s",
                source_id, EXTERNAL_ID_MODULE, expected)
            twin = self.env['hr.rfid.door'].sudo().with_context(
                active_test=False).search(
                [('name', '=', door.get('name'))], limit=1)
            if twin:
                return self.env._(
                    "door №%(num)s \"%(name)s\" is part of this transfer; a "
                    "door with the same name exists here (№%(target)s) but "
                    "under a different transfer identity, so they are not "
                    "recognised as one - send this protocol to support",
                    num=source_id, name=door.get('name') or '?',
                    target=twin.id,
                ), True
            return self.env._(
                "door №%(num)s \"%(name)s\" is part of this transfer and "
                "still did not arrive - look at the hardware step above",
                num=source_id, name=door.get('name') or '?',
            ), True
        except Exception:
            _logger.warning(
                "Could not ask the source about door %s while writing the "
                "protocol", source_id, exc_info=True)
            return self.env._(
                "door №%(num)s from the other system has no match here",
                num=source_id,
            ), True

    def _map_company(self, source_company_id):
        """Map source company ID to target company ID."""
        if not source_company_id:
            return False
        sid = source_company_id[0] if isinstance(source_company_id, (list, tuple)) else source_company_id
        target = self.company_map.get(sid, False)
        if not target:
            self.note_skip('res.company', sid)
        return target

    def _company_domain(self):
        """Return domain filter for source companies being imported."""
        source_ids = list(self.company_map.keys())
        if len(source_ids) == 1:
            return [('company_id', '=', source_ids[0])]
        return [('company_id', 'in', source_ids)]

    def _target_columns(self, model):
        """Real database columns of a target model.

        ``_fields`` also contains non-stored related/computed fields, which
        have NO column. Naming one in a raw INSERT raises UndefinedColumn and
        takes the whole bulk step down - e.g. v19 `hr.rfid.event.user` exposes
        `card_number` as a related field with no column of its own. Only the
        bulk (SQL) paths need this; the ORM paths legitimately write
        non-column fields such as Many2many.
        """
        return {
            name for name, field in self.env[model]._fields.items()
            if field.store and field.column_type
        }

    def _scoped_domain(self, path=''):
        """Domain restricting a model to the companies in scope.

        A model without its own ``company_id`` is attributed through the
        Many2one chain that owns it (``path``), e.g. ``'webstack_id'`` for
        system events or ``'employee_id'`` for attendance.

        WITHOUT this, a per-company run reads the WHOLE source table over
        XML-RPC and relies on a later ``continue`` to drop foreign rows -
        which silently leaks any row whose foreign key happens to be
        nullable (reproduced on hr.rfid.zone: importing a tenant that owns
        zero zones created all nine zones of the other tenants).

        Note: a dotted domain compiles to an EXISTS sub-query, so rows whose
        link is NULL do NOT match. That is intended - a row with no owner
        cannot be attributed to a company - but it means the caller must
        add an explicit branch when NULL links are legitimately in scope
        (see ``_import_system_events``).
        """
        field = '%s.company_id' % path if path else 'company_id'
        return [(field, 'in', self._source_company_ids())]

    def _source_company_ids(self):
        """Return list of source company IDs being imported."""
        return list(self.company_map.keys())

    # ── Utility ───────────────────────────────────────────────

    @staticmethod
    def _m2o_id(value):
        """Bare id of a Many2one value, whichever shape the read returned.

        Reads run with load='_classic_write', which hands a Many2one back as a
        bare integer - and every ``value[0]`` written for the [id, name] shape
        then dies with "'int' object is not subscriptable". It took the People
        phase of a live migration with it, and cards and memberships cascaded
        after. One shape-tolerant accessor, used everywhere, instead of four
        copies of the same indexing.
        """
        if isinstance(value, (list, tuple)):
            return value[0] if value else False
        return value or False

    def _map_m2o(self, model, source_val):
        """Map Many2one field: [id, name] or id → target_id or False.

        Does NOT fail hard - use _require_target_id for mandatory fields.

        Falls back to the external ID, exactly as ``_require_target_id`` does. The
        in-memory map does not survive the process: a transfer that continues
        in a later pass starts with it empty, every link resolves to False and
        the row is counted as skipped. The protocol then reads as a clean run
        while whole phases of relations are missing.
        """
        if not source_val:
            return False
        source_id = source_val[0] if isinstance(source_val, (list, tuple)) else source_val
        target_id = self._get_target_id(model, source_id)
        if target_id is None:
            # Deliberately skipped by the operator - said so in the protocol.
            self.note_skip_reason(self.env._(
                "left out by the operator's own choice"))
            return False
        if not target_id:
            target_id = self._resolve_from_imd(model, source_id)
        if not target_id:
            self.note_skip(model, source_id)
        return target_id or False

    def _map_m2m(self, model, source_ids):
        """Map Many2many field: [id1, id2, ...] → [(6, 0, [target_ids])]."""
        if not source_ids:
            return [(6, 0, [])]
        # One query for the whole list rather than one per miss.
        self.prefetch_external_ids(model, [
            s for s in source_ids if not self._get_target_id(model, s)])
        target_ids = []
        for sid in source_ids:
            tid = self._get_target_id(model, sid)
            if tid:  # skip None (skipped) and False (not found)
                target_ids.append(tid)
        return [(6, 0, target_ids)]

    def _common_fields(self, source_model, target_model):
        """Get fields that exist in both source and target.

        Returns set of field names present in both, excluding
        computed/readonly/relational metadata fields.
        """
        source_fields = self._get_source_fields(source_model)
        target_fields = set(self.env[target_model]._fields.keys())
        # Exclude auto-generated fields
        exclude = {
            'id', '__last_update', 'create_uid', 'create_date',
            'write_uid', 'write_date', 'display_name',
            'message_follower_ids', 'message_ids', 'message_main_attachment_id',
            'activity_ids', 'activity_state', 'activity_summary',
            'activity_type_id', 'activity_date_deadline',
            'activity_user_id', 'activity_exception_decoration',
            'activity_exception_icon', 'activity_type_icon',
            'has_message', 'message_attachment_count',
            'message_has_error', 'message_has_error_counter',
            'message_has_sms_error', 'message_is_follower',
            'message_needaction', 'message_needaction_counter',
            'message_partner_ids', 'website_message_ids',
        }
        return (set(source_fields.keys()) & target_fields) - exclude

    def note_skip(self, model, source_id, count=1):
        """Remember why a row was left behind, for the current protocol line.

        Tolerant of test doubles built without __init__ - the same convention
        _can_read_fields already follows for rpc_models.
        """
        pending = getattr(self, '_pending_skips', None)
        if pending is None:
            pending = self._pending_skips = {}
        key = (model, source_id)
        pending[key] = pending.get(key, 0) + count

    def note_skip_reason(self, text, count=1):
        """Free-text variant for causes that are not a missing record."""
        pending = getattr(self, '_pending_skips', None)
        if pending is None:
            pending = self._pending_skips = {}
        key = (None, text)
        pending[key] = pending.get(key, 0) + count

    def _drain_skip_summary(self):
        """The reasons collected since the last line, as one sentence."""
        pending = getattr(self, '_pending_skips', {})
        self._pending_skips = {}
        if not pending:
            return ''
        parts = []
        for (model, ident), count in sorted(
                pending.items(), key=lambda kv: -kv[1])[:8]:
            if model is None:
                what = ident
            else:
                label = (self.env[model]._description
                         if model in self.env else model)
                what = self.env._(
                    "%(kind)s №%(num)s from the other system has no match "
                    "here", kind=label, num=ident)
            parts.append(
                self.env._("%(what)s - %(count)s row(s)",
                           what=what, count=count))
        more = len(pending) - 8
        if more > 0:
            parts.append(self.env._("and %(more)s more reason(s)", more=more))
        return "; ".join(parts)

    def _make_result(self, model, source_count, imported_count, linked_count=0,
                     skipped_count=0, duration=0, status='done', error='',
                     rejected_count=0):
        """One row of the import protocol.

        The counts must add up: a source row is imported, linked to an
        existing target record, skipped (out of scope / unresolvable
        relation) or rejected (the database refused it). An uncounted
        ``continue`` makes "no data in the source" indistinguishable from
        "every row was dropped" - the operator cannot tell a clean run from
        a broken one.
        """
        reasons = self._drain_skip_summary()
        if reasons:
            error = ("%s | %s" % (error, reasons)) if error else reasons
        landed = imported_count + linked_count
        if status == 'done' and source_count and not landed:
            # The source holds records of this kind and not one arrived. That
            # is not "there was nothing to move" - it is "all of it fell
            # through", and from the numbers alone the two look identical.
            # Calling this done is how a broken transfer reads as a clean one.
            status = 'error'
            error = error or self.env._(
                "The other system holds %(count)s record(s) of this kind and "
                "none of them came across. Look at the step before this one - "
                "what these records point at is probably missing.",
                count=source_count,
            )
        elif status == 'done' and source_count and landed < source_count:
            status = 'partial'
        return {
            'model': model,
            'source_count': source_count,
            'imported_count': imported_count,
            'linked_count': linked_count,
            'skipped_count': skipped_count,
            'rejected_count': rejected_count,
            'duration': duration,
            'status': status,
            'error': error,
        }

    def _log(self, msg, *args):
        """Log a message."""
        if args:
            _logger.info(msg, *args)
        else:
            _logger.info(msg)
