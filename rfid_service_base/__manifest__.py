{
    'name': "RFID Service system Base",

    'summary': """
        Base module for visitor management and temporary RFID access control
    """,

    'description': """
RFID Service System Base
========================

This module provides the foundation for managing temporary RFID access services, ideal for visitor management, 
temporary passes, and service-based access control.

Key Features
------------
* **Service Management**: Define different types of RFID services (visitor passes, contractor access, etc.)
* **Service Sales**: Create and manage temporary RFID card assignments
* **Multi-Company Support**: Separate service configurations per company
* **Partner Integration**: Link services to contacts with dedicated partner fields
* **Email Templates**: Send access credentials and information to visitors
* **Standard Printing**: Print visitor badges using Odoo's standard PDF reports

Module Architecture
-------------------
This is the base module that provides core functionality. It can be extended with:
- `rfid_service_zpl_labels`: Adds ZPL wristband printing capabilities
- `rfid_service_portal`: Adds visitor portal for self-service
- Other custom extensions

Quick Start Guide
-----------------
1. **Configure Services** (RFID Services → Configuration → Services):
   - Create service types (e.g., "1-Day Visitor Pass", "Contractor Access")
   - Set validity periods and access rules
   - Configure email and print templates

2. **Create Service Sales**:
   - Use the wizard: RFID Services → Service Sales → Create
   - Select service type and visitor
   - Assign RFID card (manual entry or scan)
   - Set validity dates

3. **Manage Access**:
   - View active services in Service Sales list
   - Email badges to visitors
   - Print physical badges
   - Monitor service expiration

Configuration
-------------
* **Email Templates**: Customize visitor notification emails
* **Print Templates**: Design PDF badges for printing
* **Security Groups**: 
  - Card User: Basic service operations
  - Card Manager: Full service configuration

Technical Details
-----------------
* Models: `rfid.service`, `rfid.service.sale`
* Default print template: Partner foldable badge (PDF)
* Email template: Card barcode email template
    """,

    'author': "Polimex Dev Team",
    'website': "https://polimex.co",
    'license': 'AGPL-3',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': "Generic Modules/Property Management System",
    'version': '19.0.0.2.0',

    # any module necessary for this one to work correctly
    'depends': ['hr_rfid'],

    # always loaded
    'data': [
        'security/rfid_service_base_security.xml',
        'security/ir.model.access.csv',
        'views/rfid_service.xml',
        'views/rfid_service_sale.xml',
        'views/rfid_service_sale_wiz.xml',
        'views/res_partner_views.xml',
        'views/menus.xml',
        'data/data.xml',
        'security/rfid_services_multi_company.xml',
    ],
    # 'images': ['static/images/main_screenshot.png'],
    "demo": [
        'demo/rfid_service_demo.xml',
    ],
    "application": True,
}
