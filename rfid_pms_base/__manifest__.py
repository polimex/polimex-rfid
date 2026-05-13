{
    'name': "RFID PMS Base",
    'summary': "RFID PMS system Base structures",
    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',
    'category': "Generic Modules/Property Management System",
    'version': '19.0.0.6.0',
    'depends': ['hr_rfid', 'onboarding'],
    'data': [
        'security/pms_base_security.xml',
        'security/ir.model.access.csv',
        'views/wiz_card_from_room.xml',
        'views/wiz_room_move.xml',
        'views/hr_rfid_card.xml',
        'views/room.xml',
        'views/views.xml',
        'views/menus.xml',
        'data/data.xml',
        'data/onboarding_data.xml',
    ],
    'application': True,
    'installable': True,
    'assets': {
        'web.assets_tests': [
            'rfid_pms_base/static/tests/tours/*.js',
        ],
    },
}
