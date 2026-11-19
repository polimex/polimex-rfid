# Porting to Odoo 20 - the anchors that change

Checked 20.10.2026 against the local 20.0 tree; the holiday section again on
19.11.2026.

## The holiday generator (`models/res_company.py`, `_generate_bg_public_holidays`)

An official holiday is a public holiday of the company with no working
schedule, so it holds for every schedule of the company. It is the whole day,
midnight to midnight, where the company works.

| What | Odoo 19 (here) | Odoo 20 |
|---|---|---|
| A holiday with no schedule holds for every schedule of its company | `resource/models/resource_calendar.py:515` (`calendar_id in [False] + schedules`), company guard `:535` | the same, `:477` and `:506` |
| Two public holidays over the same hours of one company are refused | `hr_holidays/models/resource.py`, `_check_compare_dates` | `hr_holidays/models/resource_calendar_leaves.py:22-40` |
| Zone of the day | `resource.calendar.tz` of the company's working schedule | the schedule has no zone (`resource/models/resource_calendar.py`, no `tz` field); the company has one (`resource/models/res_company.py:15`) |
| Who moves the day | nobody for a holiday with no schedule: `_prepare_public_holidays_values` moves only one tied to a schedule, so the generator hands the day over in the schedule's zone | nobody: `hr_holidays/models/resource_calendar_leaves.py:117-121` stores what it is given |

In the port: hand the day over as midnight to midnight in `company.tz` (UTC
when empty), and check for days already there in the same zone. The tests
(`tests/test_public_holidays.py`) keep their statements and set `company.tz`
instead of the schedule's zone.

The upgrade step of 19.0.1.0.6 (`_hand_bg_public_holidays_to_everyone`) has no
place in 20: a database reaches 20 after it.

## Access rights

`security/ir.model.access.csv` becomes `security/ir.access.csv` (`ir.access`
replaces `ir.model.access`, skill `odoo19-gotchas`).
