# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bulgaria — Attendance Overtime Rates',
    'version': '19.0.1.0.3',
    'category': 'Human Resources/Attendances',
    'summary': 'Bulgarian statutory overtime/night coefficients and public holidays',
    'author': 'Polimex',
    'website': 'https://polimex.co',
    'license': 'AGPL-3',

    # hr_attendance_late provides the dated hr.legal.rate store this module
    # seeds; hr_holidays provides Public Holidays (global resource.calendar
    # leaves) used to tell a rest day apart from an official holiday.
    'depends': ['hr_attendance_late', 'hr_holidays'],

    'data': [
        'security/ir.model.access.csv',
        'data/legal_rates.xml',
        'data/ir_cron.xml',
        'views/hr_public_holidays_views.xml',
    ],

    'demo': [
        'demo/l10n_bg_hr_attendance_overtime_rates_demo_showcase.xml',
    ],

    'installable': True,
    'auto_install': False,
}
