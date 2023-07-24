{
    'name': "RFID Service System Portal plugin",

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
    'version': '0.1',

    'depends': ['rfid_service_base', 'hr_rfid_portal'],

    'data': [
        'views/hr_rfid_portal.xml',
        'views/rfid_service_sale_wiz.xml',
    ],
    'application': False,
    'auto_install': True,
}
