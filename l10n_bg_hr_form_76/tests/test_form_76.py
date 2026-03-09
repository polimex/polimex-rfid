from datetime import date, datetime, timedelta
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestForm76Common(TransactionCase):
    """Common setup for Form 76 tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.tz = 'Europe/Sofia'

        cls.company = cls.env.company
        cls.company.resource_calendar_id.tz = 'Europe/Sofia'

        # Department
        cls.department = cls.env['hr.department'].create({
            'name': 'Test Department F76',
            'company_id': cls.company.id,
        })

        # Leave types with form76 codes
        cls.leave_type_regular = cls.env['hr.leave.type'].create({
            'name': 'Regular Leave F76',
            'form76_code': 'О',
            'form76_law_reason': 'чл. 155, ал. 1 от КТ',
            'requires_allocation': False,
            'company_id': cls.company.id,
        })

        cls.leave_type_sick = cls.env['hr.leave.type'].create({
            'name': 'Sick Leave F76',
            'form76_code': 'Б',
            'form76_law_reason': 'чл. 162, ал. 1 от КТ',
            'requires_allocation': False,
            'company_id': cls.company.id,
        })

        # Employees
        cls.employee_1 = cls.env['hr.employee'].create({
            'name': 'Иван Тестов',
            'department_id': cls.department.id,
            'company_id': cls.company.id,
            'corporate_internal_number': '001',
        })

        cls.employee_2 = cls.env['hr.employee'].create({
            'name': 'Мария Тестова',
            'department_id': cls.department.id,
            'company_id': cls.company.id,
            'corporate_internal_number': '002',
        })


@tagged('post_install', '-at_install')
class TestLeaveType(TestForm76Common):
    """Test form76 fields on hr.leave.type."""

    def test_form76_code_default(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Default Code Test',
            'company_id': self.company.id,
        })
        self.assertEqual(leave_type.form76_code, 'NA')

    def test_form76_law_reason_default(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Default Reason Test',
            'company_id': self.company.id,
        })
        self.assertEqual(leave_type.form76_law_reason, 'чл. 155, ал. 1 от Кодекса на труда /КТ/')

    def test_form76_custom_code(self):
        self.assertEqual(self.leave_type_regular.form76_code, 'О')
        self.assertEqual(self.leave_type_sick.form76_code, 'Б')


@tagged('post_install', '-at_install')
class TestEmployee(TestForm76Common):
    """Test form76 fields and methods on hr.employee."""

    def test_corporate_internal_number(self):
        self.assertEqual(self.employee_1.corporate_internal_number, '001')
        self.assertEqual(self.employee_2.corporate_internal_number, '002')

    def test_f76_intervals_working_day(self):
        """Monday should be a working day."""
        # Find next Monday from today
        today = date.today()
        monday = today + timedelta(days=(7 - today.weekday()) % 7)
        if monday == today and today.weekday() != 0:
            monday += timedelta(days=7 - today.weekday())
        # Ensure it's Monday
        while monday.weekday() != 0:
            monday += timedelta(days=1)

        result = self.employee_1.f76_intervals(monday)
        self.assertFalse(result, "Monday should be a working day")

    def test_f76_intervals_weekend(self):
        """Saturday should be non-working."""
        today = date.today()
        saturday = today + timedelta(days=(5 - today.weekday()) % 7)
        if saturday <= today:
            saturday += timedelta(days=7)

        result = self.employee_1.f76_intervals(saturday)
        self.assertEqual(result, 'Н', "Saturday should be non-working")

    def test_f76_intervals_string_date(self):
        """Test with string date input."""
        today = date.today()
        saturday = today + timedelta(days=(5 - today.weekday()) % 7)
        if saturday <= today:
            saturday += timedelta(days=7)

        result = self.employee_1.f76_intervals(saturday.strftime('%Y-%m-%d'))
        self.assertEqual(result, 'Н')

    def test_f76_intervals_invalid_input(self):
        """Test with invalid input raises ValueError."""
        with self.assertRaises(ValueError):
            self.employee_1.f76_intervals(12345)


@tagged('post_install', '-at_install')
class TestWizard(TestForm76Common):
    """Test Form 76 wizard."""

    def _create_wizard(self, **kwargs):
        vals = {
            'report_year': 2026,
            'report_month': '3',
            'department_ids': [(6, 0, self.department.ids)],
        }
        vals.update(kwargs)
        return self.env['hr.attendance.form76.wizard'].create(vals)

    def test_wizard_defaults(self):
        wizard = self._create_wizard()
        self.assertEqual(wizard.precision, 0)
        self.assertEqual(wizard.set_hours_to, 0)

    def test_wizard_prepare_report_data(self):
        wizard = self._create_wizard()
        data = wizard._prepare_report_data()

        self.assertEqual(data['report_year'], 2026)
        self.assertEqual(data['report_month'], 3)
        self.assertEqual(data['department_ids'], self.department.ids)
        self.assertEqual(data['set_hours_to'], 0)
        self.assertEqual(data['precision'], 0)
        self.assertEqual(data['company_id'], self.company.id)

    def test_wizard_invalid_year(self):
        wizard = self._create_wizard(report_year=2019)
        with self.assertRaises(UserError):
            wizard._prepare_report_data()

    def test_wizard_future_year(self):
        wizard = self._create_wizard(report_year=2099)
        with self.assertRaises(UserError):
            wizard._prepare_report_data()

    def test_wizard_report_print(self):
        wizard = self._create_wizard()
        result = wizard.report_print()

        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        # Odoo may wrap report in document layout configurator
        if result.get('res_model') == 'base.document.layout':
            report_action = result.get('context', {}).get('report_action', {})
            self.assertIn('data', report_action)
        else:
            self.assertIn('data', result)

    def test_wizard_report_view_preview(self):
        wizard = self._create_wizard()
        result = wizard.report_view()

        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        self.assertEqual(result.get('report_type'), 'qweb-html')

    def test_wizard_preview_does_not_modify_db(self):
        """Preview should NOT modify the ir.actions.report record."""
        report_rec = self.env.ref('l10n_bg_hr_form_76.form_76_report')
        original_type = report_rec.report_type
        self.assertEqual(original_type, 'qweb-pdf')

        wizard = self._create_wizard()
        wizard.report_view()

        report_rec.invalidate_recordset()
        self.assertEqual(report_rec.report_type, 'qweb-pdf',
                         "Preview must not modify DB report_type")


@tagged('post_install', '-at_install')
class TestReportForm76(TestForm76Common):
    """Test Form 76 report data generation."""

    def _get_report_data(self, **kwargs):
        data = {
            'report_year': 2026,
            'report_month': 3,
            'precision': 2,
            'department_ids': self.department.ids,
            'company_id': self.company.id,
            'set_hours_to': 0,
        }
        data.update(kwargs)
        return data

    def test_get_attendance_data_returns_correct_structure(self):
        """SQL query should return rows with correct number of columns."""
        report = self.env['report.l10n_bg_hr_form_76.report_form_76']
        data = self._get_report_data()

        last_day_num, rows = report._get_attendance_data(data)

        self.assertEqual(last_day_num, 31)  # March has 31 days
        self.assertGreater(len(rows), 0, "Should find employees in department")

        # Each row: emp_id, dept_id, name, job_title, corporate_id, + day columns
        expected_cols = 5 + last_day_num
        for row in rows:
            self.assertEqual(len(row), expected_cols,
                             f"Row should have {expected_cols} columns")

    def test_get_attendance_data_february(self):
        """February should have 28 or 29 days."""
        report = self.env['report.l10n_bg_hr_form_76.report_form_76']
        data = self._get_report_data(report_month=2)

        last_day_num, rows = report._get_attendance_data(data)

        self.assertIn(last_day_num, [28, 29])

    def test_get_attendance_data_filters_by_department(self):
        """Only employees in specified department should be returned."""
        other_dept = self.env['hr.department'].create({
            'name': 'Other Dept F76',
            'company_id': self.company.id,
        })
        self.env['hr.employee'].create({
            'name': 'Друг Служител',
            'department_id': other_dept.id,
            'company_id': self.company.id,
        })

        report = self.env['report.l10n_bg_hr_form_76.report_form_76']
        data = self._get_report_data()

        _, rows = report._get_attendance_data(data)
        emp_ids = [row[0] for row in rows]

        self.assertIn(self.employee_1.id, emp_ids)
        self.assertIn(self.employee_2.id, emp_ids)
        # "Друг Служител" should NOT be in results
        for row in rows:
            self.assertNotEqual(row[2], 'Друг Служител')

    def test_get_attendance_data_company_filter(self):
        """SQL query should filter by company_id."""
        report = self.env['report.l10n_bg_hr_form_76.report_form_76']
        # Use a non-existent company_id — should return no rows
        data = self._get_report_data(company_id=99999)

        _, rows = report._get_attendance_data(data)
        self.assertEqual(len(rows), 0,
                         "No employees should match non-existent company")

    def test_get_holiday_map(self):
        """Holiday map should identify weekends correctly."""
        report = self.env['report.l10n_bg_hr_form_76.report_form_76']
        date_from = date(2026, 3, 1)
        date_to = date(2026, 3, 31)

        holiday_map = report._get_holiday_map(
            [self.employee_1.id], date_from, date_to
        )

        self.assertIn(self.employee_1.id, holiday_map)
        emp_days = holiday_map[self.employee_1.id]
        self.assertEqual(len(emp_days), 31)

        # March 1, 2026 is Sunday → 'Н'
        self.assertEqual(emp_days[date(2026, 3, 1)], 'Н',
                         "Sunday should be non-working")
        # March 2, 2026 is Monday → False (working day)
        self.assertFalse(emp_days[date(2026, 3, 2)],
                         "Monday should be working day")

    def test_get_holiday_map_multiple_employees(self):
        """Holiday map should handle multiple employees."""
        report = self.env['report.l10n_bg_hr_form_76.report_form_76']
        emp_ids = [self.employee_1.id, self.employee_2.id]
        date_from = date(2026, 3, 1)
        date_to = date(2026, 3, 31)

        holiday_map = report._get_holiday_map(emp_ids, date_from, date_to)

        self.assertEqual(len(holiday_map), 2)
        self.assertIn(self.employee_1.id, holiday_map)
        self.assertIn(self.employee_2.id, holiday_map)

    def test_get_report_values_structure(self):
        """Report values should contain all required keys."""
        report = self.env['report.l10n_bg_hr_form_76.report_form_76']
        data = self._get_report_data()

        values = report._get_report_values(None, data=data)

        required_keys = [
            'departments', 'doc_model', 'last_day_num',
            'vertical_text', 'report_month', 'report_year',
        ]
        for key in required_keys:
            self.assertIn(key, values, f"Missing key: {key}")

        self.assertEqual(values['report_month'], 3)
        self.assertEqual(values['report_year'], 2026)
        self.assertEqual(values['last_day_num'], 31)

    def test_get_report_values_line_structure(self):
        """Each line in departments should have all named keys."""
        report = self.env['report.l10n_bg_hr_form_76.report_form_76']
        data = self._get_report_data()

        values = report._get_report_values(None, data=data)

        self.assertGreater(len(values['departments']), 0)

        expected_line_keys = [
            'employee_id', 'department_name', 'name', 'job_title',
            'corporate_id', 'days', 'covekodni', 'covekodni_celi',
            'otpusk_o', 'otpusk_m', 'otpusk_b', 'otpusk_d', 'otpusk_a',
            'samootluchka', 'pochivni', 'hours_summary', 'extra_hours',
            'partial',
        ]

        for dept_name, lines in values['departments'].items():
            for line in lines:
                for key in expected_line_keys:
                    self.assertIn(key, line, f"Line missing key: {key}")

    def test_get_report_values_no_data_raises(self):
        """Report without data should raise UserError."""
        report = self.env['report.l10n_bg_hr_form_76.report_form_76']

        with self.assertRaises(UserError):
            report._get_report_values(None, data=None)

    def test_get_report_values_with_leave(self):
        """Approved leave should appear with correct form76 code."""
        # Create an approved leave for employee_1
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_1.id,
            'holiday_status_id': self.leave_type_regular.id,
            'request_date_from': '2026-03-02',
            'request_date_to': '2026-03-06',
        })
        leave.action_approve()

        report = self.env['report.l10n_bg_hr_form_76.report_form_76']
        data = self._get_report_data()

        _, rows = report._get_attendance_data(data)

        # Find employee_1 row
        emp_row = None
        for row in rows:
            if row[0] == self.employee_1.id:
                emp_row = row
                break

        self.assertIsNotNone(emp_row, "Employee should be in results")

        # Day columns start at index 5
        # March 2 = day 2 = index 5+1 = 6
        # The leave should show 'О' code for workdays in the leave period
        day_2 = emp_row[6]  # March 2 (Monday)
        self.assertEqual(day_2, 'О',
                         "Approved regular leave should show 'О' code")

    def test_vertical_text(self):
        """vertical_text should join characters with <br/>."""
        report = self.env['report.l10n_bg_hr_form_76.report_form_76']
        result = report.vertical_text('АБВ')
        self.assertEqual(result, 'А<br/>Б<br/>В')

    def test_set_hours_to_replaces_actual(self):
        """When set_hours_to > 0, actual hours should be replaced."""
        report = self.env['report.l10n_bg_hr_form_76.report_form_76']
        data = self._get_report_data(set_hours_to=8)

        values = report._get_report_values(None, data=data)

        # With set_hours_to=8, working days should show 8
        for dept_name, lines in values['departments'].items():
            for line in lines:
                for day_val in line['days']:
                    if isinstance(day_val, (int, float)) and day_val > 0:
                        self.assertEqual(day_val, 8,
                                         "set_hours_to should replace actual hours")


@tagged('post_install', '-at_install')
class TestHolidayRequestReport(TestForm76Common):
    """Test the holiday request (Молба за отпуск) report."""

    def test_report_action_exists(self):
        """Holiday request report action should exist."""
        report = self.env.ref(
            'l10n_bg_hr_form_76.action_report_hr_holidays_request',
            raise_if_not_found=False,
        )
        self.assertIsNotNone(report)
        self.assertEqual(report.model, 'hr.leave')
        self.assertEqual(report.report_type, 'qweb-pdf')

    def test_form76_report_action_exists(self):
        """Form 76 report action should exist."""
        report = self.env.ref(
            'l10n_bg_hr_form_76.form_76_report',
            raise_if_not_found=False,
        )
        self.assertIsNotNone(report)
        self.assertEqual(report.report_type, 'qweb-pdf')
