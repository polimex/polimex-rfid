# -*- coding: utf-8 -*-
"""Полето, което вносът иска, съществува тук.

Бизнес твърдение: клиентът получава ДАННИТЕ си, не празни записи.

Всяка стъпка сверява имената, които иска, с двете страни - източника и целта -
и мълчаливо изхвърля непознатото. Това е правилно за поле, което една от
версиите няма. Но е ТИХО и за име, което не съществува НИКЪДЕ - тогава данните
просто не идват, а протоколът показва зелен ред с точния брой.

Мерено на живо при пренасяне на облак с 27 фирми - четири списъка съдържаха
такива имена:

* контролерът: `readers_count` / `time_schedules_count` (истинските са
  `readers` / `time_schedules`) - и понеже изходните времена се проверяват
  срещу тези капацитети, всичките 10 бяха отказани;
* дневните обобщения: шест имена (`late_minutes`, `worked_hours`, ...) - всеки
  ред щеше да пристигне като празна черупка: човек и дата, без нито едно число;
* вендинг профилът на човека: седем имена (`..._pin`, `..._negbal`, ...) -
  хората пристигаха с наличност и без правилата, които я управляват;
* зареждането: `amount` / `period` вместо задължителното `auto_refill_total` -
  всичките 3 546 зареждания бяха отказани от базата.

Тестът проверява ЦЕЛТА (тя е налична тук). И четирите дефекта бяха имена,
липсващи от ДВЕТЕ страни, така че тази проверка хваща целия клас; за
източника такава проверка не може да се направи без жива връзка към него, и
това е нарочно записано, за да не се чете тестът като по-силен, отколкото е.
"""

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.attendance_importer import EXTRA_OPTIONAL_FIELDS
from ..models.importers.core_importer import CTRL_OPTIONAL_FIELDS
from ..models.importers.vending_importer import (
    AUTO_REFILL_OPTIONAL_FIELDS, EMPLOYEE_VENDING_FIELDS,
)


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_fields')
class TestFieldNamesAreReal(TransactionCase):

    def _assert_real(self, model, names):
        if model not in self.env:
            self.skipTest('%s не е част от тази инсталация' % model)
        unknown = [n for n in names if n not in self.env[model]._fields]
        self.assertFalse(
            unknown,
            'Вносът иска от %s поле(та), които тук не съществуват: %s. '
            'Такова име се изхвърля мълчаливо и данните не идват, а редът в '
            'протокола изглежда зелен.' % (model, ', '.join(unknown)),
        )

    def test_controller_capacities_and_settings(self):
        self._assert_real('hr.rfid.ctrl', CTRL_OPTIONAL_FIELDS)

    def test_the_numbers_of_a_working_day(self):
        self._assert_real('hr.attendance.extra', EXTRA_OPTIONAL_FIELDS)

    def test_the_vending_profile_of_a_person(self):
        self._assert_real('hr.employee', EMPLOYEE_VENDING_FIELDS)

    def test_what_a_refill_run_records(self):
        self._assert_real('hr.rfid.vending.auto.refill',
                          AUTO_REFILL_OPTIONAL_FIELDS)

    def test_the_capacities_the_constraints_validate_against(self):
        """Именно тези две капацитета решават дали изходните времена влизат."""
        for capacity in ('readers', 'time_schedules', 'inputs', 'outputs'):
            self.assertIn(
                capacity, CTRL_OPTIONAL_FIELDS,
                'Капацитетът %r не се пренася, а ограниченията се проверяват '
                'срещу него - редовете ще бъдат отказани с "извън диапазона '
                'от 1 до 0"' % capacity,
            )
