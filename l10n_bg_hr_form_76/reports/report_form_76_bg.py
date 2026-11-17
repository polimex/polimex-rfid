from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools import float_round
from datetime import date, datetime, time, timedelta
import calendar
import pytz
from markupsafe import Markup


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

        # The sheet of a past month shows the person's department and position
        # of that month: the version in force on its last day, as core picks
        # it (hr.employee._get_version), not the one in force today.
        month_versions = {
            employee.id: employee._get_version(date_to)
            for employee in self.env['hr.employee'].sudo().search([('company_id', '=', company_id)])
        }
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
        """Batch извличане на работен график — празнични/почивни дни за ВСИЧКИ служители."""
        employees = self.env['hr.employee'].browse(employee_ids)
        result = {}

        # Group employees by calendar for batch processing - and by the zone
        # their days are read in (hr.employee._local_tz, the one the daily
        # figures in the same report are filed under).
        groups = employees.grouped(
            lambda emp: (emp.resource_id.calendar_id, emp._local_tz()))

        for (cal, zone), emps in groups.items():
            tz = pytz.timezone(zone)
            start_dt = tz.localize(datetime.combine(date_from, time.min))
            end_dt = tz.localize(datetime.combine(date_to, time.max))

            resources = emps.resource_id

            # Batch calls — ONE per calendar, not per employee per day
            attendance_intervals = cal._attendance_intervals_batch(start_dt, end_dt, resources)
            leave_intervals = cal._leave_intervals_batch(start_dt, end_dt)

            # Global leaves are under key False (no specific resource)
            global_leaves = leave_intervals[False]

            for emp in emps:
                emp_intervals = attendance_intervals[emp.resource_id.id]
                day_map = {}
                current = date_from
                while current <= date_to:
                    day_start = tz.localize(datetime.combine(current, time.min))
                    day_end = tz.localize(datetime.combine(current, time.max))

                    # Check if any global leave covers this day
                    has_global_leave = any(
                        s <= day_end and e >= day_start
                        for s, e, _meta in global_leaves
                    )
                    # Check if employee has attendance scheduled this day
                    has_attendance = any(
                        s <= day_end and e >= day_start
                        for s, e, _meta in emp_intervals
                    )

                    if has_global_leave or not has_attendance:
                        day_map[current] = 'Н'
                    else:
                        day_map[current] = False

                    current += timedelta(days=1)
                result[emp.id] = day_map

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
        # hours missed on a day the person came (late arrival, early leave)
        # in "Неотработени човекочасове: частични" (НСИ, form 76, appendix 1).
        # With the hours replaced by a fixed figure the sheet shows that
        # figure for the day, so neither is taken from the real day.
        day_figures = {}
        if data['set_hours_to'] <= 0 and employee_ids:
            for figure in self.env['hr.attendance.extra'].sudo().search_read(
                    [('employee_id', 'in', employee_ids),
                     ('for_date', '>=', date_from), ('for_date', '<=', date_to)],
                    ['employee_id', 'for_date', 'overtime', 'late_time', 'early_leave_time']):
                day_figures[figure['employee_id'][0], figure['for_date']] = figure
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
            emp_holidays = holiday_map.get(emp_id, {})

            # Merge SQL data with holiday calendar
            new_days = []
            extr_hours = 0
            off_day_hours = 0
            partial_hours = 0
            for d, dt in zip(sql_days, date_list, strict=True):
                a = emp_holidays.get(dt, False)
                if d != 'С' and a == 'Н':
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
                            figure['late_time'] + figure['early_leave_time'])
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

            work_days_count = len(new_days) - new_days.count('Н')
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
