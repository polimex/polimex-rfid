# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'rfid_import_ui')
class TestWarningsRender(TransactionCase):
    """Операторът чете предупреждение, не програмен запис.

    Бизнес твърдение (собственик, 2026-08-13, върху реалния екран): човекът,
    който прехвърля системата, вижда изречение на своя език - какво не е наред
    и какво да направи. Досега на екрана излизаше суровият вътрешен запис.
    """

    def _wizard(self):
        return self.env['hr.rfid.odoo.import.wiz'].create({
            'source_url': 'http://localhost:8069',
            'source_login': 'admin',
            'source_password': 'admin',
            'state': 'confirm',
        })

    def test_warning_is_a_sentence_not_a_record(self):
        """Предупреждението е текст за четене, не структура за машина."""
        wiz = self._wizard()
        self.assertTrue(
            wiz.has_blocking,
            "Прогон без избрана фирма трябва да е блокиран",
        )
        html = wiz.blocking_html or ''
        for leak in ('{"', "'level'", "'message'", 'danger'):
            self.assertNotIn(
                leak, str(html),
                "Предупреждението показва вътрешен запис вместо изречение",
            )

    def test_resolving_the_problem_clears_the_warning(self):
        """Решен проблем гаси предупреждението веднага, без презареждане.

        Досега списъкът от зависимости беше непълен, затова банерът оставаше
        да виси, след като операторът вече е направил каквото трябва.
        """
        wiz = self._wizard()
        self.env['hr.rfid.odoo.import.company.line'].create({
            'wizard_id': wiz.id,
            'source_id': 1,
            'source_name': 'Фирма',
            'do_import': True,
            'target_company_id': self.env.company.id,
        })
        self.assertFalse(
            wiz.has_blocking,
            "Предупреждението остана, след като проблемът е решен",
        )

    def test_notice_names_the_feature_not_the_module(self):
        """Съобщението говори за функционалност, не за вътрешно име.

        Тестът е върху превода име-на-модул -> име-на-функционалност, а не
        върху конкретно предупреждение: дали то ще се появи зависи от това
        какво е инсталирано на машината, и тест, който разчита на това, минава
        без да е проверил каквото и да е.
        """
        wiz = self._wizard()
        for module in ('hr_rfid_vending', 'hr_attendance_multi_rfid',
                       'hr_attendance_late', 'rfid_service_base'):
            label = wiz._feature_label(module)
            self.assertTrue(label, "Функционалността %s няма човешко име" % module)
            self.assertNotIn(
                '_', label,
                "Потребителят вижда вътрешно име на модул: %s" % label,
            )
