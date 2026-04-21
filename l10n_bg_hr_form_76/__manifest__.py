# noinspection PyStatementEffect
{
    'name': 'Attendance Form 76 Bulgaria',
    'version': '19.0.1.0.2',
    'category': 'Human Resources',
    'summary': 'Form 76 for Bulgaria',
    'author': 'Polimex Holding Ltd.',
    'license': 'AGPL-3',

    'website': 'https://polimex.co',

    'depends': ['hr_attendance_late', 'hr_holidays'],

    'data': [
        'security/ir.model.access.csv',
        'data/hr_leave_type.xml',
        'data/paper_format.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_employee.xml',
        'reports/hr_holidays_request.xml',
        'reports/report_form_76_bg.xml',
        'wizards/report_form_76_wizard.xml',
    ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'installable': True,
    'auto_install': False,
}
