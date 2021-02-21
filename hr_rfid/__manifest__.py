# -*- coding: utf-8 -*-
# noinspection PyStatementEffect

{
    'name': 'RFID Access Control',
    'version': '1.14',
    'category': 'Human Resources',
    'summary': 'Manage employee access control',
    'author': 'Polimex Holding Ltd',
    'license': 'AGPL-3',

    'website': 'https://www.polimex.co/',

    'depends': ['base', 'hr', 'contacts'],

    'data': [
        'security/hr_rfid_security.xml',
        'security/ir.model.access.csv',
        'data/hr_rfid_card_type_data.xml',
        'data/hr_rfid_cron_jobs.xml',
        'data/hr_rfid_system_parameters.xml',
        'data/hr_rfid_time_schedule_data.xml',
        'views/hr_rfid_views.xml',
        'wizards/hr_rfid_wizard_views.xml',
        'views/res_config_setting_view.xml',
        'views/hr_rfid_module.xml',
        'views/hr_rfid_module_controller.xml',
        'views/hr_rfid_card.xml',
        'views/hr_rfid_menus.xml',
        'views/res_partner_views.xml',
        'views/hr_department_views.xml',
        'views/hr_employee_views.xml',
    ],

    'qweb': [
        'static/src/xml/pivot_view_field_selection.xml',
    ],

    "images": [
        'static/images/main_screenshot.png',
    ],

    'application': True,
    'installable': True,
    'auto_install': False,
}








