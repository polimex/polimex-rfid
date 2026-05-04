{
    'name': "Services ZPL Labels - CUPS Integration",

    'summary': """
        Replace direct ZPL printing with CUPS queue management
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    'category': "Generic Modules/Property Management System",
    'version': '19.0.0.1.4',

    # This module depends on both ZPL labels and CUPS printing
    'depends': [
        'rfid_service_zpl_labels',
        'base_report_to_label_printer',
    ],

    # Auto-install when both dependencies are installed
    'auto_install': True,

    # always loaded
    'data': [
        'data/report_config.xml',
        'data/server_actions.xml',
        'views/rfid_service.xml',
        'views/rfid_service_sale.xml',
    ],

    # base_report_to_label_printer lives in OCA repo report-print-send and is
    # not bundled in this repository. Keep installable=False so the Odoo Apps
    # validator does not flag an unmet dependency. Flip to True after adding
    # the OCA repo to the addons path.
    'installable': False,
    "application": False,
}