# -*- coding: utf-8 -*-
"""Пренесеното работно време не се преизчислява от този модул.

Бизнес твърдение (собственик, 2026-08-13): пренесените данни не минават през
чужд код. Записът, дошъл с прехвърлянето, е препис на другата система и се
опреснява само като прехвърлянето се пусне пак. Преизчисляването го трие
заедно с реда, по който прехвърлянето го разпознава - следващият прогон вече
не вижда, че този запис е пренесен, и го внася втори път.

Отрицателното твърдение тежи колкото положителното: база, в която никога не е
имало прехвърляне, трябва да се държи точно както преди.
"""
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.hr_rfid_odoo_import.models.importers.base_importer import (
    EXTERNAL_ID_MODULE, BaseImporter,
)

SRC_DB = 'old_cloud'


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_identity')
class TestRecalcGuard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'hr.attendance' not in cls.env:
            raise cls.skipTest(cls, 'hr_attendance not installed')
        cls.Attendance = cls.env['hr.attendance']
        # The naming of the external ID entry is taken from the transfer itself, so
        # this test fails if the transfer ever renames what it writes.
        cls.importer = BaseImporter(
            cls.env, 'https://example.invalid', SRC_DB, 1, 'x', {}, {},
        )
        cls.start_date = fields.Date.today() - timedelta(days=10)

    @classmethod
    def _employee(cls, name):
        return cls.env['hr.employee'].create({'name': name})

    @classmethod
    def _attendance(cls, employee, days_ago):
        check_in = fields.Datetime.now() - timedelta(days=days_ago)
        return cls.Attendance.create({
            'employee_id': employee.id,
            'check_in': check_in,
            'check_out': check_in + timedelta(hours=8),
        })

    @classmethod
    def _mark_as_transferred(cls, attendance, source_id):
        """Write the entry the transfer writes for a record it brought over."""
        cls.env['ir.model.data'].create({
            'module': EXTERNAL_ID_MODULE,
            'name': cls.importer._xml_id_name('hr_attendance', source_id),
            'model': 'hr.attendance',
            'res_id': attendance.id,
        })

    def test_recalculation_is_refused_for_transferred_records(self):
        """Записът, дошъл с прехвърлянето, спира преизчисляването."""
        employee = self._employee('Transferred Person')
        attendance = self._attendance(employee, days_ago=3)
        self._mark_as_transferred(attendance, 101)

        with self.assertRaises(UserError) as caught:
            employee._check_recalc_allowed(self.start_date, fields.Date.today())

        self.assertTrue(
            attendance.exists(),
            'Отказът трябва да е преди каквато и да е промяна по записа',
        )
        self.assertIn(
            employee.display_name, str(caught.exception),
            'Операторът трябва да види за кого става дума',
        )

    def test_recalculation_is_allowed_for_records_born_here(self):
        """База без прехвърляне работи както преди.

        Това е тестът, който доказва, че не сме спрели всичко.
        """
        employee = self._employee('Local Person')
        self._attendance(employee, days_ago=4)

        # No exception: nothing here came from anywhere else.
        employee._check_recalc_allowed(self.start_date, fields.Date.today())

    def test_transferred_record_of_someone_else_does_not_block_me(self):
        """Отказът е за поисканите хора, не за цялата база."""
        transferred_person = self._employee('Moved Person')
        self._mark_as_transferred(
            self._attendance(transferred_person, days_ago=5), 102)
        local_person = self._employee('Home Grown Person')
        self._attendance(local_person, days_ago=5)

        local_person._check_recalc_allowed(self.start_date, fields.Date.today())

    def test_record_before_the_starting_date_does_not_block(self):
        """Извън поискания период преизчисляването не се пипа."""
        employee = self._employee('Old Data Person')
        self._mark_as_transferred(
            self._attendance(employee, days_ago=40), 103)

        employee._check_recalc_allowed(self.start_date, fields.Date.today())

    def test_record_after_the_end_of_the_period_does_not_block(self):
        """Периодът има и КРАЙ - записът след него не спира преизчисляването.

        Преизчисляването чисти точно между двата избрани дни. Отказ заради
        запис извън тях спира работа, която не би го докоснала - а именно
        такъв отказ получаваше операторът, защото проверката гледаше само
        началото.
        """
        employee = self._employee('Future Data Person')
        self._mark_as_transferred(
            self._attendance(employee, days_ago=-5), 104)

        employee._check_recalc_allowed(
            self.start_date, fields.Date.today() - timedelta(days=1))

    def test_a_record_inside_the_period_still_blocks(self):
        """Обратната страна на същото: вътре в периода отказът си остава."""
        employee = self._employee('Inside Period Person')
        self._mark_as_transferred(self._attendance(employee, days_ago=2), 105)

        with self.assertRaises(UserError):
            employee._check_recalc_allowed(
                self.start_date, fields.Date.today())

    def test_message_names_the_people_instead_of_listing_ids(self):
        """Съобщението казва кои са хората и колко са записите.

        Списък с вътрешни номера не помага на никого - операторът трябва да
        разпознае служителите и да реши какво да прави.
        """
        employees = self.env['hr.employee']
        for index in range(4):
            employee = self._employee('Moved Person %s' % index)
            # Two records each, so the total in the message is not the number
            # of people - a count of people would read as a count of records.
            for offset in range(2):
                self._mark_as_transferred(
                    self._attendance(employee, days_ago=3 + offset),
                    200 + index * 10 + offset,
                )
            employees |= employee

        with self.assertRaises(UserError) as caught:
            employees._check_recalc_allowed(self.start_date, fields.Date.today())
        message = str(caught.exception)

        named = [e for e in employees if e.display_name in message]
        self.assertEqual(
            len(named), 3,
            'Очаквахме няколко имена и после брой, а не всички или нито едно',
        )
        self.assertIn(
            '8', message,
            'Операторът трябва да види колко записа спират преизчисляването',
        )
        self.assertNotIn(
            '[', message,
            'Съобщението не бива да изсипва списък с вътрешни номера',
        )
        for leak in ('hr.attendance', 'ir.model.data', 'res_id', 'employee_id'):
            self.assertNotIn(
                leak, message,
                'Съобщението е за оператора, не за програмист',
            )
