# noinspection PyStatementEffect
{
    "name": "RFID Demo Data",
    "version": "19.0.1.0.1",
    "category": "Human Resources",
    "summary": "A demo company that keeps working: passages, attendance, "
    "lateness and overtime for the RFID set, day after day",
    "author": "Polimex Dev Team",
    "website": "https://polimex.co",
    "license": "AGPL-3",
    "depends": [
        "hr_rfid",
        "hr_attendance_multi_rfid",
        "hr_attendance_late",
        "hr_attendace_rfid_hr_hourly_cost",
    ],
    "data": [
        "data/hr_rfid_demo_cron.xml",
    ],
    "demo": [
        "demo/hr_rfid_demo_people.xml",
        "demo/hr_rfid_demo_backfill.xml",
    ],
    "installable": True,
    "application": False,
}
