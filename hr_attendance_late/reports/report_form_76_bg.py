# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError


class ReportForm76(models.AbstractModel):
    _name = 'report.form76_bg'
    _description = 'Form 76 Report'

    def _lines(self, data, partner):
        query = """
            WITH dates AS (
                SELECT DATE(generate_series(
                    '2023-05-01'::timestamp,
                    '2023-05-31'::timestamp,
                    '1 day'::interval
                )) as for_date
            ), emp AS (
                SELECT DISTINCT employee_id
                FROM public.hr_attendance_extra
            )
            SELECT
                emp.employee_id,
                MAX(CASE WHEN dates.for_date = '2023-05-01' THEN COALESCE(hr_attendance_extra.actual_work_time::char, hr_leave.holiday_type, 'O') END) as "1",
                MAX(CASE WHEN dates.for_date = '2023-05-02' THEN COALESCE(hr_attendance_extra.actual_work_time::char, hr_leave.holiday_type, 'O') END) as "2",
                MAX(CASE WHEN dates.for_date = '2023-05-03' THEN COALESCE(hr_attendance_extra.actual_work_time::char, hr_leave.holiday_type, 'O') END) as "3"
            FROM
                dates
            CROSS JOIN emp
            LEFT JOIN public.hr_attendance_extra ON dates.for_date = hr_attendance_extra.for_date
                AND emp.employee_id = hr_attendance_extra.employee_id
            LEFT JOIN public.hr_leave ON dates.for_date BETWEEN hr_leave.date_from AND hr_leave.date_to
                AND emp.employee_id = hr_leave.employee_id
            GROUP BY
                emp.employee_id
            ORDER BY
                emp.employee_id;    
        """

    @api.model
    def _get_report_values(self, docids, data=None):
        pass
