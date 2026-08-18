# -*- coding: utf-8 -*-
"""Продадената услуга важи ОТ МОМЕНТА НА ПРОДАЖБАТА нататък.

Бизнес твърдение (собственик): посетител, който плаща в 15:10, влиза. Каса,
която отказва да запише картата с „периодът изтича в миналото", е спрян
приход и опашка на рецепцията.

Услугата има РАБОТНО ВРЕМЕ (например 08:00-17:00) и ПРОДЪЛЖИТЕЛНОСТ (един ден,
един месец). И двете са в часовника на обекта, не в UTC - „затваряме в 17:00"
значи 17:00 при клиента. Сметнати върху UTC датата, двете се разминават всеки
ден в часовете, когато местната дата и UTC датата са различни, а през лятото в
София това е цяла трета от денонощието.

Тестът върти часовника през денонощието, защото дефектът се вижда само в част
от него - точно затова и стигна до каса.
"""

from datetime import date, datetime, timedelta

import pytz
from freezegun import freeze_time

from odoo.tests.common import TransactionCase, tagged

#: Часът на обекта. Дефектът е в разминаването между него и UTC.
SITE_TZ = 'Europe/Sofia'


@tagged('post_install', '-at_install', 'rfid_service', 'rfid_service_hours')
class TestSalePeriodIsNeverInThePast(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = SITE_TZ
        cls.company = cls.env.company
        cls.access_group = cls.env['hr.rfid.access.group'].create({
            'name': 'Басейн', 'company_id': cls.company.id,
        })
        cls.service = cls.env['rfid.service'].create({
            'name': 'Дневна карта',
            'company_id': cls.company.id,
            'access_group_id': cls.access_group.id,
            'fixed_time': True,
            'time_interval_start': 8.0,     # обектът отваря в 08:00 местно
            'time_interval_end': 17.0,      # и затваря в 17:00 местно
            'time_interval_type': 'days',
            'time_interval_number': 1,
        })

    def _sold_at(self, local_hour, local_minute=0):
        """Периодът, който касата предлага в този местен час."""
        tz = pytz.timezone(SITE_TZ)
        # Ден без превключване на часовото време, за да е за ЧАСА, не за него.
        local = tz.localize(datetime.combine(date(2026, 8, 20),
                                             datetime.min.time())
                            + timedelta(hours=local_hour, minutes=local_minute))
        with freeze_time(local.astimezone(pytz.UTC).replace(tzinfo=None)):
            wiz = self.env['rfid.service.sale.wiz'].new({
                'service_id': self.service.id,
            })
            wiz._onchange_service_id()
            return wiz.start_date, wiz.end_date, datetime.utcnow()

    def test_the_period_offered_covers_the_moment_of_sale(self):
        broken = []
        for hour in range(0, 24):
            start, end, now = self._sold_at(hour, 10)
            if not start or not end or end <= now:
                broken.append('%02d:10 -> %s .. %s' % (hour, start, end))
        self.assertFalse(
            broken,
            'Касата предлага период, който вече е изтекъл, в тези местни '
            'часове: %s' % '; '.join(broken),
        )

    def test_the_day_offered_is_the_customers_day(self):
        """Работното време е на обекта: 17:00 значи 17:00 при клиента."""
        tz = pytz.timezone(SITE_TZ)
        for hour in (9, 15, 22):
            start, end, _now = self._sold_at(hour)
            local_end = pytz.UTC.localize(end).astimezone(tz)
            self.assertEqual(
                (local_end.hour, local_end.minute), (17, 0),
                'Продажба в %02d:00 свършва в %s местно, а обектът затваря в '
                '17:00' % (hour, local_end.strftime('%H:%M')),
            )
            local_start = pytz.UTC.localize(start).astimezone(tz)
            self.assertEqual(
                (local_start.hour, local_start.minute), (8, 0),
                'Продажба в %02d:00 започва в %s местно, а обектът отваря в '
                '08:00' % (hour, local_start.strftime('%H:%M')),
            )

    def test_the_day_is_read_when_the_sale_is_made_not_when_the_server_booted(self):
        """Един и същи сървър, два различни дни - два различни периода.

        Денят беше СТОЙНОСТ ПО ПОДРАЗБИРАНЕ на вътрешна функция, а Python я
        изчислява веднъж - при зареждането на модула. Сървър, вдигнат преди два
        дни, продаваше срещу деня на пускането си, корекцията „+1 ден" стигаше
        само за първия, и касата отказваше картата с „периодът изтича в
        миналото". Тестът пуска две продажби на два различни дни в един и същи
        процес: ако денят се вземе при зареждане, двете съвпадат.
        """
        first_start, first_end, _ = self._sold_at(10)
        tz = pytz.timezone(SITE_TZ)
        later = tz.localize(datetime.combine(date(2026, 8, 23), datetime.min.time())
                            + timedelta(hours=10))
        with freeze_time(later.astimezone(pytz.UTC).replace(tzinfo=None)):
            wiz = self.env['rfid.service.sale.wiz'].new({'service_id': self.service.id})
            wiz._onchange_service_id()
            second_start, second_end = wiz.start_date, wiz.end_date
        self.assertEqual(
            (second_start - first_start).days, 3,
            'Продажба три дни по-късно тръгва от същия ден - денят е взет при '
            'зареждане на модула, не при продажбата',
        )
        self.assertGreater(second_end, second_start)
