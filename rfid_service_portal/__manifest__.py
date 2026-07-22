{
    'name': "RFID Services Portal",

    'summary': """
        RFID Service System Portal plugin
    """,

    'description': """
        RFID Service System Portal plugin
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    'category': "Generic Modules/Property Management System",
    'version': '19.0.0.2.3',

    'depends': ['rfid_service_base', 'hr_rfid_portal'],

    'data': [
        'views/hr_rfid_portal.xml',
        'views/rfid_service_sale_wiz.xml',
    ],
    'demo': [
        'demo/rfid_service_portal_demo_showcase.xml',
    ],
    # 'images': ['static/images/main_screenshot.png'],
    'application': False,
    'auto_install': True,
}
