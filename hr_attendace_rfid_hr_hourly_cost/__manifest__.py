{
    'name': "RFID Hourly Cost",

    'summary': """
        RFID attendance hourly cost plugin
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    'category': "Human Resources",
    'version': '19.0.1.1.0',

    'depends': ['hr_hourly_cost', 'hr_attendance_late'],

    'data': [
        'views/hr_attendance_extra.xml',
    ],
    # 'images': ['static/images/main_screenshot.png'],
    'application': False,
    'auto_install': True,
}
