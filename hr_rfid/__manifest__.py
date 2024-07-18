# -*- coding: utf-8 -*-
# noinspection PyStatementEffect

{
    'name': 'RFID Access Control',
    'version': '2.2',
    'category': 'Human Resources',
    'summary': 'Manage employee access control',
    'company': 'Polimex Holding Ltd',
    'author': 'Polimex Dev Team',
    'license': 'AGPL-3',

    'website': 'https://polimex.co/',
    'live_test_url': 'https://demo.polimex.co',
    "saas_demo_title": "Complete backend demo on Polimex servers",
    'depends': ['hr', 'contacts', 'digest'],

    'data': [
        'security/hr_rfid_security.xml',
        'security/ir.model.access.csv',
        'data/res_lang.xml',
        'data/hr_rfid_card_type_data.xml',
        'data/hr_rfid_cron_jobs.xml',
        'data/hr_rfid_system_parameters.xml',
        'views/res_config_setting_view.xml',
        'views/hr_rfid_webstack.xml',
        'views/hr_rfid_webstack_discovery.xml',
        'views/hr_rfid_webstack_replace_wiz.xml',
        'views/hr_rfid_ctrl_time_schedule.xml',
        'views/hr_rfid_ctrl_iotable.xml',
        'views/hr_rfid_ctrl.xml',
        'views/hr_rfid_ctrl_th.xml',
        'views/hr_rfid_ctrl_th_log.xml',
        'views/hr_rfid_reader.xml',
        'views/hr_rfid_door.xml',
        'views/hr_rfid_ctrl_alarm.xml',
        'views/hr_rfid_ctrl_alarm_group.xml',
        'views/hr_rfid_ctrl_emergency_group.xml',
        'views/hr_rfid_card.xml',
        'views/hr_rfid_zone.xml',
        'views/hr_rfid_card_door_rel.xml',
        'views/hr_rfid_access_group.xml',
        'views/hr_rfid_event_user.xml',
        'views/hr_rfid_event_system.xml',
        'views/hr_rfid_command.xml',
        'views/hr_rfid_workcode.xml',
        'views/res_partner_views.xml',
        'views/hr_department_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_rfid_menus.xml',
        'views/digest_views.xml',
        'views/res_company.xml',
        'templates/banners.xml',
        'security/hr_rfid_multi_company.xml',
        'report/hr_rfid_card_templates.xml',
        'report/hr_rfid_card_reports.xml',
        'data/mail_template_data.xml',
    ],

    'qweb': [
        'static/src/xml/pivot_view_field_selection.xml',
    ],

    'demo': [
        'demo/hr_rfid_demo.xml',
        'demo/hr_rfid_demo_events.xml',
    ],
    "images": [
        'static/images/main_screenshot.png',
    ],
    'assets': {
        'web.assets_backend': [
            # 'board/static/src/**/*.scss',
            # '/hr_rfid/static/src/**/*.js',
            # 'board/static/src/**/*.xml',
        ],
        # 'web.assets_common': [
        #     'hr_rfid/static/src/js/tours/**/*',
        # ],
        # 'web.assets_qweb': [
        #     'hr_rfid/static/src/xml/**/*',
        # ],
        'web.report_assets_common': [
            '/hr_rfid/static/src/scss/card_foldable_badge_report.scss',
            '/hr_rfid/static/src/scss/card_full_page_ticket_report.scss',
        ],
        'web.report_assets_pdf': [
            '/hr_rfid/static/src/scss/card_full_page_ticket_report_pdf.scss',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}
