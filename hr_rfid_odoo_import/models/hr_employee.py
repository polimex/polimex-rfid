# -*- coding: utf-8 -*-
"""Attendance that arrived with a transfer is never rebuilt here.

A transferred attendance record is a transcript of what the other system
recorded. This system cannot work it out again: the door events behind it may
not have come along, the old system may have been corrected by hand, and the
rules that produced it were the rules of that installation.

Worse than a wrong result, rebuilding destroys identity. Every transferred
record carries the external ID that says "this row over there is that row over
here". Recalculation deletes the record together with that external ID, so the
next run of the transfer no longer recognises the row it already brought over
and adds it a second time.

So the transfer module - which writes those external IDs - refuses the rebuild.
The attendance module stays unaware that a transfer exists: it only offers the
hook ``hr.employee._check_recalc_allowed`` and honours whatever is raised from
it.
"""
import logging
from datetime import datetime, time, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from .importers.base_importer import EXTERNAL_ID_MODULE, EXTERNAL_ID_PREFIX
from .importers.phase import _target_available

_logger = logging.getLogger(__name__)

# The record kind whose provenance is checked here.
ATTENDANCE_MODEL = 'hr.attendance'

# Shape of the external ID written for every transferred attendance row, as
# produced by BaseImporter._xml_id_name() ('rfid_import_{source}_{model}_{id}').
# The source installation is part of the name and is not known here, hence the
# wildcard in the middle. Matching on the module alone would be wrong: an
# ordinary spreadsheet import writes the same module with a different name.
EXTERNAL_ID_NAME_PATTERN = '%s%%_%s_%%' % (
    EXTERNAL_ID_PREFIX, ATTENDANCE_MODEL.replace('.', '_'))

# How many people are named in the refusal before it switches to a count.
NAMES_SHOWN = 3

# Same window the rebuild itself starts from when the caller gives no date
# (hr_attendance_multi_rfid/models/hr_employee.py, recalc_attendance).
DEFAULT_LOOKBACK_DAYS = 30


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _check_recalc_allowed(self, start_date=None, end_date=None):
        """Refuse to rebuild attendance that came from another system.

        Silent when nothing in the requested window was transferred, so an
        installation that never ran a transfer behaves exactly as before.
        """
        # First, as the hook requires (hr_rfid/models/hr_employee.py:135), or
        # the objections of everything underneath are lost.
        super()._check_recalc_allowed(start_date, end_date)

        if not self:
            return
        if not _target_available(self.env, ATTENDANCE_MODEL):
            # Attendance is not part of this installation at all.
            return

        groups = self._transferred_attendance_by_employee(start_date, end_date)
        if not groups:
            return

        total = sum(count for _employee, count in groups)
        _logger.warning(
            "Refused to rebuild %s attendance records for %s employee(s): "
            "they were brought over by a data transfer",
            total, len(groups),
        )
        raise UserError(self._transferred_attendance_message(groups, total))

    # ── Detection ─────────────────────────────────────────────

    def _transferred_attendance_by_employee(self, start_date, end_date=None):
        """[(employee, number of transferred records)], heaviest first.

        One query. The external IDs live on another model with no link back to
        attendance, so they are used as a sub-select - the core way to filter
        by "recorded elsewhere" without materialising ids
        (odoo/addons/hr/models/hr_employee.py:549).
        """
        # Not readable by the person who runs a recalculation, and whether a
        # record was transferred is not their private business.
        external_ids = self.env['ir.model.data'].sudo()._search([
            ('module', '=', EXTERNAL_ID_MODULE),
            ('model', '=', ATTENDANCE_MODEL),
            ('name', '=like', EXTERNAL_ID_NAME_PATTERN),
        ])

        periods = self._recalc_periods(start_date, end_date)
        if not periods:
            return []

        # The attendance side is read with the caller's own rights on purpose:
        # the rebuild deletes what the caller can see, so the refusal must be
        # about exactly those records - and no name from another company leaks
        # into the message.
        #
        # Bounded at BOTH ends, and at exactly the moments the rebuild itself
        # would clear. Refusing on a record outside the requested period would
        # block a rebuild that could not have touched it.
        domain = ['|'] * (len(periods) - 1)
        for employees, period_start, period_end in periods:
            domain += [
                '&', '&',
                ('employee_id', 'in', employees.ids),
                ('check_in', '>=', period_start),
                ('check_in', '<', period_end),
            ]
        domain.append(('id', 'in', external_ids.select('res_id')))

        groups = self.env[ATTENDANCE_MODEL]._read_group(
            domain, ['employee_id'], ['__count'],
        )
        return sorted(groups, key=lambda group: group[1], reverse=True)

    def _recalc_periods(self, start_date, end_date):
        """[(employees, first moment, moment after the last)] for this request.

        Asked of the rebuild itself, so the two cannot drift apart: it turns
        the two chosen DAYS into the two MOMENTS it clears between, and a day
        is only a day somewhere - it ends when midnight passes for the person,
        not in London (hr_attendance_multi_rfid/models/hr_employee.py,
        _recalc_window). People are therefore grouped by their timezone, which
        keeps this to one query however many of them there are.
        """
        if start_date is None:
            start_date = fields.Date.today() - timedelta(days=DEFAULT_LOOKBACK_DAYS)
        if end_date is None:
            end_date = fields.Date.today()

        by_tz = {}
        for employee in self:
            by_tz.setdefault(employee.tz, self.env[self._name])
            by_tz[employee.tz] |= employee

        periods = []
        for employees in by_tz.values():
            first = employees[0]
            if hasattr(first, '_recalc_window'):
                window = first._recalc_window(start_date, end_date)
            else:
                # The rebuild is not part of this installation; nothing can
                # call this from there, but the period still has to be right
                # for anything that asks directly.
                window = self._plain_window(start_date, end_date)
            periods.append((employees, window[0], window[1]))
        return periods

    @staticmethod
    def _plain_window(start_date, end_date):
        """The two chosen days as moments, the last one included whole."""
        start = fields.Date.to_date(start_date)
        end = fields.Date.to_date(end_date)
        return (datetime.combine(start, time.min),
                datetime.combine(end + timedelta(days=1), time.min))

    # ── Wording ───────────────────────────────────────────────

    @api.model
    def _transferred_attendance_message(self, groups, total):
        """What the operator is told, in their own terms."""
        named = [employee.display_name for employee, _count in groups[:NAMES_SHOWN]]
        rest = len(groups) - len(named)
        who = ', '.join(named)
        if rest > 0:
            who = self.env._(
                "%(names)s and %(others)s more",
                names=who, others=rest,
            )
        return self.env._(
            "This attendance was brought over from another system and cannot "
            "be recalculated here.\n\n"
            "%(records)s attendance records of %(who)s are a copy of what the "
            "old system recorded. They cannot be worked out again from the "
            "door events, and recalculating them would break the link with "
            "the old system: the next transfer would no longer recognise "
            "them and would bring them over a second time.\n\n"
            "To refresh this data, run the transfer again. To recalculate the "
            "rest, choose a period without these records, or leave these "
            "people out.",
            records=total, who=who,
        )
