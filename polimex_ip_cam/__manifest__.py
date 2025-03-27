{
    'name': "IP Camera Management",
    'version': "1.0",
    'summary': "Module for managing IP cameras via manufacturers integration integration",
    'description': """
        This module is designed for managing cameras (e.g. Hikvision, Dahua) with automatic
        configuration through the API interfaces. It provides a model for storing camera data,
        including connection status and license plate lists (whitelist, blacklist, etc.).
        The module is designed to be flexible and extensible for different manufacturers,
        separating the logic for ANPR, CCTV IP Cams, CCTV IP NVRs.

    """,
    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',
    'category': 'Hidden/Tools',
    'depends': ['mail', 'hr_rfid'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/multi_company_related.xml',
        'views/cctv_camera_command_views.xml',
        'views/cctv_camera_views.xml',
        'views/hr_rfid_card_views.xml',
        'views/hr_rfid_door.xml',
        'views/hr_rfid_event_user.xml',
        'views/hr_rfid_event_system.xml',
        'views/hr_rfid_reader.xml',
    ],

    'demo': [
        'demo/demo_cam.xml',
    ],
    'application': False,
    'auto_install': False,
}

