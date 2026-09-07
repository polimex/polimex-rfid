# Copyright 2026 Polimex Holding Ltd. - https://polimex.co
# License LGPL-3 or later.
"""Попълва "дошъл в / излязъл в" за дните, измерени преди тези колони да
съществуват.

`first_in` и `last_out` (hr_attendance_extra) се пишат само от преизчислението
(models/hr_employee.py:341-346). На база, дошла от 18, всеки исторически ред ги
има празни, а списъчният изглед ги показва по подразбиране
(views/hr_attendance_extra.xml:82-83) - тоест колоните стоят празни във всеки
отчет за минал период. Измерено на клиентска база (urbanpassive, 06.09.2026):
0 от 3563 реда.

Данните за попълването са налице и непокътнати - изчислява се същото, което
преизчислението би изчислило, по същите три правила:
  * денят се взема по UTC границите на `for_date`, защото точно така ги взема
    и кодът (hr_employee.py:183-184 сравнява наивни UTC времена с датата) -
    смяна върху локални граници тук би дала стойности, които следващото
    преизчисление после ще промени;
  * `in_mode='technical'` се изключва - това е едносекундният запис, който
    ядрото поставя за отсъствен ден (hr_employee.py:186-195);
  * стойността е ЧАСОВНИКЪТ в часовата зона на служителя, не отстояние от
    началото на деня: смяна, приключила на следващата сутрин в 07:24, дава
    7.4153, точно както го смята кодът.

Часовата зона се резолвва като в hr_employee.py:156-157 - собственият календар
на служителя, иначе фирменият, иначе UTC. В v19 календарът живее на hr.version
(делегация hr.employee._inherits, hr 19.0.1.1); за база, дошла от по-стара
версия, се пада обратно към колоната на hr_employee.

Не се измисля стойност, която кодът не би дал: ден без нито едно присъствие
(отсъствие) остава празен по двете полета, а ден само с незатворен престой
получава `first_in` и остава без `last_out` - затварянето му зависи от
`stay_is_not_credible()` / `_settled_check_out()`, което е ORM логика и няма
как да се възпроизведе в SQL. На клиентската база това са 18 и 2 реда.

Идемпотентен: пише само там, където полето още е NULL.
"""
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

#: Часовата зона на служителя - собствен календар, иначе фирмен, иначе UTC.
#: Вариантът за v19, където календарът е на hr.version.
SQL_EMPLOYEE_TZ_VERSION = """
(
    SELECT e.id AS employee_id,
           COALESCE(ecal.tz, ccal.tz, 'UTC') AS tz
      FROM hr_employee e
      LEFT JOIN hr_version v ON v.id = e.current_version_id
      LEFT JOIN resource_calendar ecal ON ecal.id = v.resource_calendar_id
      LEFT JOIN res_company c ON c.id = e.company_id
      LEFT JOIN resource_calendar ccal ON ccal.id = c.resource_calendar_id
) t
"""

#: Същото, когато календарът още стои директно на служителя (до v18).
SQL_EMPLOYEE_TZ_LEGACY = """
(
    SELECT e.id AS employee_id,
           COALESCE(ecal.tz, ccal.tz, 'UTC') AS tz
      FROM hr_employee e
      LEFT JOIN resource_calendar ecal ON ecal.id = e.resource_calendar_id
      LEFT JOIN res_company c ON c.id = e.company_id
      LEFT JOIN resource_calendar ccal ON ccal.id = c.resource_calendar_id
) t
"""


def _employee_tz_source(cr):
    """Откъде се чете календарът - от hr.version (19) или от hr.employee (18)."""
    if openupgrade.column_exists(cr, "hr_version", "resource_calendar_id"):
        return SQL_EMPLOYEE_TZ_VERSION
    return SQL_EMPLOYEE_TZ_LEGACY


def fill_first_in_last_out(env):
    """Попълни часа на първото влизане и последното излизане за всеки
    измерен ден, който още няма стойност."""
    for column in ("first_in", "last_out"):
        if not openupgrade.column_exists(env.cr, "hr_attendance_extra", column):
            _logger.warning(
                "hr_attendance_extra.%s липсва - пропускам попълването", column)
            return
    if not openupgrade.column_exists(env.cr, "hr_attendance", "in_mode"):
        _logger.warning("hr_attendance.in_mode липсва - пропускам попълването")
        return

    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_attendance_extra x
           SET first_in = d.first_in,
               last_out = d.last_out
          FROM (
                SELECT b.id,
                       EXTRACT(HOUR   FROM b.fi)
                     + EXTRACT(MINUTE FROM b.fi) / 60.0
                     + EXTRACT(SECOND FROM b.fi) / 3600.0 AS first_in,
                       EXTRACT(HOUR   FROM b.lo)
                     + EXTRACT(MINUTE FROM b.lo) / 60.0
                     + EXTRACT(SECOND FROM b.lo) / 3600.0 AS last_out
                  FROM (
                        SELECT x2.id,
                               (MIN(a.check_in)  AT TIME ZONE 'UTC')
                                   AT TIME ZONE t.tz AS fi,
                               (MAX(a.check_out) AT TIME ZONE 'UTC')
                                   AT TIME ZONE t.tz AS lo
                          FROM hr_attendance_extra x2
                          JOIN %s ON t.employee_id = x2.employee_id
                          JOIN hr_attendance a
                                ON a.employee_id = x2.employee_id
                               AND a.in_mode IS DISTINCT FROM 'technical'
                               AND a.check_in >= x2.for_date::timestamp
                               AND a.check_in <  x2.for_date::timestamp
                                                 + interval '1 day'
                         WHERE x2.first_in IS NULL
                            OR x2.last_out IS NULL
                         GROUP BY x2.id, t.tz
                       ) b
               ) d
         WHERE d.id = x.id
        """
        % _employee_tz_source(env.cr),
    )


@openupgrade.migrate()
def migrate(env, version):
    fill_first_in_last_out(env)
