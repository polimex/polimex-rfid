{
    'name': "IP Camera Management",
    'version': '19.0.1.16.2',
    'summary': "Module for managing IP cameras via manufacturers integration integration",
    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',
    'category': 'Hidden/Tools',
    'depends': ['hr_rfid'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/multi_company_related.xml',
        'views/cctv_camera_command_views.xml',
        'views/cctv_camera_views.xml',
        'views/cctv_camera_discovery_wizard.xml',
        'views/cctv_camera_rfid_rel.xml',
        'views/hr_rfid_card_views.xml',
        'views/hr_rfid_door.xml',
        'views/hr_rfid_event_user.xml',
        'views/hr_rfid_event_system.xml',
        'views/hr_rfid_reader.xml',
        'views/cctv_camera_diagnostic.xml',
    ],
    # 'images': ['static/images/main_screenshot.png'],

    'assets': {
        'web.assets_tests': [
            'polimex_ip_cam/static/tests/tours/ipcam_discovery_tour.js',
        ],
    },

    'demo': [
        'demo/demo_cam.xml',
        'demo/polimex_ip_cam_demo_showcase.xml',
    ],
    'application': False,
    'auto_install': False,
}

