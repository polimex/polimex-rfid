# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install', 'rfid_access_group')
class TestAddDoorsTimeSchedule(TransactionCase):
    """Правата на една фирма не се пишат с работното време на друга.

    Бизнес твърдение: когато на група достъп на фирма А се даде врата, работното
    време идва от графиците на фирма А. Графикът на фирма Б описва работния ден
    на нейните хора и няма никаква връзка с достъпа във фирма А - попадне ли там,
    вратата се отваря по чуждо разписание.

    Графиците не подлежат на изтриване (hr_rfid_ctrl_time_schedule.py:102),
    затова тестовете стъпват върху заварените и добавят свои, вместо да чистят.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env['res.company'].create({'name': 'Фирма А'})
        cls.TimeSchedule = cls.env['hr.rfid.time.schedule']

    def _door(self, name='Врата'):
        return self.env['hr.rfid.door'].create({'name': name, 'number': 1})

    def _group(self, company):
        return self.env['hr.rfid.access.group'].create({
            'name': 'Група %s' % company.name, 'company_id': company.id,
        })

    def _rel_schedule(self, group, door):
        return self.env['hr.rfid.access.group.door.rel'].search([
            ('access_group_id', '=', group.id), ('door_id', '=', door.id),
        ]).time_schedule_id

    def test_schedule_never_belongs_to_another_company(self):
        """Избраното работно време е на фирмата на групата, или е общо.

        В базата вече има графици на другите фирми, при това с по-малки
        идентификатори - точно те печелеха при търсене без филтър.
        """
        foreign = self.TimeSchedule.search([
            ('company_id', 'not in', [self.company_a.id, False]),
        ], limit=1, order='number')
        self.assertTrue(
            foreign, "Тестът иска поне един чужд график, за да има какво да сбърка")

        group = self._group(self.company_a)
        door = self._door('Врата А')

        group.add_doors(door)

        chosen = self._rel_schedule(group, door)
        self.assertTrue(chosen, "Правото е останало без работно време")
        self.assertIn(
            chosen.company_id, (self.company_a, self.env['res.company']),
            "Правото е записано с работното време на друга фирма (%s)"
            % (chosen.company_id.name or '-'),
        )

    def test_missing_schedule_says_what_is_missing(self):
        """Липсващо работно време казва какво липсва.

        Преди това търсенето вземаше първия елемент от празен резултат и даваше
        IndexError - съобщение, което не помага на никого.

        Нова фирма получава шестнадесет графика автоматично (res_company.py:26),
        така че празната таблица не се постига през нормалния път. Клонът пак
        трябва да е покрит: непроверена защита е мъртъв код, който минава
        компилация и се проваля чак когато потрябва.
        """
        group = self._group(self.company_a)
        door = self._door()
        empty = self.TimeSchedule.browse()

        with patch.object(type(self.TimeSchedule), 'search', return_value=empty):
            with self.assertRaises(UserError):
                group.add_doors(door)

    def test_global_schedule_is_acceptable(self):
        """График без фирма важи за всички - не бива да се отхвърля.

        Фирмата се оставя без собствени графици (те се преотстъпват на друга),
        за да остане общият единственият кандидат. Иначе своят винаги печели и
        клонът за общите графици не се упражнява.
        """
        company = self.env['res.company'].create({'name': 'Фирма с общ график'})
        self.TimeSchedule.search([('company_id', '=', company.id)]).write({
            'company_id': self.company_a.id,
        })
        shared = self.TimeSchedule.create({
            'name': 'Общ график', 'number': 0, 'company_id': False,
        })
        group = self._group(company)
        door = self._door()

        group.add_doors(door)

        self.assertEqual(
            self._rel_schedule(group, door), shared,
            "Общият график е отхвърлен, макар да важи за всички фирми",
        )
