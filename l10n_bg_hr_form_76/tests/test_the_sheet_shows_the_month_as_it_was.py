# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""The attendance sheet (form 76) says what the month was.

The sheet's columns are those of the NSI template (Приложение 1, "Таблица за
отчитане явяването/неявяването на работа"): "Явяване на работа - всичко
човекодни, в т.ч. целодневен престой", "Неявявания" by letter, "Отработени
човекочасове - всичко, в т.ч. извънредни" and "Неотработени човекочасове -
частични". The person who keeps the sheet hands it to payroll and to an
inspector; every column must hold what its heading says, for the month the
sheet is about.
"""

from datetime import date

from odoo.tests.common import tagged

from .test_form_76 import TestForm76Common


@tagged("post_install", "-at_install")
class TestTheSheetShowsTheMonthAsItWas(TestForm76Common):
    def _line(self, employee, **data):
        values = {
            "report_year": 2026,
            "report_month": 3,
            "precision": 2,
            "department_ids": self.department.ids,
            "company_id": self.company.id,
            "set_hours_to": 0,
        }
        values.update(data)
        report = self.env["report.l10n_bg_hr_form_76.report_form_76"]
        lines = report._get_report_values(None, data=values)["departments"].values()
        found = [
            line
            for dept in lines
            for line in dept
            if line["employee_id"] == employee.id
        ]
        self.assertEqual(len(found), 1, "the person has one line on the sheet")
        return found[0]

    def _day(self, employee, day, **figures):
        values = {
            "employee_id": employee.id,
            "for_date": day,
            "theoretical_work_time": 8.0,
        }
        values.update(figures)
        return self.env["hr.attendance.extra"].create(values)

    # -- The sheet itself ---------------------------------------------------

    def test_hr_can_print_the_sheet_with_the_nsi_headings(self):
        """The sheet opened from the menu's wizard renders, with the person,
        the position and the NSI group headings over the hour columns."""
        self.employee_1.job_title = "Монтажник"
        wizard = self.env["hr.attendance.form76.wizard"].create(
            {
                "report_year": 2026,
                "report_month": "3",
                "department_ids": [(6, 0, self.department.ids)],
            }
        )
        report = self.env.ref("l10n_bg_hr_form_76.form_76_report")

        # The data the wizard's "Print" and "Preview" hand to the report.
        html = report._render_qweb_html(
            report.report_name, [], data=wizard._prepare_report_data()
        )[0].decode()

        for text in (
            "Иван Тестов",
            "Монтажник",
            "Отработени човекочасове",
            "Неотработени човекочасове",
            "в т.ч. целодневен престой",
        ):
            self.assertIn(text, html)

    def test_the_printed_sheet_writes_its_headings_letter_by_letter(self):
        """The printed (PDF) sheet stands its column headings upright, one
        letter per line; the line breaks are breaks, not the text "<br/>"
        printed into the heading."""
        wizard = self.env["hr.attendance.form76.wizard"].create(
            {
                "report_year": 2026,
                "report_month": "3",
                "department_ids": [(6, 0, self.department.ids)],
            }
        )
        report = self.env.ref("l10n_bg_hr_form_76.form_76_report")

        # Under tests core renders the PDF path as its HTML, report_type 'pdf'.
        printed = report._render_qweb_pdf(
            report.report_name, [], data=wizard._prepare_report_data()
        )[0].decode()

        self.assertIn("Ч<br/>а<br/>с<br/>т<br/>и<br/>ч<br/>н<br/>и", printed)
        self.assertNotIn("&lt;br", printed)

    # -- Time off from the Bulgarian catalog ---------------------------------

    def _catalog_type(self, letter):
        if "l10n_bg_form76_code" not in self.env["hr.leave.type"]._fields:
            self.skipTest("the Bulgarian time-off catalog is not installed")
        return self.env["hr.leave.type"].create(
            {
                "name": "Catalog time off %s" % letter,
                "requires_allocation": False,
                "company_id": self.company.id,
                "l10n_bg_form76_code": letter,
            }
        )

    def _time_off(self, leave_type, day_from, day_to):
        leave = self.env["hr.leave"].create(
            {
                "employee_id": self.employee_1.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": day_from,
                "request_date_to": day_to,
            }
        )
        leave.action_approve()
        if leave.state != "validate":
            leave.action_validate()
        return leave

    def test_time_off_marked_in_the_bulgarian_catalog_prints_its_letter(self):
        """HR marks a catalog time-off type with "А" on its own form; the
        sheet prints "А" on those days and counts them under "С разреш. на
        администр.", not "NA" counted nowhere."""
        self._time_off(self._catalog_type("А"), "2026-03-02", "2026-03-03")

        line = self._line(self.employee_1)

        self.assertEqual(line["days"][1:3], ["А", "А"])
        self.assertEqual(line["otpusk_a"], 2)

    def test_the_catalog_letter_wins_over_the_sheets_own(self):
        """The letter HR filled in the catalog is the type's letter even when
        the sheet's own field holds another one."""
        leave_type = self._catalog_type("Б")
        leave_type.form76_code = "О"
        self._time_off(leave_type, "2026-03-02", "2026-03-02")

        line = self._line(self.employee_1)

        self.assertEqual(line["days"][1], "Б")
        self.assertEqual((line["otpusk_b"], line["otpusk_o"]), (1, 0))

    def test_a_catalog_type_without_a_letter_keeps_the_sheets_own(self):
        """NEGATIVE: an empty letter in the catalog does not hide the letter
        set on the sheet's own field of the same type."""
        leave_type = self._catalog_type(False)
        leave_type.form76_code = "О"
        self._time_off(leave_type, "2026-03-02", "2026-03-02")

        line = self._line(self.employee_1)

        self.assertEqual(line["days"][1], "О")
        self.assertEqual(line["otpusk_o"], 1)

    # -- Worked and missed hours ---------------------------------------------

    def test_overtime_on_a_working_day_is_in_the_overtime_column(self):
        """Two hours over the schedule on a Monday are overtime as much as
        four hours on a Saturday: "в т.ч. извънредни" holds both, 6, and both
        are hours worked: Monday shows the 10 hours worked, "Всичко" is 14.

        The figures are as the attendance calculation keeps them: the hours
        inside the schedule apart from the overtime after it."""
        self._day(self.employee_1, "2026-03-09", actual_work_time=8.0, overtime=2.0)
        self._day(
            self.employee_1, "2026-03-14", theoretical_work_time=0.0, extra_time=4.0
        )

        line = self._line(self.employee_1)

        self.assertEqual(line["days"][8], "10")
        self.assertEqual(line["extra_hours"], 6.0)
        self.assertEqual(line["hours_summary"].split("/")[0], "14.0")

    def test_hours_on_a_public_holiday_are_overtime_once(self):
        """A weekday public holiday is a day off for everyone: the person who
        stayed home has "Н", not "С", and the four hours of the person who
        came are counted once, in "в т.ч. извънредни" and in "Всичко"."""
        self.env["resource.calendar.leaves"].create(
            {
                "name": "Public holiday F76",
                "calendar_id": self.company.resource_calendar_id.id,
                "resource_id": False,
                "date_from": "2026-03-03 22:00:00",
                "date_to": "2026-03-04 21:59:59",
            }
        )
        self._day(
            self.employee_1, "2026-03-04", theoretical_work_time=0.0, extra_time=4.0
        )

        worked = self._line(self.employee_1)
        stayed_home = self._line(self.employee_2)

        self.assertEqual(stayed_home["days"][3], "Н")
        self.assertEqual(worked["days"][3], "Н")
        self.assertEqual(worked["extra_hours"], 4.0)
        self.assertEqual(worked["hours_summary"].split("/")[0], "4.0")

    def test_whole_hours_print_as_whole_numbers_rounded_half_up(self):
        """With the wizard's default precision 0 the columns print "3" like
        the day cells do, and half an hour rounds up as in the cells."""
        self._day(self.employee_1, "2026-03-09", actual_work_time=8.0, overtime=2.5)

        line = self._line(self.employee_1, precision=0)

        self.assertEqual(line["days"][8], "11")
        self.assertEqual(line["extra_hours"], 3)
        self.assertIsInstance(line["extra_hours"], int)
        self.assertEqual(line["partial"], 0)
        self.assertIsInstance(line["partial"], int)

    def test_hours_missed_on_a_day_the_person_came_are_partial(self):
        """An hour late on Tuesday and half an hour left early on Wednesday
        are 1.5 unworked hours under "Частични"."""
        self._day(self.employee_1, "2026-03-10", actual_work_time=7.0, late_time=1.0)
        self._day(
            self.employee_1, "2026-03-11", actual_work_time=7.5, early_leave_time=0.5
        )

        line = self._line(self.employee_1)

        self.assertEqual(line["partial"], 1.5)

    def test_fixed_hours_take_nothing_from_the_real_day(self):
        """NEGATIVE: with the hours of every worked day replaced by 8, the
        sheet shows a full day, so neither the overtime nor the late hour of
        that day is added. A Saturday worked is not a replaced day: its four
        hours stay overtime and hours worked."""
        self._day(self.employee_1, "2026-03-09", actual_work_time=8.0, overtime=2.0)
        self._day(self.employee_1, "2026-03-10", actual_work_time=7.0, late_time=1.0)
        self._day(
            self.employee_1, "2026-03-14", theoretical_work_time=0.0, extra_time=4.0
        )

        line = self._line(self.employee_1, set_hours_to=8)

        self.assertEqual(line["days"][8:10], [8, 8])
        self.assertEqual(line["extra_hours"], 4.0)
        self.assertEqual(line["partial"], 0)
        self.assertEqual(line["hours_summary"].split("/")[0], "20.0")

    def test_a_day_of_absence_is_not_partial(self):
        """NEGATIVE: a working day with no attendance is "С", a whole day
        missed; it adds no partial hours."""
        line = self._line(self.employee_1)

        self.assertEqual(line["days"][1], "С")
        self.assertEqual(line["partial"], 0)

    def test_full_working_days_are_not_reported_as_standstill(self):
        """Two full days at work are not two days of standstill: nothing in
        the system records standstill, so "в т.ч. целодневен престой" stays
        empty for the person who keeps the sheet."""
        self._day(self.employee_1, "2026-03-09", actual_work_time=8.0)
        self._day(self.employee_1, "2026-03-11", actual_work_time=8.0, overtime=1.0)

        line = self._line(self.employee_1)

        self.assertEqual(line["covekodni"], 2)
        self.assertEqual(line["covekodni_celi"], "")

    # -- Position and department of the month --------------------------------

    def _promote_in_april(self):
        new_department = self.env["hr.department"].create(
            {
                "name": "Department from April F76",
                "company_id": self.company.id,
            }
        )
        self.employee_1.version_ids[:1].write(
            {
                "date_version": date(2026, 1, 1),
                "job_title": "Работник",
            }
        )
        self.employee_1.create_version(
            {
                "date_version": date(2026, 4, 1),
                "job_title": "Бригадир",
                "department_id": new_department.id,
            }
        )
        return new_department

    def test_the_sheet_of_march_shows_the_position_held_in_march(self):
        """Promoted on 1 April, the person is "Работник" in the March sheet
        of the old department."""
        self._promote_in_april()

        line = self._line(self.employee_1)

        self.assertEqual(line["job_title"], "Работник")
        self.assertEqual(line["department_name"], self.department.complete_name)

    def test_a_move_in_the_middle_of_the_month_is_on_the_new_departments_sheet(self):
        """Moved to another department on 20 March, the person is on that
        department's March sheet with the position held at the month's end,
        and no longer on the old department's March sheet."""
        new_department = self.env["hr.department"].create(
            {
                "name": "Department from 20 March F76",
                "company_id": self.company.id,
            }
        )
        self.employee_1.version_ids[:1].date_version = date(2026, 1, 1)
        self.employee_1.create_version(
            {
                "date_version": date(2026, 3, 20),
                "job_title": "Склададжия",
                "department_id": new_department.id,
            }
        )

        line = self._line(self.employee_1, department_ids=new_department.ids)

        self.assertEqual(line["job_title"], "Склададжия")
        self.assertEqual(len(line["days"]), 31)
        report = self.env["report.l10n_bg_hr_form_76.report_form_76"]
        _days, rows = report._get_attendance_data(
            {
                "report_year": 2026,
                "report_month": 3,
                "precision": 2,
                "department_ids": self.department.ids,
                "company_id": self.company.id,
                "set_hours_to": 0,
            }
        )
        self.assertNotIn(self.employee_1.id, [row[0] for row in rows])

    def test_the_sheet_of_april_shows_the_new_position(self):
        """NEGATIVE: the April sheet is the new department's, with the new
        position; the old department's April sheet does not list the person."""
        new_department = self._promote_in_april()

        line = self._line(
            self.employee_1, report_month=4, department_ids=new_department.ids
        )

        self.assertEqual(line["job_title"], "Бригадир")
        report = self.env["report.l10n_bg_hr_form_76.report_form_76"]
        _days, rows = report._get_attendance_data(
            {
                "report_year": 2026,
                "report_month": 4,
                "precision": 2,
                "department_ids": self.department.ids,
                "company_id": self.company.id,
                "set_hours_to": 0,
            }
        )
        self.assertNotIn(self.employee_1.id, [row[0] for row in rows])
