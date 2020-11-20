# -*- coding: utf-8 -*-
{
    'name': "Andromeda import",
    'summary': """
        Import cards, Access groups, Users, may be rights""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Polimex Odoo Dev Team",
    'website': "https://polimex.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['hr_rfid'],

    # connection to Firebird database
    "external_dependencies": {"python": ["fdb"]},

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'application': False,
    'installable': True,
}