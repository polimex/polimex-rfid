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
    'version': '0.1',

    'depends': ['hr_rfid', 'portal'],

    'data': [
        'views/hr_rfid_card.xml',
        'views/hr_rfid_portal.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            '/hr_rfid_portal/static/src/scss/barcode_card_web.scss',
        ],
    },
    'application': False,
    'auto_install': True,
}
