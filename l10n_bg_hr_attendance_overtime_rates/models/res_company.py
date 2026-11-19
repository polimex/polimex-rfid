# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
import logging
from datetime import date, datetime, time, timedelta

from dateutil.easter import easter, EASTER_ORTHODOX
from pytz import timezone, utc

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Fixed Bulgarian public holidays (Labour Code art. 154) as (month, day, name).
# The moving Orthodox-Easter cluster (Good Friday / Holy Saturday / Easter
# Monday) is computed per year - Easter Sunday itself is already a weekend.
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

# The longest a single holiday lasts: a whole day, its last second included.
ONE_DAY = timedelta(days=1)


def _bg_public_holiday_days(year):
    """The official days of that year as (date, name): the fixed dates and the
    moving Orthodox-Easter cluster."""
    easter_sunday = easter(year, method=EASTER_ORTHODOX)
    days = [(date(year, m, d), name) for (m, d, name) in BG_FIXED_HOLIDAYS]
    days += [
        (easter_sunday - timedelta(days=2), "Good Friday"),
        (easter_sunday - timedelta(days=1), "Holy Saturday"),
        (easter_sunday + timedelta(days=1), "Easter Monday"),
    ]
    return days


def _day_bounds(day, tz):
    """A whole day in that zone, its first and last moment, as stored (naive UTC)."""
    start = tz.localize(datetime.combine(day, time.min))
    stop = tz.localize(datetime.combine(day, time.max))
    return (
        start.astimezone(utc).replace(tzinfo=None),
        stop.astimezone(utc).replace(tzinfo=None),
    )


def _overlap(a_from, a_to, b_from, b_to):
    """Two stretches of time share at least a moment."""
    return a_from <= b_to and a_to >= b_from


