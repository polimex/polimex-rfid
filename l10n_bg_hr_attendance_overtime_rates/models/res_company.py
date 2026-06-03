# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
import logging
from datetime import date, datetime, time, timedelta

from dateutil.easter import easter, EASTER_ORTHODOX

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Fixed Bulgarian public holidays (Labour Code art. 154) as (month, day, name).
# The moving Orthodox-Easter cluster (Good Friday / Holy Saturday / Easter
# Monday) is computed per year — Easter Sunday itself is already a weekend.
BG_FIXED_HOLIDAYS = [
    (1, 1, "New Year's Day"),
    (3, 3, "Liberation Day"),
    (5, 1, "Labour Day"),
    (5, 6, "St. George's Day / Day of Valour"),
    (5, 24, "Day of Bulgarian Education and Culture"),
    (9, 6, "Unification Day"),
    (9, 22, "Independence Day"),
    (12, 24, "Christmas Eve"),
    (12, 25, "Christmas Day"),
    (12, 26, "Second Day of Christmas"),
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _generate_bg_public_holidays(self, year):
        """Create global Public Holiday entries for a calendar year.

        Public holidays are global ``resource.calendar.leaves`` (no resource,
        ``time_type='leave'``) on the company's working calendar — the same
        records Time Off → Public Holidays manages and that the cost
        calculation reads to tell a rest day from an official holiday.

        Idempotent: a holiday already present for the company/calendar on a
        given day is skipped, so it is safe to re-run or schedule yearly.
        Returns the created ``resource.calendar.leaves`` recordset.
        """
        Leave = self.env['resource.calendar.leaves']
        created = Leave.browse()
        for company in self:
            calendar = company.resource_calendar_id
            if not calendar:
                _logger.warning(
                    "Company %s has no working calendar; skipping BG public "
                    "holidays generation.", company.display_name)
                continue

            # Fixed dates + moving Orthodox-Easter cluster, resolved to dates.
            easter_sunday = easter(year, method=EASTER_ORTHODOX)
            days = [(date(year, m, d), name) for (m, d, name) in BG_FIXED_HOLIDAYS]
            days += [
                (easter_sunday - timedelta(days=2), "Good Friday"),
                (easter_sunday - timedelta(days=1), "Holy Saturday"),
                (easter_sunday + timedelta(days=1), "Easter Monday"),
            ]

            # Prefetch the global leaves overlapping the target year once, so
            # the idempotency check is in-memory instead of one query per day.
            year_from = datetime(year, 1, 1, 0, 0, 0)
            year_to = datetime(year, 12, 31, 23, 59, 59)
            existing = Leave.search([
                ('calendar_id', '=', calendar.id),
                ('resource_id', '=', False),
                ('date_from', '<=', year_to),
                ('date_to', '>=', year_from),
            ])
            existing_intervals = [(r.date_from, r.date_to) for r in existing]

            vals_list = []
            for day, name in days:
                date_from = datetime.combine(day, time.min)
                date_to = datetime.combine(day, time.max)
                # Day already covered by an existing global leave: skip.
                if any(start <= date_to and stop >= date_from
                       for start, stop in existing_intervals):
                    continue
                existing_intervals.append((date_from, date_to))
                vals_list.append({
                    'name': name,
                    'calendar_id': calendar.id,
                    'company_id': company.id,
                    'resource_id': False,
                    'date_from': date_from,
                    'date_to': date_to,
                    'time_type': 'leave',
                })
            created |= Leave.create(vals_list)
        return created

    @api.model
    def _cron_generate_bg_public_holidays(self):
        """Yearly cron: seed next year's BG public holidays for every company
        that already has at least one (i.e. opted in to managed holidays)."""
        next_year = fields.Date.context_today(self).year + 1
        Leave = self.env['resource.calendar.leaves']
        for company in self.env['res.company'].search([]):
            cal = company.resource_calendar_id
            if not cal:
                continue
            has_any = Leave.search_count([
                ('calendar_id', '=', cal.id),
                ('resource_id', '=', False),
            ])
            if has_any:
                company._generate_bg_public_holidays(next_year)
