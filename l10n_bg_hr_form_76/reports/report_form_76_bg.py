from odoo import api, models, _
from odoo.exceptions import UserError
from datetime import date, datetime, time, timedelta
import calendar
import pytz


class ReportForm76(models.AbstractModel):
    _name = 'report.l10n_bg_hr_form_76.report_form_76'
    _description = 'Form 76 Report'

    @api.model
    def vertical_text(self, text):
        return '<br/>'.join(text)

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

        # Flush ORM cache to ensure DB consistency
        self.env['hr.employee'].flush_model(['name', 'active', 'corporate_internal_number'])
        self.env['hr.version'].flush_model(['department_id', 'job_title', 'employee_id'])
        self.env['hr.leave'].flush_model(['employee_id', 'date_from', 'date_to', 'state', 'holiday_status_id'])

        # Dynamic day columns with parameterized precision
        q_dates = ','.join([
            f"MAX(CASE WHEN dates.for_date = %s THEN COALESCE("
            f"ROUND(NULLIF(att.extra_time, 0), %s)::float::text, "
            f"ROUND(NULLIF(att.actual_work_time, 0), %s)::float::text, "
            f"lt.form76_code, 'С'"
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
                ver.department_id,
                emp.name as employee_name,
                ver.job_title,
                COALESCE(emp.corporate_internal_number, '-') as corporate_id,
                {q_dates}
            FROM dates
            CROSS JOIN hr_employee emp
            JOIN hr_version ver ON ver.id = emp.current_version_id
            LEFT JOIN hr_attendance_extra att
                ON dates.for_date = att.for_date AND emp.id = att.employee_id
            LEFT JOIN hr_leave lv
                ON dates.for_date BETWEEN lv.date_from::date AND lv.date_to::date
                AND emp.id = lv.employee_id
                AND lv.state = 'validate'
            LEFT JOIN hr_leave_type lt ON lv.holiday_status_id = lt.id
            WHERE ver.department_id IN %s
                AND emp.active = TRUE
                AND emp.company_id = %s
            GROUP BY ver.department_id, emp.id, emp.corporate_internal_number,
                     emp.name, ver.job_title
            ORDER BY emp.id
        """

        params = [date_from, date_to] + day_params + [tuple(department_ids), company_id]
        self.env.cr.execute(query, params)
        rows = self.env.cr.fetchall()
        return last_day_num, rows

    def _get_holiday_map(self, employee_ids, date_from, date_to):
        """Batch извличане на работен график — празнични/почивни дни за ВСИЧКИ служители."""
        employees = self.env['hr.employee'].browse(employee_ids)
        result = {}

        # Group employees by calendar for batch processing
        calendars = {}
        for emp in employees:
            cal = emp.resource_id.calendar_id
            if cal not in calendars:
                calendars[cal] = []
            calendars[cal].append(emp)

        for cal, emps in calendars.items():
            tz = pytz.timezone(cal.tz or 'UTC')
            start_dt = tz.localize(datetime.combine(date_from, time.min))
            end_dt = tz.localize(datetime.combine(date_to, time.max))

            resources = self.env['resource.resource'].concat(*(e.resource_id for e in emps))

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
            for i, (d, dt) in enumerate(zip(sql_days, date_list)):
                a = emp_holidays.get(dt, False)
                if d != 'С' and a == 'Н':
                    # Working day hours on a holiday — count as extra
                    try:
                        extr_hours += float(d)
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

            # Calculate summary columns
            covekodni = 0
            covekochasove = 0
            covekodni_celi = 0
            for element in new_days:
                try:
                    number = float(element)
                    if number >= work_hours_daily:
                        covekodni_celi += 1
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
                'covekodni_celi': covekodni_celi,
                'otpusk_o': new_days.count('О'),
                'otpusk_m': new_days.count('М'),
                'otpusk_b': new_days.count('Б'),
                'otpusk_d': new_days.count('Д'),
                'otpusk_a': new_days.count('А'),
                'samootluchka': new_days.count('С'),
                'pochivni': new_days.count('Н'),
                'hours_summary': f"{covekochasove}/{work_days_count * work_hours_daily}",
                'extra_hours': extr_hours,
                'partial': 0,
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
