{
    'name': "RFID attendance hourly cost plugin",

    'summary': """
        RFID attendance hourly cost plugin
    """,

    'description': """
        RFID attendance hourly cost plugin
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'LGPL-3',

    'category': "Human Resources",
    'version': '1.0',

    'depends': ['hr_hourly_cost', 'hr_attendance_late'],

    'data': [
        'views/hr_attendance_extra.xml',
    ],
    'application': False,
    'auto_install': True,
}
