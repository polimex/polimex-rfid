## How an imported record is recognised again

Every record this wizard creates is registered in Odoo's own external-ID
metadata (`ir.model.data`), against the Andromeda record it came from. That
register is what makes a second run find the first run's work instead of
creating it again - identity is the SOURCE ID, never a name, a code or a card
number.

### The name

```
__import__.rfid_import_andromeda_{target_model}_{source_table}_{source_id}
```

built by `_xml_id_name(model, source_ref)`; `source_ref` is
`{SRC_*}_{andromeda id}`. The target model is part of the name because one
Andromeda user can land as BOTH an `hr.employee` and a `res.partner`, and both
have to be recognised separately.

### Helpers on `hr.rfid.andromeda.import.wiz`

| Method | Does |
|---|---|
| `_source_slug()` | The source identity (`SOURCE_SLUG`). Override it if an installation ever needs to keep two Andromeda sources apart. |
| `_xml_id_name(model, source_ref)` / `_xml_id(model, source_ref)` | The name, and the full external ID. |
| `_find_imported(model, source_ref)` | The record an earlier run created for this source record, or an empty recordset. `env.ref(..., raise_if_not_found=False)`. |
| `_mark_imported(record, source_ref)` | Registers a freshly created record. Called on EVERY create path: company, contact, department, employee, card, placeholder access group, access-group membership. |
| `_already_imported_user_ids()` | The Andromeda user ids an earlier run brought in, so they are not offered for import again. Looks under both `hr.employee` and `res.partner` prefixes; the `SRC_USER` token keeps companies (also `res.partner`) out. |

### Memberships have TWO guards

`_add_ag_membership` skips a membership when its external ID exists **or** when
the (person, access group) pair is already there. The second guard is not
redundant: memberships created before this module wrote external IDs at all
carry nothing that says they came from here, and without it the first run after
the change would duplicate every one of them.

### Placeholder access group

A department with no default access group gets a placeholder, registered
against the source access group that made it necessary
(`SRC_PLACEHOLDER_AG`), so a second run reuses it instead of leaving another
one behind.

### Records marked by an earlier version

Versions before 19.0.1.3.0 registered their work under `__export__` with names
like `andromeda_u_id_7`. Those names are NOT read any more, and there is no
conversion step: on a database imported with an older version, the users
concerned are offered again and accepted as new. A site in that position should
be checked before a repeat import is run.

### Tests

`tests/test_import_wizard.py` - the create paths and their repeats (company,
department, employee, contact), an access group is not given twice (by external
ID, and by the pair guard for memberships that predate it), the placeholder is
reused, one badge stays one card, a door keeps exactly one way in, a visitor's
badge is not handed out twice, and a card switched off in Andromeda is not
reissued as a second working copy. The Firebird calls are patched out
(`do_fb_sql_context`), so no server is needed - and none is needed for any of
this logic.

## What the constants of the import mean

- **`LEDGER_MODULE`** = `'__import__'` - the `ir.model.data` module every record
  created here is registered under. It is what core's own `BaseModel.load()`
  writes for imported rows, so a second run recognises the first run's work
  exactly the way core would.
- **`SOURCE_SLUG`** = `'andromeda'` - the source identity inside the external
  ID. One slug for every Andromeda source: the Firebird connection exposes no
  stable installation identifier (the IP can change between runs and the
  database path is the same on every default install).
- **`SRC_USER`/`SRC_COMPANY`/`SRC_DEPARTMENT`/`SRC_ACCESS_GROUP`/`SRC_TAG`/`SRC_AG_USER`/`SRC_PLACEHOLDER_AG`**
  = `'u'`/`'c'`/`'d'`/`'ag'`/`'tag'`/`'agu'`/`'placeholder'` - source TABLE
  tokens. USERS and COMPANY both land in `res.partner`, so the reference has to
  say which Andromeda table an id came from, or user 7 and company 7 are the
  same record.
