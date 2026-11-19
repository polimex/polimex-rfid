from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from datetime import date, datetime, time, timedelta
import calendar
import pytz
from collections import defaultdict
from markupsafe import Markup

from ..models.hr_employee import PUBLIC_HOLIDAYS

# A day outside the person's contract: before they were hired or after they
# left. The NSI sheet leaves it blank - it is neither attendance nor absence.
OUT_OF_CONTRACT = ''


def _month_days(first, last):
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


class ReportForm76(models.AbstractModel):
    _name = 'report.l10n_bg_hr_form_76.report_form_76'
    _description = 'Form 76 Report'

    @api.model
    def vertical_text(self, text):
        # One letter per line for the printed headers. The template prints it
        # with t-out, which escapes a plain str: the line breaks must be
        # markup and the letters escaped text.
        return Markup('<br/>').join(text)

    def _get_attendance_data(self, data):
        """Извлича данни от hr_attendance_extra и hr_leave с параметризиран SQL."""
        report_year = data['report_year']
        report_month = data['report_month']
        precision = data['precision']
        department_ids = data['department_ids']
        company_id = data.get('company_id', self.env.company.id)
        _, last_day_num = calendar.monthrange(report_year, report_month)

        date_from = date(report_year, report_month, 1)
        date_to = date(report_year, report_month, last_day_num)

        # Who is on the sheet: everybody in contract on at least one day of
        # the month, archived or not, as core counts it
        # (hr.employee._get_versions_with_contract_overlap_with_period) - the
        # person who left on the 10th and the one hired on the 20th are on
        # their month's sheet, nobody hired later is. A person with no
        # contract dates at all has no period to go by and is on every sheet
        # while active (core's _get_resource_without_contract).
        # Archived people are looked for, archived versions are not: the days
        # of the sheet come from the active versions (core's
        # _get_contracts_valid_periods), so the list goes by the same ones.
        company_employees = self.env['hr.employee'].sudo().with_context(active_test=False).search(
            [('company_id', '=', company_id)]).with_context(active_test=True)
        employees = (
            company_employees._get_versions_with_contract_overlap_with_period(date_from, date_to).employee_id
            | company_employees.filtered('active').resource_id._get_resource_without_contract().employee_id
        )
        # The sheet of a past month shows the person's department and position
        # of that month: the version in force on its last day, as core picks
        # it (hr.employee._get_version), not the one in force today.
        month_versions = {employee.id: employee._get_version(date_to) for employee in employees}
        month_versions = {
            employee_id: version for employee_id, version in month_versions.items()
            if version.department_id.id in department_ids
        }
        if not month_versions:
            return last_day_num, []

        # Flush ORM cache to ensure DB consistency
        self.env['hr.employee'].flush_model(['name', 'active', 'corporate_internal_number'])
        self.env['hr.leave'].flush_model(['employee_id', 'request_date_from', 'request_date_to', 'date_from', 'date_to', 'state', 'holiday_status_id'])
        self.env['hr.leave.type'].flush_model()

        # The Bulgarian time-off catalog (l10n_bg_hr_holidays) carries its own
        # form 76 letter on the same time-off type; the one HR filled in there
        # is the type's letter, ours (always set, 'NA' by default) otherwise.
        code_sql = (
            "COALESCE(NULLIF(lt.l10n_bg_form76_code, ''), lt.form76_code)"
            if 'l10n_bg_form76_code' in self.env['hr.leave.type']._fields
            else "lt.form76_code"
        )

        # Dynamic day columns with parameterized precision. A working day
        # shows every hour worked that day: the daily figures keep the hours
        # inside the schedule (actual_work_time) apart from the overtime after
        # it (hr_attendance_late, get_work_time_details).
        q_dates = ','.join([
            f"MAX(CASE WHEN dates.for_date = %s THEN COALESCE("
            f"ROUND(NULLIF(att.extra_time, 0), %s)::float::text, "
            f"ROUND(NULLIF(att.actual_work_time + COALESCE(att.overtime, 0), 0), %s)::float::text, "
            f"{code_sql}, 'С'"
            f") END) as day_{i}"
            for i in range(1, last_day_num + 1)
        ])

        # Build params for each day column
        day_params = []
        for i in range(1, last_day_num + 1):
            day_date = date(report_year, report_month, i)
            day_params.extend([day_date, precision, precision])

        query = f"""
            WITH dates AS (
                SELECT generate_series(%s::date, %s::date, '1 day'::interval)::date as for_date
            )
            SELECT
                emp.id as employee_id,
                emp.name as employee_name,
                COALESCE(emp.corporate_internal_number, '-') as corporate_id,
                {q_dates}
            FROM dates
            CROSS JOIN hr_employee emp
            LEFT JOIN hr_attendance_extra att
                ON dates.for_date = att.for_date AND emp.id = att.employee_id
            LEFT JOIN hr_leave lv
                -- The days the leave was asked for, as the person counts
                -- them; date_from::date is the UTC date of a moment, kept
                -- only for a leave that carries no asked-for days.
                ON dates.for_date BETWEEN COALESCE(lv.request_date_from, lv.date_from::date)
                                      AND COALESCE(lv.request_date_to, lv.date_to::date)
                AND emp.id = lv.employee_id
                AND lv.state = 'validate'
            LEFT JOIN hr_leave_type lt ON lv.holiday_status_id = lt.id
            WHERE emp.id IN %s
            GROUP BY emp.id, emp.corporate_internal_number, emp.name
            ORDER BY emp.id
        """

        params = [date_from, date_to] + day_params + [tuple(month_versions)]
        self.env.cr.execute(query, params)
        rows = []
        for employee_id, name, corporate_id, *days in self.env.cr.fetchall():
            version = month_versions[employee_id]
            rows.append((employee_id, version.department_id.id, name,
                         version.job_title, corporate_id, *days))
        return last_day_num, rows

    def _get_holiday_map(self, employee_ids, date_from, date_to):
        """Each day of the month of every person on the sheet: 'Н' for a day
        off or a public holiday, False for a working day, OUT_OF_CONTRACT for
        a day outside the person's contract.

        The days off of a past month are those of the working schedule in
        force then: core keeps, per person, which schedule was valid over
        which part of the period - the schedule of each contract version, and
        for a person without contract dates the current one over the whole
        period (resource.resource._get_calendars_validity_within_period). A
        day no contract covers is in no schedule's period.
        """
        employees = self.env['hr.employee'].browse(employee_ids)
        result = {
            employee_id: dict.fromkeys(_month_days(date_from, date_to), OUT_OF_CONTRACT)
            for employee_id in employee_ids
        }

        # The days are read in the person's own zone (hr.employee._local_tz,
        # the one the daily figures in the same report are filed under).
        for zone, emps in employees.grouped(lambda emp: emp._local_tz()).items():
            tz = pytz.timezone(zone)
            start_dt = tz.localize(datetime.combine(date_from, time.min))
            end_dt = tz.localize(datetime.combine(date_to, time.max))
            validity = emps.resource_id.sudo()._get_calendars_validity_within_period(start_dt, end_dt)

            # A contract version without a schedule (fully flexible) has no
            # days off of its own; the sheet reads them from the company's
            # schedule, as core does for a resource without one
            # (resource.resource._get_calendars_validity_within_period).
            periods_per_schedule = defaultdict(list)
            for emp in emps:
                for version_schedule, periods in validity[emp.resource_id.id].items():
                    schedule = version_schedule or emp.company_id.resource_calendar_id
                    periods_per_schedule[schedule].append((emp, periods))

            for schedule, emp_periods in periods_per_schedule.items():
                # Batch calls - ONE per schedule, not per person per day.
                # Public holidays are read per person, so a holiday of another
                # company stays out (PUBLIC_HOLIDAYS).
                schedule_resources = self.env['hr.employee'].concat(
                    *(emp for emp, _periods in emp_periods)).resource_id
                attendance_intervals = schedule._attendance_intervals_batch(
                    start_dt, end_dt, schedule_resources)
                public_holidays = schedule._leave_intervals_batch(
                    start_dt, end_dt, resources=schedule_resources, domain=PUBLIC_HOLIDAYS)
                for emp, periods in emp_periods:
                    day_map = result[emp.id]
                    for valid_from, valid_to, _meta in periods:
                        for current in _month_days(valid_from.astimezone(tz).date(),
                                                   valid_to.astimezone(tz).date()):
                            day_start = tz.localize(datetime.combine(current, time.min))
                            day_end = tz.localize(datetime.combine(current, time.max))
                            has_global_leave = any(
                                s <= day_end and e >= day_start
                                for s, e, _meta in public_holidays[emp.resource_id.id])
                            has_attendance = any(
                                s <= day_end and e >= day_start
                                for s, e, _meta in attendance_intervals[emp.resource_id.id])
                            day_map[current] = 'Н' if has_global_leave or not has_attendance else False

        return result

    def _get_part_day_leave_hours(self, employee_ids, date_from, date_to):
        """{(employee id, day): hours} of approved time off that covers only
        part of the person's working day.

        The hours of a time off fall on the days of its schedule as core
        counts its duration (resource.mixin._list_work_time_per_day, the
        helper of hr.leave._get_durations): a leave from Monday afternoon to
        Wednesday morning has a part of Monday and of Wednesday, and all of
        Tuesday. A day the time off covers whole is a day of leave, not
        partial hours - whatever the time-off type's unit.
        """
        result = defaultdict(float)
        # The leave's moments are UTC; a day either side catches every zone,
        # the days themselves are then kept to the month.
        month_start = datetime.combine(date_from - timedelta(days=1), time.min)
        month_end = datetime.combine(date_to + timedelta(days=1), time.max)
        leaves = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', employee_ids), ('state', '=', 'validate'),
            ('date_from', '<=', month_end), ('date_to', '>=', month_start),
            '|', ('request_unit_half', '=', True), ('request_unit_hours', '=', True),
        ])
        for leave in leaves:
            employee = leave.employee_id.with_context(compute_leaves=False)
            schedule = leave.resource_calendar_id or employee.resource_calendar_id or employee.company_id.resource_calendar_id
            tz = pytz.timezone(employee._local_tz())
            leave_hours = employee._list_work_time_per_day(
                leave.date_from, leave.date_to, calendar=schedule)[employee.id]
            if not leave_hours:
                continue
            day_hours = dict(employee._list_work_time_per_day(
                tz.localize(datetime.combine(leave_hours[0][0], time.min)),
                tz.localize(datetime.combine(leave_hours[-1][0], time.max)),
                calendar=schedule)[employee.id])
            for day, hours in leave_hours:
                if date_from <= day <= date_to and float_compare(
                        hours, day_hours.get(day, 0.0), precision_digits=2) < 0:
                    result[employee.id, day] += hours
        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            raise UserError(_("No data for report!"))

        report_year = data['report_year']
        report_month = data['report_month']
        last_day_num, rows = self._get_attendance_data(data)
        work_hours_daily = data['set_hours_to'] if data['set_hours_to'] > 0 else 8

        # Build date range
        date_from = date(report_year, report_month, 1)
        date_to = date(report_year, report_month, last_day_num)
        date_list = [date_from + timedelta(days=i) for i in range(last_day_num)]

        # Batch holiday map — replaces N+1 f76_intervals calls
        employee_ids = [row[0] for row in rows]
        holiday_map = self._get_holiday_map(employee_ids, date_from, date_to)

        # Resolve department names via ORM (handles translations and complete_name)
        dept_ids = list({row[1] for row in rows if row[1]})
        dept_name_map = {}
        if dept_ids:
            depts = self.env['hr.department'].browse(dept_ids)
            dept_name_map = {d.id: d.complete_name for d in depts}

        # Overtime on a working day belongs in "в т.ч. извънредни", and the
        # scheduled hours not worked on a day the person came in
        # "Неотработени човекочасове: частични" (НСИ, form 76, appendix 1).
        # With the hours replaced by a fixed figure the sheet shows that
        # figure for the day, so neither is taken from the real day.
        # The scheduled hours not worked are those the person owed
        # (theoretical_work_time: the schedule without their own time off)
        # minus those worked inside the schedule (actual_work_time) - not
        # the late arrival and early leave, which are measured from the
        # schedule's first start and last end and so count a lunch break
        # and a morning off as lateness. Approved time off for part of the
        # day is unworked time too - NSI does not count as worked
        # "неотработените часове поради ползването на платен или неплатен
        # отпуск" (НСИ, Labour_Method_1.1) - and is added from the time off.
        day_figures = {}
        part_day_leave_hours = {}
        if data['set_hours_to'] <= 0 and employee_ids:
            for figure in self.env['hr.attendance.extra'].sudo().search_read(
                    [('employee_id', 'in', employee_ids),
                     ('for_date', '>=', date_from), ('for_date', '<=', date_to)],
                    ['employee_id', 'for_date', 'overtime', 'theoretical_work_time', 'actual_work_time']):
                day_figures[figure['employee_id'][0], figure['for_date']] = figure
            part_day_leave_hours = self._get_part_day_leave_hours(employee_ids, date_from, date_to)
        precision = data['precision']

        def day_hours_rounded(value):
            # Each day is rounded as its cell is (SQL ROUND: half up), so a
            # total column agrees with the cells it sums.
            return float_round(value, precision_digits=precision)

        def shown(value):
            # Whole hours print as the cells do: "8", not "8.0".
            rounded = float_round(value, precision_digits=precision)
            return int(rounded) if precision == 0 else rounded

        # Process rows into named dicts
        departments = {}
        for row in rows:
            emp_id = row[0]
            dept_id = row[1]
            dept_name = dept_name_map.get(dept_id, _('No Department'))
            emp_name = row[2]
            job_title = row[3]
            corporate_id = row[4]
            sql_days = list(row[5:])
            emp_holidays = holiday_map[emp_id]

            # Merge SQL data with holiday calendar
            new_days = []
            extr_hours = 0
            off_day_hours = 0
            partial_hours = 0
            for d, dt in zip(sql_days, date_list, strict=True):
                a = emp_holidays[dt]
                if d == 'С' and a == OUT_OF_CONTRACT:
                    # Not employed that day: blank, not an absence.
                    new_days.append(OUT_OF_CONTRACT)
                elif d != 'С' and a == 'Н':
                    # Working day hours on a holiday — count as extra
                    try:
                        off_day_hours += float(d)
                    except (ValueError, TypeError):
                        pass
                    new_days.append('Н')
                else:
                    day_hours = None
                    try:
                        day_hours = float(d)
                    except (ValueError, TypeError):
                        pass
                    if day_hours is not None and data['set_hours_to'] > 0:
                        new_days.append(data['set_hours_to'])
                    else:
                        new_days.append((d != 'С' and d) or a or d)
                    figure = day_figures.get((emp_id, dt)) if day_hours is not None else None
                    if figure:
                        extr_hours += day_hours_rounded(figure['overtime'])
                        partial_hours += day_hours_rounded(
                            max(0.0, figure['theoretical_work_time'] - figure['actual_work_time'])
                            + part_day_leave_hours.get((emp_id, dt), 0.0))
            # Hours on days off and holidays are overtime too, and, like the
            # overtime of a working day, part of the hours worked: "в т.ч.
            # извънредни" is a part of "Всичко".
            extr_hours += off_day_hours

            # Calculate summary columns
            covekodni = 0
            covekochasove = off_day_hours
            for element in new_days:
                try:
                    number = float(element)
                    covekodni += 1
                    if data['precision'] != 0:
                        covekochasove += number
                    else:
                        covekochasove += int(number)
                except (ValueError, TypeError):
                    pass

            # The norm counts only the working days of the person's contract.
            work_days_count = len(new_days) - new_days.count('Н') - new_days.count(OUT_OF_CONTRACT)
            line = {
                'employee_id': emp_id,
                'department_name': dept_name,
                'name': emp_name,
                'job_title': job_title,
                'corporate_id': corporate_id,
                'days': new_days,
                'covekodni': covekodni,
                # "в т.ч. целодневен престой": days of standstill the employer
                # caused. Nothing in the system records them, so the column
                # stays empty for the person who keeps the sheet to fill in;
                # a count of full working days here read as idle days.
                'covekodni_celi': '',
                'otpusk_o': new_days.count('О'),
                'otpusk_m': new_days.count('М'),
                'otpusk_b': new_days.count('Б'),
                'otpusk_d': new_days.count('Д'),
                'otpusk_a': new_days.count('А'),
                'samootluchka': new_days.count('С'),
                'pochivni': new_days.count('Н'),
                'hours_summary': f"{shown(covekochasove)}/{work_days_count * work_hours_daily}",
                'extra_hours': shown(extr_hours),
                'partial': shown(partial_hours),
            }

            if dept_name not in departments:
                departments[dept_name] = []
            departments[dept_name].append(line)

        return {
            'departments': departments,
            'doc_model': self._name,
            'last_day_num': last_day_num,
            'vertical_text': self.vertical_text,
            'report_month': report_month,
            'report_year': report_year,
        }
