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
- **iCON180**: 2-4 doors, 4 readers, IO support, alarm support
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
   - Type part of a person's, contact's or door's name, or an action as it
     reads in the list (e.g. "Card Denied"), in the search box and press Enter

2. **Door Status**
   - RFID → Doors
   - View current door states
   - Remote open/close doors

3. **Zone Notifications**
   - On a zone, the **Notifications** tab: each row picks an action (for
     example "Card Denied" or "Card Granted") and who is told, in the chat or
     by e-mail, when it happens at a door of the zone
   - A refused card is told like any other action; only a granted passage
     moves people in or out of the zone

4. **Work Codes**
   - **RFID System → Access Control → Work codes**: a four-digit code and what it
     means - "Coming to work", "Going to a break" or "End last action"
   - At a reader set to **Card and Workcode**, the code typed after the card
     says whether the person comes in or goes out of the zone, whatever the
     reader's type; "End last action" ends what the person's last code of the
     previous 12 hours began. The attendance and its rebuild follow the code

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
   - A controller in external database mode asks the system about every card and gets the same answer the written rights give: a card is stopped after its access in the group expires, before it starts, when its visits are used up, when it is not of the door's card type, and outside the door's time schedule (at the controller's local time)

3. **Events not appearing**
   - Check controller online status
   - Verify event processing cron job
   - Review system logs

### Messages you may see

- **"The door ... takes time schedules numbered 0 to 3 for a card"** - iCON130 and iCON180 (hotel too) hold time schedules 0-3 for a card and refuse the whole card write above that, so the door would never open for the group's cards. Choose a schedule numbered 3 or lower for such a door; iCON110, iCON115 and the turnstile take 0-15.
- **"Card ... was not written to the controller: its time schedule is number ..."** in a controller's system events - the controller refused the card because of its schedule (an access group set up before the check existed). Give the door a schedule in the controller's range in the access group and reload the cards.
- **"No answer came to "..." for card ... after N attempts, so it may not have been carried out"** in a controller's system events - a change of that card's access was handed to the module and no answer came back, so it is not known whether the controller took it. Check that the module is in touch and that the controller answers it (the line, the controller's address, its power). The command is in Events > Commands as "Command Execution Unsuccessful" with the error "No response from the Module" or "No Response from controller".
- **"No answer came to "...", so it may not have been carried out. It is not sent again, because it was meant for that moment"** in a controller's system events - a door opened or closed from the screen (the door's buttons, or "Open / close doors") got no answer. It is never handed over again later, so the door cannot open after the person has gone; look at the door to see whether it opened, and check that the module is in touch and that the controller answers it. On a module Odoo reaches directly, a failed hand-over ends the same way at once. A door set to stay unlocked or locked is a state, not a moment, and is sent until the controller takes it.
- **"No answer came to "..."" for the clock or the status reading** in a controller's system events - the controller stopped answering its routine upkeep. The line is written once, when the silence starts, not at every clock setting after it.
- **A command stays "Command Processing"** - it is out with the module, which has a short time to answer. Without an answer it is handed over again with the module's next reports and closed as unsuccessful after its attempts; the commands behind it then go out. The clock and the status reading are tried once only - their schedule repeats them - so a controller that does not answer them does not hold up changes of access. The answer to a card shown at a door that asks the server, and the credit for a vending machine, are also given once and never later.
- **"A card was used at a controller that has not described itself yet"** in a controller's system events - the controller is known only by its number and has not answered what it is, so it has no readers yet. A 100.1 module keeps the passage and sends it again once the controller is described; the report is also kept in the event. If the controller never answers, its passages are noted and accepted so that the module's other reports are not held back; ask it again with "Reload Controller Information" in the Actions menu of the controller.
- **"A vending machine asked how much credit a card has, and the vending add-on is not installed here"** - the site has a vending controller but not the vending add-on (`hr_rfid_vending`); the request is logged and the machine gets no credit. With the add-on installed, a machine is served over the classic connection and in real time alike.
- **"The number "..." is longer than the 10 characters a card number holds. Nothing was saved."** or **"Card number must be exactly 10 digits"** - a card number has 10 digits (a 4-byte number, as "5 digits + 5 digits" or as one 10-digit number). A longer number, such as a 7-byte card number written as one decimal number, is refused when it is imported or sent through the API; it is never cut to fit. A number plate is checked after its spaces and dashes are dropped.
- **Old passages arriving** - a module that was out of touch sends its stored passages when it is back, with their own dates. Each is recorded and counts for attendance on its own day. A passage that is more than 10 minutes old when it arrives, and comes after a newer one of the same person, does not change who is shown inside a zone, and does not change the anti-passback state of their card. A passage stamped later than the server's own time (a controller with its clock ahead) is not counted as the newer one.
- **Enable real-time is not on the form** - the real-time connection exists on iCON1XX 100.1 modules. A 10.3 module works the classic way only: it reports in and takes its commands in the reply.

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