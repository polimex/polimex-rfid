# RFID Portal Access

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.0.1.0-green.svg)](https://apps.odoo.com)

Portal interface for RFID card management and self-service features.

## 🎯 Overview

RFID Portal Access extends Odoo's portal functionality to provide self-service RFID card management for employees, contractors, and visitors. Users can view their cards, access history, and manage their RFID-related information through a user-friendly web interface.

## ✨ Key Features

### Card Management
- **View Cards**: See all assigned RFID cards
- **Card Details**: View card number, type, and validity
- **Barcode Display**: Show card barcode for mobile access
- **Access Groups**: See assigned access permissions

### Self-Service Features
- **Access History**: View personal entry/exit logs
- **Event Timeline**: Visual timeline of access events
- **Download Reports**: Export access history
- **Mobile Friendly**: Responsive design for all devices

### Portal Integration
- **My Account**: RFID section in portal account
- **Notifications**: Email alerts for card changes
- **Security**: View-only access to personal data
- **Multi-language**: Full translation support

## 📋 Requirements

- Odoo 18.0+
- hr_rfid module
- portal module (Odoo standard)
- website module (Odoo standard)

### Dependencies
```python
'depends': ['hr_rfid', 'portal', 'website']
```

## 🛠️ Installation

1. Install hr_rfid module first

2. Install the portal module:
```bash
./odoo-bin -d your_database -i hr_rfid_portal
```

3. Portal features are automatically available

## 🔧 Configuration

### Portal Access Setup

1. **Enable Portal Access**
   - Go to employee/partner record
   - Action → Grant Portal Access
   - User receives invitation email

2. **Configure Permissions**
   - Settings → Users → Portal Users
   - Ensure "RFID Portal User" group
   - View-only permissions by default

### Display Options

Configure in Settings → Website → RFID Portal:
```python
# Portal display settings
show_card_barcode = True
show_access_history_days = 30
allow_report_download = True
show_card_image = False
```

## 📖 Usage

### Employee Portal View

1. **Access Portal**
   - Login to portal account
   - Navigate to My Account → RFID Cards

2. **View Information**
   - Active cards list
   - Card details and barcode
   - Access group memberships
   - Recent access events

3. **Download Reports**
   - Select date range
   - Choose format (PDF/Excel)
   - Download access history

### Features Available

#### Card Information
- Card number and type
- Issue and expiry dates
- Active/inactive status
- Assigned doors/zones

#### Access History
- Date and time
- Door/reader name
- Event type (entry/exit)
- Status (granted/denied)

#### Barcode Display
- Large barcode for scanning
- Card number below
- Print option available

## 🎨 Customization

### Portal Templates

Override templates for custom design:
```xml
<!-- Inherit and modify card display -->
<template id="portal_my_rfid_cards_custom" inherit_id="hr_rfid_portal.portal_my_rfid_cards">
    <xpath expr="//div[@class='card-body']" position="after">
        <div class="custom-info">
            <!-- Add custom content -->
        </div>
    </xpath>
</template>
```

### CSS Styling

Add custom styles:
```scss
// In static/src/scss/portal_rfid.scss
.rfid-card-portal {
    .card-barcode {
        text-align: center;
        padding: 20px;
        
        svg {
            max-width: 300px;
        }
    }
}
```

## 🔌 API Extensions

### Add Portal Features

```python
from odoo import http
from odoo.http import request

class RFIDPortalExtended(http.Controller):
    
    @http.route('/my/rfid/cards/<int:card_id>/events', 
                type='http', auth='user', website=True)
    def card_events(self, card_id, **kw):
        # Show detailed events for a card
        card = request.env['hr.rfid.card'].browse(card_id)
        # Check access rights
        if card.employee_id.user_id != request.env.user:
            return request.redirect('/my')
        
        events = card.event_ids.filtered(
            lambda e: e.event_time >= datetime.now() - timedelta(days=30)
        )
        
        return request.render('hr_rfid_portal.card_events', {
            'card': card,
            'events': events,
        })
```

## 🔒 Security

### Access Control
- Users see only their own cards
- No modification rights via portal
- Audit trail for all views
- Session timeout protection

### Data Protection
- Personal data filtered
- Sensitive fields hidden
- Download limits enforced
- IP restrictions available

## 🐛 Troubleshooting

### Common Issues

1. **Can't see RFID section**
   - Check portal access is granted
   - Verify user has RFID cards
   - Clear browser cache

2. **Barcode not displaying**
   - Check barcode library installed
   - Verify card has barcode number
   - Enable in settings

3. **Access history missing**
   - Check date range settings
   - Verify events exist
   - Check user permissions

## 📱 Mobile Optimization

### Responsive Features
- Touch-friendly interface
- Swipe navigation
- Optimized barcode size
- Quick access buttons

### Mobile App Integration
- QR code for app linking
- Push notifications ready
- Offline card display
- Biometric authentication

## 🤝 Contributing

We welcome contributions:
1. Fork the repository
2. Create feature branch
3. Test on multiple devices
4. Submit pull request

## 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

## 👥 Credits

### Authors
- Polimex Dev Team

### Maintainer
- [Polimex](https://polimex.co)

## 🌐 Links

- [Documentation](https://polimex.co/docs/rfid-portal)
- [Demo Portal](https://demo.polimex.co/my)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_rfid_portal/)

---

For more information, visit [polimex.co](https://polimex.co)