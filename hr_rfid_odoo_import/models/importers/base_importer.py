# -*- coding: utf-8 -*-
import logging
import time
import xmlrpc.client

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

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
                 company_map, options):
        self.env = env
        # XML-RPC connection (source — read only)
        self.source_url = source_url
        self.source_db = source_db
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

    # ── Source reading (XML-RPC) ──────────────────────────────

    def _search_read(self, model, domain, fields, order='id asc', limit=0):
        """Read records from source via XML-RPC."""
        kwargs = {'fields': fields, 'order': order}
        if limit:
            kwargs['limit'] = limit
        return self.rpc_models.execute_kw(
            self.source_db, self.source_uid, self.source_password,
            model, 'search_read', [domain], kwargs
        )

    def _read_all(self, model, domain, fields, batch_size=1000):
        """ID-based pagination for large datasets."""
        all_records = []
        last_id = 0
        while True:
            batch_domain = [('id', '>', last_id)] + domain
            records = self._search_read(
                model, batch_domain, fields, order='id asc', limit=batch_size
            )
            if not records:
                break
            all_records.extend(records)
            last_id = records[-1]['id']
        return all_records

    def _search_count(self, model, domain):
        """Count records in source."""
        return self.rpc_models.execute_kw(
            self.source_db, self.source_uid, self.source_password,
            model, 'search_count', [domain]
        )

    def _has_field(self, model, field_name):
        """Check if field exists in source model via fields_get()."""
        if model not in self._field_cache:
            self._field_cache[model] = self.rpc_models.execute_kw(
                self.source_db, self.source_uid, self.source_password,
                model, 'fields_get', [],
                {'attributes': ['type', 'relation', 'required']}
            )
        return field_name in self._field_cache[model]

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
        """Use Odoo 19 _load_records() for batch create + XML ID.

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

    def _try_load_records(self, model_name, data_list):
        """Load records with savepoint — skip silently on failure.

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
            return self.env[model_name]

    def _direct_sql_insert(self, table, columns, rows, batch_size=5000):
        """Direct SQL INSERT into target DB — bypass ORM.

        Uses execute_values for performance. Skips duplicates via ON CONFLICT.
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

    # ── ID Mapping ────────────────────────────────────────────

    def _xml_id(self, model_prefix, source_id):
        """Generate XML ID for ir.model.data.

        Includes source_db slug to prevent collisions between different sources.
        Format: __import__.rfid_import_{db_slug}_{model_prefix}_{source_id}
        """
        db_slug = self.source_db.replace('-', '_').replace('.', '_')
        return f'__import__.rfid_import_{db_slug}_{model_prefix}_{source_id}'

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
        xml_id = self._xml_id(prefix, source_id)
        # xml_id format: __import__.rfid_import_db_slug_prefix_id
        module = '__import__'
        name = xml_id.split('.', 1)[1] if '.' in xml_id else xml_id
        imd = self.env['ir.model.data'].sudo().search([
            ('module', '=', module),
            ('name', '=', name),
            ('model', '=', model),
        ], limit=1)
        if imd and imd.res_id:
            self._set_target_id(model, source_id, imd.res_id)
            return imd.res_id
        return False

    # ── Company mapping ───────────────────────────────────────

    def _map_company(self, source_company_id):
        """Map source company ID to target company ID."""
        if not source_company_id:
            return False
        sid = source_company_id[0] if isinstance(source_company_id, (list, tuple)) else source_company_id
        return self.company_map.get(sid, False)

    def _company_domain(self):
        """Return domain filter for source companies being imported."""
        source_ids = list(self.company_map.keys())
        if len(source_ids) == 1:
            return [('company_id', '=', source_ids[0])]
        return [('company_id', 'in', source_ids)]

    def _source_company_ids(self):
        """Return list of source company IDs being imported."""
        return list(self.company_map.keys())

    # ── Utility ───────────────────────────────────────────────

    def _map_m2o(self, model, source_val):
        """Map Many2one field: [id, name] or id → target_id or False.

        Does NOT fail hard — use _require_target_id for mandatory fields.
        """
        if not source_val:
            return False
        source_id = source_val[0] if isinstance(source_val, (list, tuple)) else source_val
        target_id = self._get_target_id(model, source_id)
        if target_id is None:
            return False  # skipped
        return target_id or False

    def _map_m2m(self, model, source_ids):
        """Map Many2many field: [id1, id2, ...] → [(6, 0, [target_ids])]."""
        if not source_ids:
            return [(6, 0, [])]
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

    def _log(self, msg, *args):
        """Log a message."""
        if args:
            _logger.info(msg, *args)
        else:
            _logger.info(msg)
