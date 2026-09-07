# Copyright 2026 Polimex Holding Ltd. - https://polimex.co
# License LGPL-3 or later.
"""Довършва това, до което 19.0.1.1.2 не можеше да стигне: ЗАТВОРЕНИТЕ
присъствия, родени от RFID машинарията.

19.0.1.1.2 разпознава RFID-родения запис по `in_zone_id`, защото зоновият
поток е единственият, който го попълва. Той обаче е и единственият, който го
ИЗТРИВА: v18 `hr_attendance.write` нулира `in_zone_id` в момента, в който се
впише check_out (hr_attendance_multi_rfid 18.0, models/hr_attendance.py:57-61).
Маркерът оцелява само докато човекът е още вътре, тоест предишният скрипт
хващаше единствено отворените престои. Измерено на клиентска база
(urbanpassive, 06.09.2026): 3559 затворени записа - 0 със зона; 2 отворени -
2 със зона. Скриптът се изпълни коректно и улови точно 2 от 3428.

Маркерът, който НЕ се изтрива, е самото минаване: v18 създава присъствието с
точния времеви печат на събитието от четеца, така че `check_in` съвпада ДО
СЕКУНДАТА със запис в `hr_rfid_event_user` за същия човек. На същата база
3332 от 3428 "ръчни" записа съвпадат така, а от 133-те `systray` - нито един;
от 96-те несъвпадащи само 1 е дори в рамките на минута от събитие.

Защо има значение: v19 чисти при преизчисление само `in_mode='rfid'`
(hr_employee.py `_recalc_clear_domain`), а всичко оцеляло третира като думата
на човек и отказва да пише около него (`collides_with_a_person`). Без тази
поправка преизчисление на минал период не изтрива нищо, не създава нищо и
маркира всяко минаване с `no_attendance_reason='manual_record'` - тиха
операция без резултат, която отчита успех.

Идемпотентен: пипа само `in_mode='manual'`; вече поправените са 'rfid'.
Изпълнява се ВЪТРЕ в ъпгрейда, преди потребител да е докоснал системата, тоест
не може да прегази ръчна редакция, направена след него.
"""
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


def stamp_rfid_born_attendance(env):
    """Маркирай като RFID-родено всяко "ръчно" присъствие, чието влизане
    съвпада до секундата с минаване през четец на същия човек."""
    if not openupgrade.column_exists(env.cr, "hr_attendance", "in_mode"):
        _logger.warning(
            "hr_attendance.in_mode липсва - присъствията остават без произход")
        return
    if not openupgrade.table_exists(env.cr, "hr_rfid_event_user"):
        _logger.warning(
            "hr_rfid_event_user липсва - няма по какво да се разпознае "
            "произходът на присъствията")
        return
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_attendance a
           SET in_mode = 'rfid'
         WHERE a.in_mode = 'manual'
           AND EXISTS (
                 SELECT 1
                   FROM hr_rfid_event_user e
                  WHERE e.employee_id = a.employee_id
                    AND e.event_time = a.check_in)
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    stamp_rfid_born_attendance(env)
