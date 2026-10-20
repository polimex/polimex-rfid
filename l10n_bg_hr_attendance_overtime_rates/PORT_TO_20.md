# Porting to Odoo 20 - the anchors that change

Checked 20.10.2026 against the local 20.0 tree.

## The holiday generator (`models/res_company.py`, `_generate_bg_public_holidays`)

A generated holiday must be the whole day, midnight to midnight, where the
company works. In 19 that takes two steps that both disappear in 20:

| What | Odoo 19 (here) | Odoo 20 |
|---|---|---|
| Zone of the day | `resource.calendar.tz` of the company's working schedule | the schedule has no zone (`resource/models/resource_calendar.py`, no `tz` field); the company has one (`resource/models/res_company.py:15`) |
| Who moves the day there | core, on create: `hr_holidays/models/resource.py:123-139` (`_prepare_public_holidays_values`) reads the given bounds as the day in the USER's zone and moves them to the schedule's zone, so the generator hands the day over in `env.user.tz` | nobody: `hr_holidays/models/resource_calendar_leaves.py:117-121` stores what it is given |

In the port: hand the day over directly as midnight to midnight in
`company.tz` (UTC when empty), and check for days already there in the same
zone. The tests that pin this (`tests/test_public_holidays.py`,
`test_a_holiday_is_the_whole_day_where_the_company_works`) keep their
statement - an officer in Sofia, one elsewhere, and the cron all produce the
Sofia day - and set `company.tz` instead of the schedule's zone.

## Access rights

`security/ir.model.access.csv` becomes `security/ir.access.csv` (`ir.access`
replaces `ir.model.access`, skill `odoo19-gotchas`).
