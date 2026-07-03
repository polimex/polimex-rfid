{
    'name': "RFID System Portal plugin",

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
    'version': '0.2',

    'depends': ['hr_rfid', 'portal'],

    'data': [
        'views/hr_rfid_card.xml',
        'views/hr_rfid_portal.xml',
    ],
    'application': False,
    'auto_install': True,
}
