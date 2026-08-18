# -*- coding: utf-8 -*-
"""Никой дълъг прочит не може да тръгне без памет докъде е стигнал.

Бизнес твърдение: прехвърлянето на голям наемател ЗАВЪРШВА. Мерено на облака с
27 фирми - фазата „Хора" се четеше отначало на всеки пас и целта остана с 1 001
от 6 176 души завинаги; същото важеше за 200 004 температурни отчета, 280 046
вендинг реда и 6 625 продажби на услуги.

Поправката е ГАРД, а не навик: `cursor_key` е задължителен аргумент на
`_read_all`. Тестовете тук пазят самия гард, защото гард без тест е обещание -
преди поправката ключът беше по избор, единадесет от шестнадесет места го
пропускаха, и механизмът се четеше като готов, докато половината от него го
нямаше.

Двете правила, които се проверяват:

1. прочит без ключ НЕ СЕ ИЗПЪЛНЯВА (вдига), вместо да започва отначало;
2. ключът е уникален за СТЪПКАТА, не за модела - две стъпки, които четат един
   и същи модел през различни обхвати (четците на контролер и четците на
   камера), със споделен ключ биха прескочили записите една на друга.
"""
import inspect
import re

from odoo.tests.common import TransactionCase, tagged

from ..models.importers import (
    access_importer, attendance_importer, camera_importer, core_importer,
    event_importer, leave_importer, people_importer, service_importer,
    site_importer, vending_importer,
)
from ..models.importers.base_importer import BaseImporter

#: Файловете, чиито прочити трябва да носят ключ.
IMPORTER_MODULES = [
    access_importer, attendance_importer, camera_importer, core_importer,
    event_importer, leave_importer, people_importer, service_importer,
    site_importer, vending_importer,
]


class _NoSource(BaseImporter):
    """Само това, което `_read_all` пипа, преди да поиска ключ."""

    def __init__(self):
        self.read_cursors = {}
        self.step_totals = {}
        self.stopped_early = False
        self.time_is_up = None


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_cursors')
class TestEveryReadCanBeResumed(TransactionCase):

    def test_a_read_without_a_cursor_key_refuses_to_run(self):
        """Без ключ прочитът не тръгва - иначе тръгва отначало всеки пас."""
        source = _NoSource()
        for missing in (None, '', False):
            message = (
                'Прочит с ключ %r беше допуснат. Точно така се стигна до '
                '1 001 от 6 176 души: пасът чете първата страница, времето му '
                'свършва, следващият започва от нея пак.' % (missing,))
            with self.assertRaises(ValueError, msg=message):
                source._read_all('hr.employee', [], ['name'], missing)

    def test_a_finished_read_is_not_asked_for_again(self):
        """Приключилият прочит не пипа източника втори път."""
        source = _NoSource()
        source.read_cursors['people:hr.employee'] = source.CURSOR_FINISHED
        self.assertEqual(
            source._read_all('hr.employee', [], ['name'], 'people:hr.employee'),
            [],
            'Приключил прочит пак пита другата система - на 1,2 милиона реда '
            'това е цял пас, хвърлен на вятъра',
        )

    # ── ключът е на СТЪПКАТА, не на модела ────────────────────

    def _cursor_keys(self):
        """Ключовете, изписани в кода, по файл и по ред."""
        found = []
        for module in IMPORTER_MODULES:
            code = inspect.getsource(module)
            where = module.__name__.rsplit('.', 1)[-1]
            # Ключът се появява или като присвояване (`cursor_key = '...'`),
            # или направо в самото извикване на `_read_all`.
            for pattern in (r"cursor_key\s*=\s*'([^']+)'",
                            r"_read_all\([^)]*?'([a-z]+:[^']*)'"):
                for match in re.finditer(pattern, code, re.S):
                    found.append((where, match.group(1)))
        return found

    def test_no_two_steps_share_one_cursor_key(self):
        """Един ключ - една стъпка.

        Камерната фаза и хардуерната четат ЕДИН И СЪЩИ модел (`hr.rfid.reader`)
        през различни обхвати. Със споделен ключ втората би продължила оттам,
        докъдето е стигнала първата, и всяка би прескочила записите на другата -
        загуба, която никой брояч не показва, защото и двете стъпки отчитат
        „прочетох докрай".
        """
        keys = self._cursor_keys()
        self.assertTrue(
            keys,
            'Тестът не намери нито един ключ в кода - шаблонът се е променил и '
            'проверката е спряла да пази каквото и да е',
        )
        seen = {}
        clashes = []
        for where, key in keys:
            if key in seen and seen[key] != where:
                clashes.append('%s се ползва и в %s, и в %s'
                               % (key, seen[key], where))
            seen.setdefault(key, where)
        self.assertFalse(
            clashes,
            'Един ключ в две различни стъпки: %s. Всяка ще прескача записите '
            'на другата, а протоколът ще казва, че е прочела всичко.'
            % '; '.join(clashes),
        )

    def test_every_step_that_reads_pages_names_its_step_in_the_key(self):
        """Ключът казва КОЯ стъпка е, не само кой модел."""
        bare_model = [(where, key) for where, key in self._cursor_keys()
                      if ':' not in key]
        self.assertFalse(
            bare_model,
            'Ключ само с име на модел: %s. Две стъпки върху същия модел ще '
            'споделят курсора му.' % bare_model,
        )
