## How an imported record is recognised again

Every record this wizard creates is registered in Odoo's own external-ID
metadata (`ir.model.data`), against the cloud record it came from. That register
is what makes a second run find the first run's work instead of creating it
again - identity is the SOURCE ID, never a name, a code or a card number.

### The name

```
__import__.rfid_import_{old_cloud_pc|old_cloud_ss}_{target_model}_{source_table}_{source_id}
```

built by `_xml_id_name(model, source_ref)`; `source_ref` is
`{SRC_*}_{cloud id}`. The target model is part of the name because one cloud
holder can land as BOTH an `hr.employee` and a `res.partner`, and both have to
be recognised separately. The cloud is part of it because the two clouds number
their records independently - `tests/test_import_idempotency.py::test_the_two_clouds_never_share_an_external_id`
pins exactly that.

### Helpers on `hr.rfid.old.cloud.import.wiz`

| Method | Does |
|---|---|
| `_source_slug()` | The identity of the cloud this run reads, from `url_domain` through `SOURCE_SLUG_BY_DOMAIN`. |
| `_xml_id_name(model, source_ref)` / `_xml_id(model, source_ref)` | The name, and the full external ID. |
| `_find_imported(model, source_ref)` | The record an earlier run created for this source record, or an empty recordset. `env.ref(..., raise_if_not_found=False)` - which is NOT filtered by `active`, so an archived record is still recognised. |
| `_mark_imported(record, source_ref)` | Registers a freshly created record. Called on EVERY create path: customer, contact, department, employee, card, placeholder access group, access-group membership. |
| `_already_imported_user_ids()` | The cloud user ids an earlier run brought in, so they are not offered for import again. Looks under both `hr.employee` and `res.partner` prefixes; the `SRC_USER` token keeps customers (also `res.partner`) out. |

### Memberships have TWO guards

`_add_ag_membership` skips a membership when its external ID exists **or** when
the (person, access group) pair is already there. The second guard is not
redundant: memberships created before this module wrote external IDs at all
carry nothing that says they came from here, and without it the first run after
the change would duplicate every one of them.

### Records marked by an earlier version

Versions before 19.0.1.2.0 registered their work under `__export__` with names
like `old_cloud_u_id_7`. Those names are NOT read any more, and there is no
conversion step: on a database imported with an older version, the holders
concerned are offered again and accepted as new. A site in that position should
be checked before a repeat import is run.

### Tests

`tests/test_import_idempotency.py` - a second run creates no second employee or
contact, gives no access group twice (by external ID, and by the pair guard for
memberships that predate it), reuses the placeholder group, keeps one badge as
one card, leaves a door with exactly one way in, does not hand a visitor the
same badge twice, and keeps the two clouds apart. The cloud HTTP calls are
patched out, so nothing goes to the network.

## What the constants of the import mean

- **`LEDGER_MODULE`** = `'__import__'` - the `ir.model.data` module every record
  created here is registered under. It is what core's own `BaseModel.load()`
  writes for imported rows, so a second run recognises the first run's work
  exactly the way core would.
- **`SOURCE_SLUG_BY_DOMAIN`** = `{'pc': 'old_cloud_pc', 'ss': 'old_cloud_ss'}`,
  **`DEFAULT_SOURCE_DOMAIN`** = `'pc'` - the source identity inside the external
  ID. The two legacy clouds (my.polimex.online and schoolsafety.online) are
  separate installations with their own record numbering, so each gets its own
  slug and holder 7 on one is never taken for holder 7 on the other. An
  unrecognised domain falls back to `old_cloud_{domain}`.
- **`SRC_USER`/`SRC_COMPANY`/`SRC_DEPARTMENT`/`SRC_ACCESS_GROUP`/`SRC_TAG`/`SRC_AG_USER`/`SRC_PLACEHOLDER_AG`**
  = `'u'`/`'c'`/`'d'`/`'ag'`/`'tag'`/`'agu'`/`'placeholder'` - source TABLE
  tokens. Holders and customers both land in `res.partner`, so the reference has
  to say which of them an id came from.
