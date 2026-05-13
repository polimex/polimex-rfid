{
    'name': "IP Camera Management",
    'version': '19.0.1.2.0',
    'summary': "Module for managing IP cameras via manufacturers integration integration",
    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',
    'category': 'Hidden/Tools',
    'depends': ['hr_rfid'],
    'external_dependencies': {
        'python': ['defusedxml'],
    },

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/multi_company_related.xml',
        'views/cctv_camera_command_views.xml',
        'views/cctv_camera_views.xml',
        'views/cctv_camera_rfid_rel.xml',
        'views/hr_rfid_card_views.xml',
        'views/hr_rfid_door.xml',
        'views/hr_rfid_event_user.xml',
        'views/hr_rfid_event_system.xml',
        'views/hr_rfid_reader.xml',
    ],
    # 'images': ['static/images/main_screenshot.png'],

    'demo': [
        'demo/demo_cam.xml',
    ],
    'application': False,
    'auto_install': False,
}

