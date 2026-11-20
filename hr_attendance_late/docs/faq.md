## The legal rates (`hr.legal.rate`)

`_get_rate(code, date, company_id=None)`:
Returns the coefficient for ``code`` effective on ``date``. Company row
first, then global - NOT one ordered query, because in PostgreSQL
`ORDER BY company_id DESC` puts NULL (global) first and a global row would
shadow a company override. Missing = `0.0` (no premium), never a guessed
`1.0`.


### Correcting a rate vs. superseding it

Two operations that look alike and must not be confused:

- **The law changed** -> CREATE a new row with the new `date_from`. The lookup
  takes the latest `date_from` on or before the worked day, so historical
  periods keep their historical coefficient.
- **The stored figure is wrong** -> WRITE on the existing row. This must NOT
  leave a second dated row for the same code: two rows effective on the same
  day make the lookup depend on which one wins. The partial unique indexes stop
  the exact duplicate (`(code, date_from, company_id) WHERE company_id IS NOT
  NULL` and `(code, date_from) WHERE company_id IS NULL` - a plain 3-column
  UNIQUE would NOT stop duplicate GLOBAL rows, because PostgreSQL treats NULL
  as distinct), and `test_legal_rate_edit_tour` asserts the count after an
  inline correction.

`create` / `write` / `unlink` all call `self.env.registry.clear_cache()`,
because the lookup is `ormcache`d on (code, date, company_id).

### Presentation, and what a test may assert

`value` carries `digits=(16, 4)`, so it renders with four decimals AND with the
decimal mark of the user's language: **1,8500** in Bulgarian, **1.8500** in
English. A customer database typically has only `bg_BG` installed, and a
fixture that writes `admin.lang = 'en_US'` does NOT change that - core
`res.users.context_get` drops a language that is not installed and falls back
to the company's. So a UI test must assert the VALUE, not its rendering:
`:contains(/1[.,]85/)`, scoped to the edited row
(`.o_data_row:has(.o_data_cell[name='code']:contains(zz_tour_rate))`).

The tour `test_legal_rate_edit_tour` (`tests/test_tours.py`): an HR manager
corrects a wrong coefficient in the list, sees the corrected value on that rate
afterwards, and the correction lands on the rate they opened - without leaving
a second row for that code. It asserts both halves: `rate.value == 1.85` and
`search_count([('code', '=', 'zz_tour_rate')]) == 1`.
