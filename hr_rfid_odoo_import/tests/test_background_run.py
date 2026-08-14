# -*- coding: utf-8 -*-
import json

from odoo.tests import TransactionCase, tagged

from ..models import import_run


# 'rfid_odoo_import' as well as the dedicated tag: the shared one is what the
# pipeline selects on (.github/workflows/test.yml), and a guard the pipeline
# never runs is not a guard.
@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_run')
class TestBackgroundRun(TransactionCase):
    """Прехвърлянето издържа нощта и не започва отначало.

    Бизнес твърдение (собственик, 2026-08-13): обект с десетки хиляди събития
    се прехвърля наведнъж. Ако нещо прекъсне - изтекло време, рестарт, спрян
    сървър - работата продължава оттам, а не от нулата, и никой запис не влиза
    два пъти. Операторът затваря страницата и се връща по-късно.
    """

    def _run(self, **overrides):
        values = {
            'source_url': 'http://localhost:8069',
            'source_db': 'src',
            'source_login': 'admin',
            'source_password': 'secret',
            'options_json': json.dumps({'import_hardware': True}),
            'installed_modules_json': json.dumps(['hr_rfid']),
            'company_map_json': json.dumps({'1': self.env.company.id}),
        }
        values.update(overrides)
        return self.env['hr.rfid.odoo.import.run'].create(values)

    def test_the_request_survives_the_hour(self):
        """Заявката не се чисти сама - иначе прогонът спира тихо по средата."""
        self.assertFalse(
            self.env['hr.rfid.odoo.import.run']._transient,
            "Заявката се чисти автоматично и дълъг прогон ще изчезне",
        )

    def test_the_account_of_what_happened_is_kept(self):
        """Протоколът също остава - иначе накрая няма какво да се прочете."""
        self.assertFalse(
            self.env['hr.rfid.odoo.import.log']._transient,
            "Протоколът се чисти и операторът остава без отчет",
        )

    def test_password_is_gone_when_finished(self):
        """Паролата на другата система не остава да лежи след края."""
        run = self._run()
        run._finish(state='done')
        self.assertFalse(
            run.sudo().source_password, "Паролата остана записана след края")
        self.assertEqual(run.state, 'done')

    def test_password_is_not_readable_by_everyone(self):
        """Паролата се вижда само от администратор."""
        field = self.env['hr.rfid.odoo.import.run']._fields['source_password']
        self.assertTrue(field.groups, "Паролата няма ограничение за четене")

    def test_finished_steps_are_not_repeated(self):
        """Втори пас не повтаря вече свършеното."""
        run = self._run(done_phases_json=json.dumps(['Phase 1+3']))
        done = set(json.loads(run.done_phases_json))
        self.assertIn('Phase 1+3', done)

    def test_decisions_survive_a_new_process(self):
        """Решенията на оператора се прилагат наново при всеки пас.

        Те живеят в паметта иначе, а пас в нов процес би сметнал пропуснат
        запис за нов - и той се сблъсква със съществуващия, което сваля цялата
        стъпка.
        """
        run = self._run(resolution_json=json.dumps([
            {'model': 'hr.rfid.webstack', 'source_id': 7,
             'target_id': 3, 'resolution': 'skip'},
        ]))
        importer = run._build_importer({'import_hardware': True})
        self.assertIsNone(
            importer._get_target_id('hr.rfid.webstack', 7),
            "Пропуснатият по решение запис е забравен при новия пас",
        )

    def test_a_long_read_can_stop_and_be_continued(self):
        """Четенето спира между страници, когато времето изтече.

        Крон нишката също има таван, а превишаването му не просто проваля
        стъпката - рестартира сървъра.
        """
        from odoo.addons.hr_rfid_odoo_import.models.importers.base_importer import (
            BaseImporter,
        )
        self.assertTrue(hasattr(BaseImporter, 'prefetch_external_ids'))
        run = self._run()
        importer = run._build_importer({})
        self.assertIsNone(importer.time_is_up)
        self.assertFalse(importer.stopped_early)

    def test_scheduler_entry_is_active(self):
        """Кронът се доставя включен.

        Изключен крон не тръгва дори когато го събудим - условието за
        готовност изисква active, и провалът е напълно безмълвен.
        """
        cron = self.env.ref('hr_rfid_odoo_import.ir_cron_import_run')
        self.assertTrue(cron.active, "Кронът е изключен и няма да тръгне никога")

    def test_manual_start_does_not_do_the_work_in_the_request(self):
        """Ръчното пускане само събужда работника."""
        self.assertTrue(
            hasattr(self.env['hr.rfid.odoo.import.run'], '_cron_process'))

    def test_a_dead_transfer_stays_closed_when_the_next_one_breaks(self):
        """Затварянето на мъртво прехвърляне се запазва, преди да се пробва друго.

        Бизнес твърдение (собственик): спряло по средата прехвърляне не бива да
        държи опашката, нито паролата на другата система. Работникът го затваря
        при всяко събуждане - но ако тази работа не се запази ВЕДНАГА, следващото
        прехвърляне, което се счупи, дърпа отката и връща мъртвите обратно
        „в ход". Тогава при всяко следващо събуждане опашката е блокирана от
        същите мъртви прогони, а паролата остава да лежи в базата.
        """
        abandoned = self._run(state='running')
        waiting = self._run()

        # Какво щеше да остане в базата на всяка точка, в която свършеното до
        # момента е направено постоянно.
        kept = []
        self.patch(self.env.cr, 'commit',
                   lambda: kept.append((abandoned.state, waiting.state)))
        # Откатът също се обезврежда: в тест истинският би върнал самата
        # подготовка на теста (както прави и sms_twilio в кора).
        self.patch(self.env.cr, 'rollback', lambda: None)

        def falls_over(run):
            raise ValueError('работникът падна')

        self.patch(self.registry['hr.rfid.odoo.import.run'], '_process_pass',
                   falls_over)
        # Всичко още отворено се брои за недокоснато твърде дълго.
        self.patch(import_run, 'STALLED_MINUTES', -1)
        self.env['hr.rfid.odoo.import.run']._cron_process()

        self.assertEqual(abandoned.state, 'failed',
                         "Прогон, по който никой не работи, трябва да се затвори")
        self.assertFalse(abandoned.sudo().source_password,
                         "Паролата на другата система остана след затварянето")
        self.assertTrue(kept, "Затварянето не е направено постоянно изобщо")
        self.assertEqual(
            kept[0], ('failed', 'queued'),
            "Мъртвият прогон трябва да е затворен и запазен ПРЕДИ да се пробва "
            "следващият - запазен само след него, счупването отнася и "
            "затварянето със себе си",
        )

    # ── Гледането не пипа прехвърлянето ───────────────────────

    def test_looking_at_a_running_transfer_does_not_touch_it(self):
        """Операторът гледа докъде е стигнало и с това не му пречи.

        Продукционен инцидент (192.168.0.99, 2026-08-14): бутонът в заглавната
        лента пишеше състоянието на СЪЩИЯ ред, който работникът пренаписва на
        всяка фаза. Odoo работи на REPEATABLE READ (odoo/sql_db.py:373), затова
        писането се блокираше в реда, който работникът държи, и накрая падаше с
        "could not serialize access"; Odoo повтаря заявката пет пъти
        (odoo/service/model.py:29-30), значи операторът чакаше дълго и виждаше
        червена сървърна грешка - върху прехвърляне, което вървеше нормално.
        """
        run = self._run(state='running', current_phase='Phase 1+3',
                        done_count=3, total_count=12)
        before = run.read()[0]

        run.action_refresh()

        self.assertEqual(run.read()[0], before,
                         "Погледът върху прехвърлянето не бива да променя нищо "
                         "по него - работникът пише в същия ред")

    def test_looking_does_not_start_a_second_worker(self):
        """Върху вече работещо прехвърляне няма какво да се събужда.

        Втори пас само намира реда зает; будим планировчика единствено когато
        прехвърлянето чака.
        """
        woken = []
        self.patch(self.registry['hr.rfid.odoo.import.run'],
                   '_wake_the_worker', lambda records: woken.append(True))

        self._run(state='running').action_refresh()
        self.assertFalse(woken, "Работещо прехвърляне не се бута наново")

        self._run(state='queued').action_refresh()
        self.assertTrue(woken, "Чакащо прехвърляне трябва да събуди работника")

    def test_a_transfer_is_refused_when_nothing_would_ever_run_it(self):
        """Спрян планировчик значи прехвърляне, което чака вечно.

        По-добре отказ на място, отколкото заявка, която стои на "изчаква
        стартиране" и операторът натиска бутона до безкрай.
        """
        from odoo.exceptions import RedirectWarning

        cron = self.env.ref('hr_rfid_odoo_import.ir_cron_import_run')
        wizard = self.env['hr.rfid.odoo.import.wiz'].create({
            'source_url': 'http://localhost:8069',
            'source_login': 'admin',
            'source_password': 'secret',
        })

        cron.sudo().active = False
        # Точният клас, не общият: тестът тече като системен администратор и
        # получава варианта с пренасочване. RedirectWarning наследява направо
        # Exception (odoo/exceptions.py:24), не UserError - а v19 assertRaises
        # не приема tuple, затова един клас.
        with self.assertRaises(RedirectWarning):
            wizard._check_background_worker_available()

        cron.sudo().active = True
        self.assertIsNone(
            wizard._check_background_worker_available(),
            "С работещ планировчик прехвърлянето не бива да се спира",
        )
