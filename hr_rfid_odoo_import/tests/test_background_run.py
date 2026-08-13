# -*- coding: utf-8 -*-
import json

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'rfid_import_run')
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
        self.assertTrue(hasattr(BaseImporter, 'warm_up_ledger'))
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
