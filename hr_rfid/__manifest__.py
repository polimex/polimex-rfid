# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': 'RFID Access Control',
    'version': '1.15',
    'category': 'Human Resources',
    'summary': 'Manage employee access control',
    'author': 'Polimex Odoo Dev Team',
    'license': 'AGPL-3',

    'website': 'https://polimex.co/',

    'depends': [ 'base', 'hr', 'contacts' ],

    'data': [
        'security/hr_rfid_security.xml',
        'security/ir.model.access.csv',
        'data/hr_rfid_card_type_data.xml',
        'data/hr_rfid_cron_jobs.xml',
        'data/hr_rfid_system_parameters.xml',
        'data/hr_rfid_time_schedule_data.xml',
        'views/web_assets_backend.xml',
        'views/hr_department_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_rfid_view_actions.xml',
        'views/hr_rfid_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_setting_view.xml',
        'wizards/hr_rfid_wizard_views.xml',
    ],

    'qweb': [
        'static/src/xml/pivot_view_field_selection.xml',
        'static/src/xml/module_discovery_button.xml'
    ],

    # 'demo': [ ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'application': True,
    'installable': True,
    'auto_install': False,
}