class ResCompany(models.Model):
    _inherit = "res.company"

    def _bg_holiday_zone(self):
        """The zone the company's days run in: its working schedule's, else
        the company's own address, else UTC."""
        self.ensure_one()
        return timezone(self.resource_calendar_id.tz or self.partner_id.tz or "UTC")

    @api.model
    def _bg_companies(self):
        """The companies in Bulgaria - by the country of their address, the way
        core's localisations tell their companies apart."""
        return self.search([("partner_id.country_id.code", "=", "BG")])

    def _bg_public_holidays_domain(self, year):
        """The company's public holidays that overlap that year."""
        self.ensure_one()
        zone = self._bg_holiday_zone()
        return [
            ("company_id", "=", self.id),
            ("resource_id", "=", False),
            ("date_from", "<=", _day_bounds(date(year, 12, 31), zone)[1]),
            ("date_to", ">=", _day_bounds(date(year, 1, 1), zone)[0]),
        ]

    def _generate_bg_public_holidays(self, year):
        """Create the official Bulgarian public holidays of a calendar year.

        An official holiday is a day off for everybody in the company, whatever
        working schedule a person is on. So it is a Public Holiday with no
        working schedule and no resource - the form core's Time Off -> Public
        Holidays makes when "Working Hours" is left empty, and the one core
        applies to every schedule (resource/models/resource_calendar.py:515,
        ``calendar_id in [False] + schedules``) of the company it belongs to
        (the same file, :535).

        The day runs midnight to midnight in the zone the company works in
        (_bg_holiday_zone) - what every daily figure reads. Core moves the
        bounds it is given only for a holiday tied to a schedule
        (hr_holidays/models/resource.py, _prepare_public_holidays_values), so
        these are stored as given, whoever runs this: an officer in Sofia, one
        elsewhere, or the yearly cron that has no zone at all.

        Core refuses two public holidays over the same hours of one company,
        for everyone or for one schedule (hr_holidays/models/resource.py,
        _check_compare_dates). A day that already holds one is left as it is,
        so re-running is safe and a day the company entered by hand stays; the
        wizard lists the whole year, so the holiday that holds such a day is in
        front of the person who runs it.
        Returns the created ``resource.calendar.leaves`` recordset.
        """
        created = self.env["resource.calendar.leaves"]
        for company in self:
            Leave = self.env["resource.calendar.leaves"].with_company(company)
            zone = company._bg_holiday_zone()

            # The company's public holidays overlapping the year, read once so
            # the check per day is in memory.
            existing = Leave.search(company._bg_public_holidays_domain(year))
            held = [(r.date_from, r.date_to, r.name) for r in existing]

            vals_list = []
            for day, name in _bg_public_holiday_days(year):
                date_from, date_to = _day_bounds(day, zone)
                holding = next(
                    (
                        other
                        for start, stop, other in held
                        if _overlap(start, stop, date_from, date_to)
                    ),
                    None,
                )
                if holding is not None:
                    _logger.info(
                        "%s (%s) of company %s is not added: the public holiday "
                        "%s already covers it.",
                        name,
                        day,
                        company.display_name,
                        holding,
                    )
                    continue
                held.append((date_from, date_to, name))
                vals_list.append(
                    {
                        "name": name,
                        "company_id": company.id,
                        "calendar_id": False,
                        "resource_id": False,
                        "date_from": date_from,
                        "date_to": date_to,
                        "time_type": "leave",
                    }
                )
            created |= Leave.create(vals_list)
        return created

    @api.model
    def _hand_bg_public_holidays_to_everyone(self):
        """Make the official days held for one working schedule hold for
        everybody in the company, from today on.

        Before 19.0.1.0.6 the generator tied every official day to the
        company's working schedule of the moment, so a person on any other
        schedule (shifts, part time, a night schedule) worked through the
        holiday in every daily figure and in pay. For every company in
        Bulgaria, a public holiday tied to one of its schedules that is one
        official day - it begins on that day in the schedule's zone and lasts
        no longer than a day (the versions before the zone fix made it from
        midnight UTC, 02:00 in Sofia) - is released from the schedule; so are
        the days left on a schedule the company no longer uses as its main
        one.

        Left as they are, each logged for a person to settle:
        - a day another public holiday of the company overlaps (core refuses
          the overlap);
        - a day whose release core refuses while it counts the time off on it
          again (hr_holidays/models/resource.py, write -> _reevaluate_leaves);
          one such day does not stop the others or the upgrade.
        Not touched: days already over (their time off and pay are settled),
        closures of several days, holidays on any other date, and a company
        abroad. Returns the released records.
        """
        released = self.env["resource.calendar.leaves"]
        now = fields.Datetime.now()
        for company in self._bg_companies():
            Leave = self.env["resource.calendar.leaves"].with_company(company)
            company_released = Leave
            company_holidays = Leave.search(
                [
                    ("company_id", "=", company.id),
                    ("resource_id", "=", False),
                ]
            )
            official = {}
            for leave in company_holidays:
                if (
                    not leave.calendar_id
                    or leave.time_type != "leave"
                    or leave.date_to < now
                ):
                    continue
                zone = timezone(leave.calendar_id.tz or "UTC")
                day = utc.localize(leave.date_from).astimezone(zone).date()
                if day.year not in official:
                    official[day.year] = {
                        d for d, _name in _bg_public_holiday_days(day.year)
                    }
                if (
                    leave.date_to - leave.date_from > ONE_DAY
                    or day not in official[day.year]
                ):
                    continue
                schedule = leave.calendar_id.display_name
                if any(
                    _overlap(
                        leave.date_from, leave.date_to, other.date_from, other.date_to
                    )
                    for other in company_holidays - leave
                ):
                    _logger.warning(
                        "Public holiday %s (%s) of company %s stays on schedule %s: "
                        "another public holiday of the company covers the same "
                        "hours.",
                        leave.name,
                        day,
                        company.display_name,
                        schedule,
                    )
                    continue
                try:
                    with self.env.cr.savepoint():
                        leave.write({"calendar_id": False})
                except UserError as error:
                    _logger.warning(
                        "Public holiday %s (%s) of company %s stays on schedule %s: "
                        "the time off on it could not be counted again: %s",
                        leave.name,
                        day,
                        company.display_name,
                        schedule,
                        error,
                    )
                    continue
                company_released |= leave
            if company_released:
                _logger.info(
                    "%s official public holidays of company %s now hold for every "
                    "working schedule.",
                    len(company_released),
                    company.display_name,
                )
            released |= company_released
        return released

    @api.model
    def _cron_generate_bg_public_holidays(self):
        """Yearly cron: seed next year's official days for every company in
        Bulgaria that keeps public holidays at all.

        The country is the company's own (the way core's localisations tell
        their companies apart): a company elsewhere in the same database keeps
        its own holidays and never receives the Bulgarian ones.
        """
        next_year = fields.Date.context_today(self).year + 1
        Leave = self.env["resource.calendar.leaves"]
        for company in self._bg_companies():
            if Leave.search_count(
                [
                    ("company_id", "=", company.id),
                    ("resource_id", "=", False),
                ],
                limit=1,
            ):
                company._generate_bg_public_holidays(next_year)
