"""Who opens the daily figures (Attendances > Reporting).

The menu is meant for the attendance officer, as core's own attendance
reports are: an officer sees the people they are the attendance manager of,
an officer of all attendances sees everybody, and the figures stay as the
system computed them - only the administrator deletes them. The same three
levels core gives its overtime lines (hr_attendance/security).
"""

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged

MENUS = (
    "hr_attendance_late.menu_hr_attendance_extra",
    "hr_attendance_late.menu_hr_attendance_self_leave",
)


@tagged("post_install", "-at_install", "rfid_attendance_access")
class TestWhoSeesTheDailyFigures(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.officer = new_test_user(
            cls.env,
            login="officer_daily_figures",
            groups="base.group_user,hr_attendance.group_hr_attendance_officer",
        )
        cls.officer_of_all = new_test_user(
            cls.env,
            login="officer_all_daily_figures",
            groups="base.group_user,hr_attendance.group_hr_attendance_user",
        )
        cls.somebody = new_test_user(
            cls.env, login="somebody_daily_figures", groups="base.group_user"
        )
        Employee = cls.env["hr.employee"]
        cls.managed = Employee.create(
            {"name": "Managed By The Officer", "attendance_manager_id": cls.officer.id}
        )
        cls.other = Employee.create({"name": "Somebody Else's"})
        Extra = cls.env["hr.attendance.extra"]
        cls.managed_day = Extra.create(
            {"employee_id": cls.managed.id, "for_date": "2026-11-02"}
        )
        cls.other_day = Extra.create(
            {"employee_id": cls.other.id, "for_date": "2026-11-02"}
        )
        cls.days = cls.managed_day | cls.other_day

    def _visible(self, user, xmlid):
        menu = self.env.ref(xmlid)
        return menu.id in self.env["ir.ui.menu"].with_user(user)._visible_menu_ids()

    def _sees(self, user):
        return (
            self.env["hr.attendance.extra"]
            .with_user(user)
            .search([("id", "in", self.days.ids)])
        )

    def test_the_officer_sees_the_days_of_their_people(self):
        for xmlid in MENUS:
            self.assertTrue(self._visible(self.officer, xmlid), xmlid)
        self.assertEqual(self._sees(self.officer), self.managed_day)

    def test_the_officer_of_all_attendances_sees_everybody(self):
        for xmlid in MENUS:
            self.assertTrue(self._visible(self.officer_of_all, xmlid), xmlid)
        self.assertEqual(self._sees(self.officer_of_all), self.days)

    def test_the_officer_opens_the_badges_of_the_day(self):
        action = self.managed_day.with_user(self.officer).open_attendance_logs()
        self.assertIn(("employee_id", "=", self.managed.id), action["domain"])

    def test_the_figures_stay_as_the_system_computed_them(self):
        day = self.managed_day.with_user(self.officer)
        with self.assertRaises(AccessError):
            day.unlink()
        with self.assertRaises(AccessError):
            day.write({"for_date": "2026-11-03"})

    def test_somebody_without_attendance_rights_has_no_menu(self):
        for xmlid in MENUS:
            self.assertFalse(self._visible(self.somebody, xmlid), xmlid)
