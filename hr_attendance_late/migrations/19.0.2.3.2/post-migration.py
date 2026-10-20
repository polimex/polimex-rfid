# Copyright 2026 Polimex Holding Ltd. - https://polimex.co
# License LGPL-3 or later.
"""Попълва "дошъл в / излязъл в" за дните, измерени преди тези колони да
съществуват.

`first_in` и `last_out` (hr_attendance_extra) се пишат само от преизчислението
(models/hr_employee.py:341-346). Двете колони НЕ съществуват в клона 18.0 -
появяват се в 19.0 линията на модула. Затова празни ги има всеки ред, измерен
преди версията, която ги въвежда - включително на база, РОДЕНА на 19, която още
не е стигнала до тази версия. Не е въпрос на идване от 18.

Списъчният изглед ги показва по подразбиране
(views/hr_attendance_extra.xml:82-83) - тоест колоните стоят празни във всеки
отчет за минал период. Измерено на клиентска база (клиентски случай, 06.09.2026):
0 от 3563 реда.

Данните за попълването са налице и непокътнати - изчислява се същото, което
преизчислението би изчислило, по същите три правила:
  * денят е денят на служителя - от неговата полунощ до следващата, в
    неговата собствена зона, точно както го взема кодът
    (hr.employee._local_days_window в hr_attendance_multi_rfid). Други
    граници тук биха дали стойности, които следващото преизчисление после ще
    промени;
  * `in_mode='technical'` се изключва - това е едносекундният запис, който
    ядрото поставя за отсъствен ден (hr_employee.py:186-195);
  * стойността е ЧАСОВНИКЪТ в часовата зона на служителя, не отстояние от
    началото на деня: смяна, приключила на следващата сутрин в 07:24, дава
    7.4153, точно както го смята кодът.

Часовата зона е собствената зона на служителя (hr.employee._local_tz в
hr_attendance_multi_rfid) - зоната на ресурса му, иначе UTC. Тя стои на
resource_resource и в 18, и в 19.

Не се измисля стойност, която кодът не би дал: ден без нито едно присъствие
(отсъствие) остава празен по двете полета, а ден само с незатворен престой
получава `first_in` и остава без `last_out` - затварянето му зависи от
`stay_is_not_credible()` / `_settled_check_out()`, което е ORM логика и няма
как да се възпроизведе в SQL. На клиентската база това са 18 и 2 реда.

Идемпотентен: пише само там, където полето още е NULL.
"""
import logging

from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)

#: Собствената часова зона на служителя - тази на ресурса му, иначе UTC.
SQL_EMPLOYEE_TZ = """
(
    SELECT e.id AS employee_id,
           COALESCE(r.tz, 'UTC') AS tz
      FROM hr_employee e
      LEFT JOIN resource_resource r ON r.id = e.resource_id
) t
"""


def fill_first_in_last_out(cr):
    """Попълни часа на първото влизане и последното излизане за всеки
    измерен ден, който още няма стойност."""
    for column in ("first_in", "last_out"):
        if not column_exists(cr, "hr_attendance_extra", column):
            _logger.warning(
                "hr_attendance_extra.%s липсва - пропускам попълването", column)
            return
    if not column_exists(cr, "hr_attendance", "in_mode"):
        _logger.warning("hr_attendance.in_mode липсва - пропускам попълването")
        return

    cr.execute(
        """
        UPDATE hr_attendance_extra x
           -- COALESCE, а не пряко присвояване: редът се ИЗБИРА, когато КОЯТО И
           -- ДА Е от двете колони е празна, но дотук се ПРЕЗАПИСВАХА и двете.
           -- Ден, чието влизане е записано, а излизането още не е (при
           -- измерения клиентски случай такива са 5), при повторен прогон би загубил ръчна
           -- корекция на вече попълнената колона. Пише се само празното.
           SET first_in = COALESCE(x.first_in, d.first_in),
               last_out = COALESCE(x.last_out, d.last_out)
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
                               -- полунощ до полунощ в зоната на служителя,
                               -- всеки край поотделно (ден от 23/25 часа)
                               AND a.check_in >= (x2.for_date::timestamp
                                                  AT TIME ZONE t.tz)
                                                 AT TIME ZONE 'UTC'
                               AND a.check_in <  ((x2.for_date + 1)::timestamp
                                                  AT TIME ZONE t.tz)
                                                 AT TIME ZONE 'UTC'
                         WHERE x2.first_in IS NULL
                            OR x2.last_out IS NULL
                         GROUP BY x2.id, t.tz
                       ) b
               ) d
         WHERE d.id = x.id
        """
        % SQL_EMPLOYEE_TZ,
    )
    _logger.info(
        "hr_attendance_late: %s дни получиха час на влизане/излизане",
        cr.rowcount)


def migrate(cr, version):
    fill_first_in_last_out(cr)
