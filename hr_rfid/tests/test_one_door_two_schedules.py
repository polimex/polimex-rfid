# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Един човек, една врата, два различни графика - системата трябва да откаже.

Бизнес правилото: контролерът пази ЕДИН график за двойката карта-врата. Ако
човек попадне в две групи за достъп, които отварят СЪЩАТА врата по РАЗЛИЧНИ
графици, няма верен отговор кой от двата да се изпрати - записът се отказва и
човек решава. Правилото важи еднакво за служител и за контакт.

Тестът работи с ИЗКЛЮЧЕН ключ `hr_rfid.raise_if_duplicate_doors`, и това е
същината му. Включен (както е по подразбиране), той отказва една врата през
две групи изобщо, каквито и да са графиците - и тогава маскира всичко.
Изключен е разрешено човек да държи една врата през няколко групи, и тогава
ЕДИНСТВЕНОТО, което стои между инсталацията и два противоречиви графика на един
контролер, е проверката тук. Тест, писан при включен ключ, минава и върху
напълно мъртва проверка - доказва чуждия гард, не този.

Защо съществува: при контактите проверката беше мъртва - вътрешният цикъл
броеше втората група, но я четеше от индекса на ПЪРВАТА, значи всяка група се
сравняваше със себе си и графиците винаги съвпадаха. Близнакът при служителите
беше поправен, при контактите остана. Нито един от двата нямаше тест.
"""
from odoo import exceptions
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.tests.common import RFIDAppCase

#: Кой логва оплакването за дублирана врата в разрешаващия режим.
DUPLICATE_DOOR_LOGGER = 'odoo.addons.hr_rfid.models.hr_rfid_access_group'


@tagged('standard', 'at_install', 'rfid', 'rfid_access_group', 'rfid_ts_clash')
class TestOneDoorTwoSchedules(RFIDAppCase):

    def setUp(self):
        super().setUp()
        # Разрешаващият режим: една врата през няколко групи е позволена и само
        # се докладва. Точно тук проверката за графиците е единствената защита.
        self.env['ir.config_parameter'].sudo().set_param(
            'hr_rfid.raise_if_duplicate_doors', 'False')
        ctrl = self.env['hr.rfid.ctrl'].create({
            'name': 'Ctrl TS Clash',
            'ctrl_id': 98,
            'webstack_id': self.test_webstack_10_3_id.id,
            'hw_version': '12',
            'serial_number': '998',
            'sw_version': '030',
            'mode': 1,
            'inputs': 1,
            'outputs': 1,
            'readers': 1,
        })
        # Вратата тук няма своя фирма - тя дойде с мултифирменото по-късно;
        # фирмата ѝ се извежда от модула през контролера.
        self.door = self.env['hr.rfid.door'].create({
            'name': 'Shared Door',
            'number': 1,
            'controller_id': ctrl.id,
        })
        self.env['hr.rfid.reader'].create({
            'name': 'R1',
            'number': 1,
            'reader_type': '0',
            'mode': '01',
            'controller_id': ctrl.id,
            'door_id': self.door.id,
        })
        schedules = self.env['hr.rfid.time.schedule'].search(
            [('number', '!=', 0), ('company_id', '=', self.test_company_id)],
            order='number', limit=2)
        self.assertEqual(
            len(schedules), 2,
            'Тестът иска два РАЗЛИЧНИ графика, за да има изобщо сблъсък')
        self.morning, self.evening = schedules[0], schedules[1]

    def _group_on_the_door(self, name, schedule):
        """Група за достъп, която отваря общата врата по подадения график."""
        group = self.env['hr.rfid.access.group'].create({
            'name': name,
            'company_id': self.test_company_id,
        })
        self.env['hr.rfid.access.group.door.rel'].create({
            'access_group_id': group.id,
            'door_id': self.door.id,
            'time_schedule_id': schedule.id,
        })
        # Служителят получава само групи, разрешени за отдела му - това е
        # отделно правило и не бива да се меси в проверявания тук сблъсък.
        self.test_department_id.write({
            'hr_rfid_allowed_access_groups': [(4, group.id, 0)]})
        return group

    def _both_groups_named(self, message, first, second):
        """Съобщението на проверката за графици назовава ДВЕТЕ групи.

        Така тестът не може да мине заради друг гард: оплакването за дублирана
        врата назовава човека и вратата, но не и двете групи.
        """
        return first.name in message and second.name in message

    # ── контакт ───────────────────────────────────────────────

    def test_a_contact_cannot_hold_one_door_on_two_schedules(self):
        morning = self._group_on_the_door('Doorman morning', self.morning)
        evening = self._group_on_the_door('Doorman evening', self.evening)
        self.test_partner.write({
            'hr_rfid_access_group_ids': [(0, 0, {'access_group_id': morning.id})],
        })
        with self.assertRaises(
                exceptions.ValidationError,
                msg='Контактът получи една врата по два различни графика и '
                    'системата не каза нищо - контролерът ще пази единия '
                    'график, а човекът ще се оплаче от другия') as caught:
            self.test_partner.write({
                'hr_rfid_access_group_ids': [
                    (0, 0, {'access_group_id': evening.id})],
            })
        self.assertTrue(
            self._both_groups_named(str(caught.exception), morning, evening),
            'Отказът дойде от друга проверка: съобщението не назовава двете '
            'групи, чиито графици се разминават - %s' % caught.exception)

    def test_a_contact_may_hold_one_door_twice_on_the_same_schedule(self):
        """Съвпадащите графици остават разрешени - иначе това е забрана, не защита."""
        first = self._group_on_the_door('Doorman A', self.morning)
        second = self._group_on_the_door('Doorman B', self.morning)
        with self.assertLogs(DUPLICATE_DOOR_LOGGER, level='ERROR'):
            self.test_partner.write({
                'hr_rfid_access_group_ids': [
                    (0, 0, {'access_group_id': first.id}),
                    (0, 0, {'access_group_id': second.id}),
                ],
            })
        self.assertIn(
            second, self.test_partner.hr_rfid_access_group_ids.mapped(
                'access_group_id'),
            'Проверката отказа съвпадащи графици - тогава тя не пази правилото, '
            'а просто забранява втора група')

    # ── служител ──────────────────────────────────────────────

    def test_an_employee_cannot_hold_one_door_on_two_schedules(self):
        morning = self._group_on_the_door('Shift morning', self.morning)
        evening = self._group_on_the_door('Shift evening', self.evening)
        self.test_employee_id.write({
            'hr_rfid_access_group_ids': [(0, 0, {'access_group_id': morning.id})],
        })
        with self.assertRaises(
                exceptions.ValidationError,
                msg='Служителят получи една врата по два различни графика без '
                    'нито една дума за това') as caught:
            self.test_employee_id.write({
                'hr_rfid_access_group_ids': [
                    (0, 0, {'access_group_id': evening.id})],
            })
        self.assertTrue(
            self._both_groups_named(str(caught.exception), morning, evening),
            'Отказът дойде от друга проверка, не от разминаването на графиците '
            '- %s' % caught.exception)

    def test_an_employee_may_hold_one_door_twice_on_the_same_schedule(self):
        first = self._group_on_the_door('Shift A', self.morning)
        second = self._group_on_the_door('Shift B', self.morning)
        with self.assertLogs(DUPLICATE_DOOR_LOGGER, level='ERROR'):
            self.test_employee_id.write({
                'hr_rfid_access_group_ids': [
                    (0, 0, {'access_group_id': first.id}),
                    (0, 0, {'access_group_id': second.id}),
                ],
            })
        self.assertIn(
            second, self.test_employee_id.hr_rfid_access_group_ids.mapped(
                'access_group_id'),
            'Съвпадащите графици бяха отказани - защитата е станала забрана')
