# -*- coding: utf-8 -*-
"""Протоколът казва числата на целия прогон, не на последния пас.

Бизнес твърдение (клиентски протокол, 2026-08-15): прехвърляне, чиито пасове
са внесли всичко, не бива да завършва с "0 внесени / 20 851 не дойдоха".

Големият прогон върви на пасове и всеки пас чете само това, което курсорът му
още не е покрил. Редът в протокола се строи наново на всеки пас; строен само
от собствения срез на паса, той докладваше единствено ФИНАЛНИЯ - а финалният
пас по дизайн няма какво да чете и казва нула. На живо: 18 544 + 8 000 камерни
събития внесени на два паса, протокол "8 000 не дойдоха".

И обратното остава вярно: прогон, който наистина не е прочел нищо, докато
източникът държи хиляди, продължава да бие тревога.
"""

import json

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.base_importer import BaseImporter
from ..models.importers.event_importer import EventImporter
from .test_company_scope import _FakeSource


class _PagedSource(_FakeSource):
    """_FakeSource, чийто прочит уважава курсорите като истинския.

    Едно извикване връща една страница - точно колкото един пас успява,
    преди времето му да изтече.
    """

    #: Колко записа минават през един пас. По-малко от източника в теста,
    #: за да са нужни НЯКОЛКО паса - формата, заради която курсорът съществува.
    PAGE = 1000

    def _read_all(self, model, domain, fields, cursor_key, batch_size=1000):
        self.domains[model] = domain
        if self.read_cursors.get(cursor_key) == self.CURSOR_FINISHED:
            return []
        last = self.read_cursors.get(cursor_key, 0)
        rows = [dict(r) for r in self._data.get(model, []) if r['id'] > last]
        # One page per call - exactly what one pass manages before its time
        # runs out. The page is capped so a step reading a big model needs
        # several passes, which is the shape the cursor exists for.
        page, rest = rows[:self.PAGE], rows[self.PAGE:]
        if page:
            self.read_cursors[cursor_key] = page[-1]['id']
            if not rest:
                self.read_cursors[cursor_key] = self.CURSOR_FINISHED
        else:
            self.read_cursors[cursor_key] = self.CURSOR_FINISHED
        return page

    def _search_count(self, model, domain):
        leaves = [leaf for leaf in domain
                  if isinstance(leaf, (list, tuple)) and len(leaf) == 3]
        if any(str(leaf[0]).startswith('camera_id') for leaf in leaves):
            return len([r for r in self._data.get(model, [])
                        if r.get('camera_id')])
        if any('.' in str(leaf[0]) for leaf in leaves):
            # Модулната верига: в тези тестове никое събитие не виси на модул.
            return 0
        return getattr(self, 'total_in_source', len(self._data.get(model, [])))


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_totals')
class TestRunTotalsSurviveThePasses(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Totals Tenant'})
        cls.company_map = {101: cls.company.id}

    def _camera_events(self):
        return [
            {'id': i, 'event_time': '2026-08-01 0%s:00:00' % i,
             'event_action': '1', 'reader_id': False,
             'camera_id': [55, 'ВХОД'], 'license_plate': 'CA%s234BM' % i,
             'anpr_confidence': 90}
            for i in (1, 2, 3)
        ]

    def _source(self, data, **options):
        opts = {'import_user_events': True}
        opts.update(options)
        return _PagedSource(self.env, dict(self.company_map), opts, data)

    def _carry_over(self, previous):
        """Нов пас: нова памет, само записаното на прогона се пренася."""
        nxt = self._source({'hr.rfid.event.user': self._camera_events()})
        nxt.read_cursors = json.loads(json.dumps(previous.read_cursors))
        nxt.step_totals = json.loads(json.dumps(previous.step_totals))
        return nxt

    def test_the_final_pass_reports_the_whole_run(self):
        """Финалният пас, който чете нула по дизайн, казва числата на прогона."""
        if 'cctv.camera' not in self.env:
            self.skipTest('камерите не са част от тази инсталация')
        first = self._source({'hr.rfid.event.user': self._camera_events()})
        EventImporter(first)._import_user_events()

        final = self._carry_over(first)
        importer = EventImporter(final)
        importer._import_user_events()

        row = importer.results[0]
        self.assertEqual(
            (row['source_count'], row['imported_count'], row['status']),
            (3, 3, 'done'),
            'Финалният пас докладва само собствения си (празен) срез, а не '
            'работата на целия прогон - точно редът "0 внесени" от живия '
            'протокол при внесени данни',
        )
        self.assertNotIn(
            'matched none', row['error'] or '',
            'Тревогата "филтърът не хвана нищо" гърми на финалния пас на '
            'прогон, който е внесъл всичко',
        )
        cameras = importer.results[1]
        self.assertEqual(
            cameras['status'], 'done',
            'Камерната сверка сравнява с внесеното от последния пас и '
            'обявява за липсващи събитията, внесени от предишните',
        )

    def test_a_run_that_never_read_anything_still_raises_the_alarm(self):
        """Гейтването по тоталите не бива да заглуши истинската тревога."""
        never = self._source({'hr.rfid.event.user': []})
        never.total_in_source = 5
        importer = EventImporter(never)
        importer._import_user_events()

        row = importer.results[0]
        self.assertIn(
            'matched none', row['error'] or '',
            'Прогон, който не е прочел нищо при пълен източник, вече не '
            'обяснява причината - тревогата е загубена заедно с фалшивата',
        )

    def test_a_failed_insert_rewinds_the_cursors(self):
        """Провален запис не оставя курсора отвъд редовете, които не легнаха."""
        if 'cctv.camera' not in self.env:
            self.skipTest('камерите не са част от тази инсталация')

        class _RefusingSource(_PagedSource):
            def _direct_sql_insert_tracked(self, table, columns, rows, model,
                                           source_ids, batch_size=5000):
                raise ValueError('the database said no')

        broken = _RefusingSource(
            self.env, dict(self.company_map), {'import_user_events': True},
            {'hr.rfid.event.user': self._camera_events()})
        importer = EventImporter(broken)
        importer._import_user_events()

        self.assertEqual(importer.results[0]['status'], 'error')
        self.assertNotIn(
            'events:hr.rfid.event.user:module', broken.read_cursors,
            'Курсорът остана след проваления запис - следващият пас ще '
            'прескочи точно редовете, които базата отказа',
        )
        self.assertNotIn('events:hr.rfid.event.user:camera',
                         broken.read_cursors)

    def test_totals_travel_with_the_run_record(self):
        """Тоталите се пазят на записа на прогона, до курсорите."""
        run_model = self.env['hr.rfid.odoo.import.run']
        self.assertIn(
            'step_totals_json', run_model._fields,
            'Тоталите живеят само в паметта - процес, който продължава '
            'прогона, започва да брои от нула и протоколът пак лъже',
        )

    def test_the_second_leg_waits_when_time_ran_out_in_the_first(self):
        """Изтеклият пас не подхваща камерния крак - следващият го поема."""
        if 'cctv.camera' not in self.env:
            self.skipTest('камерите не са част от тази инсталация')
        tired = self._source({'hr.rfid.event.user': self._camera_events()})
        tired.stopped_early = True
        importer = EventImporter(tired)
        records = importer._read_both_legs(
            'hr.rfid.event.user', [], ['event_time'], 'events:test')
        self.assertNotIn(
            'events:test:camera', tired.read_cursors,
            'Камерният крак тръгна, макар времето на паса да е изтекло '
            'още в модулния',
        )
        self.assertEqual(len(records), 3)


class _StubBase(BaseImporter):
    """Гол BaseImporter за аритметиката на accumulate - без източник."""

    def __init__(self):
        self.step_totals = {}
        self.read_cursors = {}


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_totals')
class TestAccumulateArithmetic(TransactionCase):

    def test_slices_add_up_and_come_back(self):
        base = _StubBase()
        base.accumulate('step', source=2, imported=2, camera=1)
        totals = base.accumulate('step', source=1, linked=1)
        self.assertEqual(totals, {'source': 3, 'imported': 2,
                                  'linked': 1, 'camera': 1})

    def test_json_round_trip_keeps_counting(self):
        """Точно каквото прави записът на прогона между два паса."""
        base = _StubBase()
        base.accumulate('step', source=2)
        reloaded = _StubBase()
        reloaded.step_totals = json.loads(json.dumps(base.step_totals))
        totals = reloaded.accumulate('step', source=1)
        self.assertEqual(totals['source'], 3)

    def test_rewind_forgets_only_the_named_reads(self):
        base = _StubBase()
        base.read_cursors = {'a:module': 5, 'a:camera': 7, 'b:module': 9}
        base.rewind_cursors('a:module', 'a:camera', 'never:was')
        self.assertEqual(base.read_cursors, {'b:module': 9})
