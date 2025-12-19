# HR RFID Access Control

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-19.0.2.2.1-green.svg)](https://apps.odoo.com)

The main RFID Access Control module for Odoo, providing comprehensive hardware integration and access management capabilities.

## 🎯 Overview

HR RFID is the core module of the Polimex RFID Suite, offering enterprise-grade access control management integrated with Odoo's HR system. It supports various RFID controllers and provides real-time monitoring, advanced access rules, and comprehensive reporting.

## ✨ Key Features

### Hardware Management
- **Multi-Controller Support**: iCON50, iCON110, iCON115, iCON130, iCON180
- **Webstack Communication**: HTTP-based controller management
- **Real-time Events**: Live event processing and monitoring
- **Hardware Discovery**: Automatic detection of controllers on network

### Access Control
- **Access Groups**: Define who can access which doors
- **Time Schedules**: Configure access based on time periods
- **Zone Management**: Group doors into logical zones
- **Emergency Groups**: Special access during emergencies
- **Anti-passback**: Prevent card sharing and enforce area occupancy

### Card Management
- **Multiple Card Types**: RFID, Barcode, PIN support
- **Card Lifecycle**: Issue, activate, deactivate, expire
- **Bulk Operations**: Import/export card data
- **Card Templates**: Predefined card configurations

### Security Features
- **Duress PIN**: Silent alarm triggering
- **Alarm Management**: Door forced, door open too long
- **Audit Trail**: Complete event logging
- **Multi-Company**: Data isolation between companies

### Integration
- **HR Integration**: Link cards to employees
- **Partner Integration**: Visitor and contractor management
- **Event Webhooks**: External system notifications
- **REST API**: For third-party integrations

## 📋 Requirements

- Odoo 18.0+
- Python 3.8+
- PostgreSQL 12+
- Compatible RFID hardware

### Python Dependencies
```
- Standard Odoo dependencies
```

### Odoo Dependencies
- `base`
- `mail`
- `hr`
- `digest`

## 🛠️ Installation

1. Copy the module to your Odoo addons directory:
```bash
cp -r hr_rfid /path/to/odoo/addons/
```

2. Update the module list:
```bash
./odoo-bin -d your_database -u hr_rfid
```

3. Install via Odoo Apps interface or command line:
```bash
./odoo-bin -d your_database -i hr_rfid
```

## 🔧 Configuration

### Initial Setup

1. **System Parameters**
   - Navigate to Settings → Technical → System Parameters
   - Configure `hr_rfid.*` parameters as needed

2. **Webstack Configuration**
   - Go to RFID → Configuration → Webstacks
   - Add your webstack with IP and port
   - Test connection using the "Test" button

3. **Controller Setup**
   - Controllers will auto-appear after webstack connection
   - Configure each controller's settings
   - Map readers to doors

4. **Access Groups**
   - Create access groups under RFID → Access Groups
   - Define time schedules if needed
   - Assign doors to groups

### Hardware Setup

#### Network Configuration
```
Webstack Default Port: 80
Controller Communication: HTTP
Event Endpoint: /hr/rfid/event
```

#### Controller Types
- **iCON50**: 1 door, 1 readers
- **iCON110**: 1-2 door, 2 readers, IO support
- **iCON115**: 1-2 door, 2 readers, IO support, alarm support
- **iCON130**: 2-4 doors, 4 readers, IO support
- **turnstile**: 1 doors, 4 readers, IO support with specific turnstile features
- **iCON180**: 4 doors, 8 readers, IO support, alarm support
- **Relay**: up to 512 door, 2 readers, IO support with relays for elevator control and etc.
- **Fire**: IO support with fire alarm control panel with 4 analog fire line inputs
- **iTemp**: up to 90 temperature sensors, IO support with temperature monitoring

## 📖 Usage

### Managing Cards

1. **Issue New Card**
   - Go to RFID → Cards → Create
   - Enter card number (or scan)
   - Assign to employee/partner
   - Select access groups

2. **Bulk Import**
   - RFID → Cards → Import
   - Use Excel template provided
   - Map columns and import

### Monitoring Access

1. **Live Events**
   - RFID → Events → User Events
   - Real-time event stream
   - Filter by door, person, or time

2. **Door Status**
   - RFID → Doors
   - View current door states
   - Remote open/close doors

### Reports

- Access logs by person
- Door usage statistics
- Failed access attempts
- Alarm history

## 🔌 API Reference

### Event Processing
```python
# Event endpoint: /hr/rfid/event
POST /hr/rfid/event
{
    "controller_id": "ctrl_serial",
    "event_type": "card_read",
    "reader_id": 1,
    "card_number": "1234567890",
    "timestamp": "2024-01-01 12:00:00"
}
```

### Remote Commands
```python
# Open door remotely
door.remote_open(user_id)

# Add card to controller
card.add_to_controllers()

# Emergency open all doors
access_group.emergency_open()
```

## 🐛 Troubleshooting

### Common Issues

1. **Webstack not connecting**
   - Check network connectivity
   - Verify firewall rules
   - Confirm webstack service is running

2. **Cards not working**
   - Verify card is active
   - Check access group assignments
   - Confirm time schedules

3. **Events not appearing**
   - Check controller online status
   - Verify event processing cron job
   - Review system logs

### Debug Mode

Enable debug logging:
```python
# In configuration
log_level = debug
log_handler = hr_rfid:DEBUG
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This module is licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

## 👥 Credits

### Authors
- Polimex Dev Team

### Contributors
- See [contributors](https://github.com/polimex/odoo-apps/contributors)

### Maintainer
- [Polimex](https://polimex.co)

## 🌐 Links

- [Documentation](https://polimex.co/docs/rfid)
- [Issue Tracker](https://github.com/polimex/odoo-apps/issues)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_rfid/)

---

For more information, visit [polimex.co](https://polimex.co)