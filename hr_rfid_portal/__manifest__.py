{
    'name': "RFID Portal Access",

    'summary': """
        RFID System Portal plugin
    """,

    'description': """
        RFID System Portal plugin
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    'category': "Generic Modules/Property Management System",
    'version': '19.0.0.1.0',

    'depends': ['hr_rfid', 'portal'],

    'data': [
        'views/hr_rfid_card.xml',
        'views/hr_rfid_portal.xml',
    ],
    # 'images': ['static/images/main_screenshot.png'],
    'application': False,
    'auto_install': True,
}
