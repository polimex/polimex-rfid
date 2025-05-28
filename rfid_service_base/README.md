# RFID Service Base

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.0.2.0-green.svg)](https://apps.odoo.com)

Foundation module for visitor management and temporary access services integrated with RFID access control.

## 🎯 Overview

RFID Service Base provides the infrastructure for managing temporary access services, visitor passes, and time-limited access cards. It's designed for facilities that need to issue temporary RFID access for visitors, contractors, events, or services.

## ✨ Key Features

### Service Management
- **Service Templates**: Define reusable access patterns
- **Time-based Access**: Daily, weekly, monthly periods
- **Visit-based Access**: Limited number of entries
- **Combined Limits**: Time AND visit restrictions

### Access Configuration
- **Access Groups**: Link services to door groups
- **Zone Restrictions**: Limit access to specific areas
- **Time Schedules**: Business hours, weekends
- **Automatic Expiry**: Cards expire automatically

### Card Generation
- **Barcode Cards**: Auto-generated for quick printing
- **RFID Assignment**: Link to physical RFID cards
- **Batch Creation**: Generate multiple cards at once
- **Template-based**: Consistent card formatting

### Sales Integration
- **Service Sales**: Sell access as a service
- **Pricing Models**: Fixed price or time-based
- **Partner Integration**: Link to customers
- **Invoice Generation**: Automatic billing

## 📋 Requirements

- Odoo 18.0+
- hr_rfid module installed
- Python 3.8+

### Dependencies
```python
'depends': ['hr_rfid']
```

## 🛠️ Installation

1. Install hr_rfid module first

2. Install the service base module:
```bash
./odoo-bin -d your_database -i rfid_service_base
```

3. Configure services and access groups

## 🔧 Configuration

### Service Setup

1. **Create Service**
   - RFID → Services → Create
   - Name: "Day Pass", "Monthly Parking", etc.
   - Select service type (time/count/both)

2. **Configure Access**
   - Select access group (doors)
   - Set time limits (hours, days, months)
   - Set visit count (if applicable)
   - Define valid hours (9 AM - 6 PM)

3. **Card Settings**
   - Enable barcode generation
   - Select card type
   - Configure email template
   - Set print template

### Access Groups

1. **Visitor Groups**
   - Create dedicated visitor access groups
   - Assign appropriate doors
   - Set emergency behavior

2. **Zone Assignment**
   - Link services to zones
   - Configure zone restrictions
   - Set default zones

### Email Configuration

```python
# Email template for sending badges
mail_template_id = fields.Many2one(
    'mail.template',
    default=lambda self: self.env.ref('hr_rfid.card_barcode_mail_template_badge')
)
```

### Print Configuration

```python
# Print template for badges
print_template_id = fields.Many2one(
    'ir.actions.report',
    default=lambda self: self.env.ref('hr_rfid.action_report_res_partner_foldable_badge')
)
```

## 📖 Usage

### Creating a Service

1. **Define Service**
```
Name: "Visitor Day Pass"
Type: Time-based
Duration: 1 Day
Valid Hours: 08:00 - 18:00
Access Group: Visitor Doors
Generate Barcode: Yes
```

2. **Sell Service**
   - Click "New Sale" on service
   - Enter visitor details
   - Generate and email/print badge

### Service Types

#### Time-based Services
```
Examples:
- Day Pass (1 day)
- Week Pass (7 days)
- Monthly Pass (1 month)
- Annual Pass (1 year)
```

#### Count-based Services
```
Examples:
- 5-Visit Pass
- 10-Entry Ticket
- Single Use Pass
```

#### Combined Services
```
Examples:
- 10 visits within 30 days
- Unlimited access for 1 week
- 5 entries per month for 6 months
```

### Selling Services

1. **Quick Sale**
   - Service → New Sale
   - Fill visitor information
   - Generate card instantly

2. **Partner Sale**
   - Select existing partner
   - Choose service
   - Auto-fill information

3. **Bulk Sales**
   - Create multiple cards
   - Same service, different visitors
   - Batch print/email

## 🔌 API Extension

### Custom Services

```python
class CustomService(models.Model):
    _inherit = 'rfid.service'
    
    # Add custom fields
    requires_approval = fields.Boolean()
    approval_user_id = fields.Many2one('res.users')
    
    def action_new_sale(self):
        # Custom validation
        if self.requires_approval:
            self.check_approval()
        return super().action_new_sale()
```

### Service Validation

```python
class ServiceSaleWizard(models.TransientModel):
    _inherit = 'rfid.service.sale.wiz'
    
    @api.constrains('email')
    def _check_visitor_blacklist(self):
        # Custom validation logic
        if self.email in self.get_blacklist():
            raise ValidationError("Visitor is blacklisted")
```

## 🐛 Troubleshooting

### Common Issues

1. **Card not working**
   - Check service active dates
   - Verify visit count remaining
   - Confirm time restrictions
   - Check access group doors

2. **Email not sending**
   - Verify email configuration
   - Check template settings
   - Confirm partner email

3. **Print issues**
   - Check print template
   - Verify report configuration
   - Test with preview

### Debug Checklist

- [ ] Service is active
- [ ] Access group has doors
- [ ] Card is not expired
- [ ] Time schedule matches
- [ ] Visit count available
- [ ] Partner has access rights

## ⚙️ Advanced Features

### Multi-Service Cards

Assign multiple services to one card:
```python
# One card, multiple services
card.service_ids = [(4, service1.id), (4, service2.id)]
```

### Service Inheritance

Create service variations:
```python
# Base service as template
base_service = self.env.ref('rfid_service_base.visitor_day_pass')
new_service = base_service.copy({
    'name': 'VIP Day Pass',
    'access_group_id': vip_access_group.id
})
```

### Automatic Renewals

Configure auto-renewal:
```python
# In service configuration
auto_renew = fields.Boolean()
renew_before_days = fields.Integer(default=7)
```

## 📊 Reports

### Service Analytics
- Services sold by period
- Revenue by service type
- Popular services ranking
- Utilization rates

### Visitor Reports
- Active visitors count
- Visitor frequency
- Access patterns
- Expired services

### Usage Statistics
- Entry count by service
- Peak usage times
- Average visit duration
- Zone utilization

## 🤝 Contributing

Contributions welcome:
1. Fork repository
2. Create feature branch
3. Add tests
4. Submit pull request

## 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

## 👥 Credits

### Authors
- Polimex Dev Team

### Contributors
- See [contributors](https://github.com/polimex/odoo-apps/contributors)

### Maintainer
- [Polimex](https://polimex.co)

## 🌐 Links

- [Documentation](https://polimex.co/docs/rfid-services)
- [Video Tutorials](https://polimex.co/tutorials)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/rfid_service_base/)

---

For more information, visit [polimex.co](https://polimex.co)