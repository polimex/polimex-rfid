# -*- coding: utf-8 -*-
"""Carry what the zones said about forgotten badges onto the company.

Until now two settings answered one question. The zone had Maximum Hours in
Zone (when to settle a stay) and Auto-close Worked Hours (what to credit);
core has had Settings -> Attendances -> Automatic Check-Out with a tolerance,
measured against the person's own schedule, all along. On the installation
this came from they disagreed - 12 hours against core's 10 - and nothing said
which was in force.

The zone fields go. What they said must not: a company whose zones limited the
stay clearly wanted forgotten stays settled, so Automatic Check-Out is switched
on for it and the tolerance set to the same point in the day the zone marked.

Runs BEFORE the new module code loads, while the columns still exist.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("SELECT to_regclass('hr_rfid_zone')")
    if not cr.fetchone()[0]:
        return
    cr.execute("""
        SELECT column_name FROM information_schema.columns
         WHERE table_name = 'hr_rfid_zone'
           AND column_name IN ('max_time_in_zone', 'auto_close_time_for_zone')
    """)
    if len({row[0] for row in cr.fetchall()}) < 2:
        return  # already migrated, or never had them

    # The most permissive limit each company set on an attendance zone, and
    # the working day it is measured against. The tolerance is the gap between
    # the two: with an 8-hour day and a 12-hour zone, core settles a stay that
    # runs 4 hours past the schedule - the same moment the zone did.
    cr.execute("""
        SELECT z.company_id,
               MAX(z.max_time_in_zone),
               COALESCE(MAX(cal.hours_per_day), 0)
          FROM hr_rfid_zone z
          JOIN res_company c ON c.id = z.company_id
     LEFT JOIN resource_calendar cal ON cal.id = c.resource_calendar_id
         WHERE z.attendance IS TRUE
           AND z.max_time_in_zone > 0
           AND z.company_id IS NOT NULL
      GROUP BY z.company_id
    """)
    for company_id, zone_limit, hours_per_day in cr.fetchall():
        tolerance = max(0.0, float(zone_limit) - float(hours_per_day or 0.0))
        cr.execute("""
            UPDATE res_company
               SET auto_check_out = TRUE,
                   auto_check_out_tolerance = %s
             WHERE id = %s
               AND auto_check_out IS NOT TRUE
        """, (tolerance, company_id))
        if cr.rowcount:
            _logger.info(
                "Company %s: Automatic Check-Out switched on with a tolerance "
                "of %.2f hours, from a zone that allowed %.2f against a "
                "working day of %.2f.",
                company_id, tolerance, zone_limit, hours_per_day or 0.0)
